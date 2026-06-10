"""seed_international_soccer_games

Reads migrations/international_soccer/World Cup fields - uploadData.csv and:
  1. Inserts any teams not yet in the teams table (INTL_SOCCER sport)
  2. Deduplicates by espn_event_id (prefer the home-team row; fall back to away row)
  3. Inserts canonical game records into international_soccer_games

Team names are normalised to Odds API canonical spellings so the daily seed job
can look teams up without any name translation.

CSV columns:
  team_id, team_name, match_date, opponent, home_away, team_score, opponent_score,
  espn_event_id, espn_event_url, team_odds_american, opponent_odds_american, draw_odds_american

home_away mapping:
  home row → team_name is home, opponent is away
  away row → opponent is home, team_name is away

Revision ID: d1e2f3a4b5c6
Revises: b460d3e1ede4
Create Date: 2026-06-09
"""

from typing import Sequence, Union
import csv
import os

from alembic import op
from sqlalchemy import text


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'b460d3e1ede4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Name normalisation — CSV spelling → Odds API canonical name (stored in DB)
# DB team names must match Odds API exactly so the daily seed job needs no translation.
# ---------------------------------------------------------------------------
TEAM_NAME_NORM = {
    'Bosnia-Herzegovina': 'Bosnia & Herzegovina',
    'Congo DR':           'DR Congo',
    'Curacao':            'Curaçao',
    'Czechia':            'Czech Republic',
    'Türkiye':            'Turkey',
    'United States':      'USA',
}

CSV_PATH = os.path.join(
    os.path.dirname(__file__),
    '../../migrations/international_soccer/World Cup fields - uploadData.csv'
)


def _norm(name: str) -> str:
    return TEAM_NAME_NORM.get(name, name)


def _parse_int(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        # American odds can be "+245" or "-213" or "3333"
        return int(s.lstrip('+'))
    except ValueError:
        return None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Parse CSV
    # ------------------------------------------------------------------
    # team_name → espn_team_id  (only for teams that appear as team_name)
    espn_id_map = {}
    # All (home_name, away_name, game_date, ...) keyed by espn_event_id
    events = {}

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = _norm(row['team_name'].strip())
            opponent = _norm(row['opponent'].strip())
            espn_id_map[team] = row['team_id'].strip()
            espn_event_id = row['espn_event_id'].strip()
            if espn_event_id not in events:
                events[espn_event_id] = []
            # Store a normalised copy of the row
            events[espn_event_id].append({
                'team_name':              team,
                'opponent':               opponent,
                'home_away':              row['home_away'].strip(),
                'team_score':             row['team_score'].strip(),
                'opponent_score':         row['opponent_score'].strip(),
                'match_date':             row['match_date'].strip(),
                'team_odds_american':     row['team_odds_american'].strip(),
                'opponent_odds_american': row['opponent_odds_american'].strip(),
                'draw_odds_american':     row['draw_odds_american'].strip(),
            })

    all_team_names = set(espn_id_map.keys())
    # Collect opponent names that don't appear as a primary team
    for rows in events.values():
        for r in rows:
            all_team_names.add(r['team_name'])
            all_team_names.add(r['opponent'])

    # ------------------------------------------------------------------
    # 2. Insert any teams not yet in the DB
    # ------------------------------------------------------------------
    existing_teams = {
        r[0] for r in conn.execute(text("SELECT team_name FROM teams"))
    }
    for team_name in sorted(all_team_names):
        if team_name in existing_teams:
            continue
        espn_id = espn_id_map.get(team_name)
        if espn_id:
            conn.execute(text(
                "INSERT INTO teams (team_name, sport, espn_team_id) "
                "VALUES (:name, 'INTL_SOCCER', :espn_id)"
            ), {'name': team_name, 'espn_id': espn_id})
        else:
            conn.execute(text(
                "INSERT INTO teams (team_name, sport) VALUES (:name, 'INTL_SOCCER')"
            ), {'name': team_name})

    # ------------------------------------------------------------------
    # 3. Build team_name → team_id lookup
    # ------------------------------------------------------------------
    rows_result = conn.execute(text(
        "SELECT team_name, team_id FROM teams WHERE sport = 'INTL_SOCCER'"
    ))
    team_id_map = {r[0]: r[1] for r in rows_result}

    # ------------------------------------------------------------------
    # 4. Deduplicate events and insert games
    # ------------------------------------------------------------------
    inserted = 0
    skipped = 0

    for espn_event_id, rows in events.items():
        # Check for an existing record (idempotent re-run safety)
        existing = conn.execute(text(
            "SELECT 1 FROM international_soccer_games WHERE odds_id = :oid LIMIT 1"
        ), {'oid': espn_event_id}).fetchone()
        if existing:
            skipped += 1
            continue

        # Prefer the home-team row to build a canonical game record
        home_rows = [r for r in rows if r['home_away'] == 'home']

        if home_rows:
            r = home_rows[0]
            home_name = r['team_name']
            away_name = r['opponent']
            home_goals = _parse_int(r['team_score'])
            away_goals = _parse_int(r['opponent_score'])
            home_ml   = _parse_int(r['team_odds_american'])
            away_ml   = _parse_int(r['opponent_odds_american'])
            draw_ml   = _parse_int(r['draw_odds_american'])
            game_date = r['match_date']
        else:
            # Only away row(s) available — flip the perspective
            r = rows[0]
            home_name = r['opponent']
            away_name = r['team_name']
            home_goals = _parse_int(r['opponent_score'])
            away_goals = _parse_int(r['team_score'])
            home_ml   = _parse_int(r['opponent_odds_american'])
            away_ml   = _parse_int(r['team_odds_american'])
            draw_ml   = _parse_int(r['draw_odds_american'])
            game_date = r['match_date']

        home_team_id = team_id_map.get(home_name)
        away_team_id = team_id_map.get(away_name)

        if not home_team_id or not away_team_id:
            print(f"[seed] WARNING: no team_id for '{home_name}' or '{away_name}' — skipping ESPN {espn_event_id}")
            skipped += 1
            continue

        total_goals = None
        if home_goals is not None and away_goals is not None:
            total_goals = home_goals + away_goals

        conn.execute(text("""
            INSERT INTO international_soccer_games
                (odds_id, league, game_date,
                 home_team_id, away_team_id,
                 home_team_name, away_team_name,
                 home_goals, away_goals, total_goals,
                 home_money_line, away_money_line, draw_money_line)
            VALUES
                (:odds_id, 'INTL', :game_date,
                 :home_team_id, :away_team_id,
                 :home_name, :away_name,
                 :home_goals, :away_goals, :total_goals,
                 :home_ml, :away_ml, :draw_ml)
        """), {
            'odds_id':      espn_event_id,
            'game_date':    game_date,
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'home_name':    home_name,
            'away_name':    away_name,
            'home_goals':   home_goals,
            'away_goals':   away_goals,
            'total_goals':  total_goals,
            'home_ml':      home_ml,
            'away_ml':      away_ml,
            'draw_ml':      draw_ml,
        })
        inserted += 1

    print(f"[seed] International soccer games: inserted={inserted}, skipped={skipped}")


def downgrade() -> None:
    conn = op.get_bind()

    # Remove seeded games (identified by ESPN event IDs from the CSV)
    espn_ids = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            eid = row['espn_event_id'].strip()
            if eid:
                espn_ids.append(eid)

    if espn_ids:
        conn.execute(text(
            "DELETE FROM international_soccer_games WHERE odds_id = ANY(:ids)"
        ), {'ids': list(set(espn_ids))})

    # Remove teams that were added by this migration and have no games
    conn.execute(text("""
        DELETE FROM teams
        WHERE sport = 'INTL_SOCCER'
          AND team_id NOT IN (
            SELECT home_team_id FROM international_soccer_games
            UNION
            SELECT away_team_id FROM international_soccer_games
          )
    """))

