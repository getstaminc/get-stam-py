"""add france league

Revision ID: 609cc43261e6
Revises: c06225115194
Create Date: 2025-12-02 14:14:01.227905

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import csv
import os
from datetime import datetime
# translation helper used elsewhere in the project
from soccer_utils import translate_soccer_team_name


# revision identifiers, used by Alembic.
revision: str = '609cc43261e6'
down_revision: Union[str, None] = 'c06225115194'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed French (Ligue 1) games from CSVs located in migrations/france_csvs.

    Mirrors the defensive approach used by other league seeders (Italy/Bundesliga):
    - skip rows with unparseable dates
    - translate team names via translate_soccer_team_name
    - map spreadsheet/raw names to canonical DB names when needed
    - insert minimal `teams` rows for missing teams (sport='SOCCER') and re-query
    - fail fast if a team cannot be resolved after insertion
    - avoid duplicate inserts by checking for existing league/date/home/away rows
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "france_csvs")
    if not os.path.isdir(base_dir):
        return

    bind = op.get_bind()
    teams_table = sa.Table('teams', sa.MetaData(), autoload_with=bind)
    soccer_games = sa.Table('soccer_games', sa.MetaData(), autoload_with=bind)

    def parse_date(d: str):
        # Expect dates in strict DD/MM/YYYY format (e.g. 22/08/2025)
        try:
            return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            raise ValueError(f"Unrecognized date format (expected DD/MM/YYYY): {d}")

    def parse_start_time(row):
        time_str = row.get("Time")
        if time_str:
            try:
                return datetime.strptime(time_str, "%H:%M").time()
            except Exception:
                return None
        return None

    def to_int(v):
        try:
            if v is None or v == '' or str(v).upper() == 'NA':
                return None
            return int(float(v))
        except Exception:
            return None

    # Mapping from incoming/raw or translated names to canonical DB team names
    canonical_team_map = {
        'Ajaccio': 'AC Ajaccio',
        'Ajaccio GFCO': 'Ajaccio GFCO',
        'Amiens': 'Amiens',
        'Angers': 'Angers',
        'Arles': 'Arles',
        'Auxerre': 'Auxerre',
        'Bastia': 'SC Bastia',
        'Bordeaux': 'Bordeaux',
        'Brest': 'Brest',
        'Caen': 'Caen',
        'Clermont': 'Clermont',
        'Dijon': 'Dijon FCO',
        'Evian Thonon Gaillard': 'Evian Thonon Gaillard',
        'Guingamp': 'Guingamp',
        'Le Havre': 'Le Havre',
        'Lens': 'RC Lens',
        'Lille': 'Lille',
        'Lorient': 'Lorient',
        'Lyon': 'Lyon',
        'Marseille': 'Marseille',
        'Metz': 'Metz',
        'Monaco': 'AS Monaco',
        'Montpellier': 'Montpellier',
        'Nancy': 'Nancy',
        'Nantes': 'Nantes',
        'Nice': 'Nice',
        'Nimes': 'Nîmes Olympique',
        'Paris FC': 'Paris FC',
        'Paris SG': 'Paris Saint Germain',
        'Reims': 'Stade de Reims',
        'Rennes': 'Rennes',
        'Sochaux': 'Sochaux',
        'St Etienne': 'Saint Etienne',
        'Strasbourg': 'Strasbourg',
        'Toulouse': 'Toulouse',
        'Troyes': 'Troyes',
        'Valenciennes': 'Valenciennes',
    }

    csv_files = sorted(
        os.path.join(base_dir, f)
        for f in os.listdir(base_dir)
        if f.lower().endswith('.csv') and not f.startswith('.') and not f.startswith('~')
    )

    missing_team_rows = []
    processed_rows = 0
    for path in csv_files:
        if not os.path.isfile(path):
            continue
        print(f"[alembic] processing CSV: {os.path.basename(path)}")
        with open(path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                row = {k.strip(): v for k, v in row.items()}
                date_raw = row.get('Date')
                if not date_raw:
                    continue
                try:
                    game_date = parse_date(date_raw)
                except Exception:
                    continue

                home_raw = row.get('HomeTeam') or row.get('Home')
                away_raw = row.get('AwayTeam') or row.get('Away')
                if not home_raw or not away_raw:
                    continue

                home_name = translate_soccer_team_name(home_raw)
                away_name = translate_soccer_team_name(away_raw)

                def _canonical(raw, translated):
                    if raw in canonical_team_map:
                        return canonical_team_map[raw]
                    if translated in canonical_team_map:
                        return canonical_team_map[translated]
                    return translated

                canonical_home = _canonical(home_raw, home_name)
                canonical_away = _canonical(away_raw, away_name)

                if canonical_home != home_name:
                    print(f"[alembic] mapped home '{home_raw}' -> '{canonical_home}'")
                if canonical_away != away_name:
                    print(f"[alembic] mapped away '{away_raw}' -> '{canonical_away}'")

                home_name = canonical_home
                away_name = canonical_away

                def ensure_team(team_name_val):
                    """Ensure a team exists and return its team_id.

                    Behavior:
                    - If the team already exists, return its id.
                    - Otherwise INSERT the minimal team row and return the new id using RETURNING.
                    - If the INSERT collides (concurrent insert), re-query and return the id.
                    - On unexpected errors raise the exception so the migration fails fast.
                    """
                    # Try to find an existing team_id first
                    t_id = bind.execute(
                        sa.select(teams_table.c.team_id).where(teams_table.c.team_name == team_name_val)
                    ).scalar()
                    if t_id is not None:
                        return t_id

                    # Insert and return the new id in one round-trip when possible
                    try:
                        res = bind.execute(
                            sa.text(
                                "INSERT INTO teams (team_name, sport) VALUES (:team_name, :sport) RETURNING team_id"
                            ),
                            {"team_name": team_name_val, "sport": 'SOCCER'}
                        )
                        new_id = res.scalar()
                        if new_id is not None:
                            return int(new_id)
                    except Exception as e:
                        # If a concurrent insert caused a unique/constraint error, re-query and return the id.
                        # For other exceptions, re-raise so the migration fails loudly (we want fail-fast).
                        try:
                            # attempt to re-query in case another process inserted the team
                            t_id = bind.execute(
                                sa.select(teams_table.c.team_id).where(teams_table.c.team_name == team_name_val)
                            ).scalar()
                            if t_id is not None:
                                return t_id
                        except Exception:
                            pass
                        raise

                    # If INSERT did not return an id (rare), re-query once before giving up
                    t_id = bind.execute(
                        sa.select(teams_table.c.team_id).where(teams_table.c.team_name == team_name_val)
                    ).scalar()
                    return t_id

                home_id = ensure_team(home_name)
                away_id = ensure_team(away_name)

                if home_id is None or away_id is None:
                    missing_parts = []
                    if home_id is None:
                        missing_parts.append(f"home={home_name!r} raw={home_raw!r}")
                    if away_id is None:
                        missing_parts.append(f"away={away_name!r} raw={away_raw!r}")
                    filename = os.path.basename(path)
                    raise RuntimeError(
                        f"Missing team_id for {', '.join(missing_parts)} in {filename} date={date_raw}"
                    )

                FTHG = to_int(row.get('FTHG'))
                FTAG = to_int(row.get('FTAG'))
                HTHG = to_int(row.get('HTHG'))
                HTAG = to_int(row.get('HTAG'))

                start_time = parse_start_time(row)

                B365H = to_int(row.get('B365H'))
                B365D = to_int(row.get('B365D'))
                B365A = to_int(row.get('B365A'))
                over_price = to_int(row.get('BbAv>2.5') or row.get('B365>2.5'))
                under_price = to_int(row.get('BbAv<2.5') or row.get('B365<2.5'))
                AHCh = None
                try:
                    raw_ah = row.get('BbAHh') or row.get('BbAH') or row.get('AHCh')
                    if raw_ah not in (None, '', 'NA'):
                        AHCh = float(raw_ah)
                except Exception:
                    AHCh = None

                total_goals = None
                if FTHG is not None and FTAG is not None:
                    total_goals = FTHG + FTAG

                home_second_half = None
                away_second_half = None
                if FTHG is not None and HTHG is not None:
                    home_second_half = FTHG - HTHG
                if FTAG is not None and HTAG is not None:
                    away_second_half = FTAG - HTAG

                exists_q = sa.select(sa.func.count()).select_from(soccer_games).where(
                    sa.and_(
                        soccer_games.c.league == 'LIGUE 1',
                        soccer_games.c.game_date == game_date,
                        soccer_games.c.home_team_id == home_id,
                        soccer_games.c.away_team_id == away_id,
                    )
                )
                already = bind.execute(exists_q).scalar()
                if already and int(already) > 0:
                    continue

                bind.execute(
                    sa.text(
                        """
                        INSERT INTO soccer_games (
                            odds_id, league, game_date, home_team_id, away_team_id,
                            home_team_name, away_team_name, home_goals, total_goals, away_goals,
                            home_money_line, draw_money_line, away_money_line,
                            home_spread, away_spread, total_over_point, total_over_price,
                            total_under_point, total_under_price,
                            home_first_half_goals, away_first_half_goals,
                            home_second_half_goals, away_second_half_goals,
                            away_overtime, home_overtime, start_time
                        ) VALUES (
                            :odds_id, :league, :game_date, :home_team_id, :away_team_id,
                            :home_team_name, :away_team_name, :home_goals, :total_goals, :away_goals,
                            :home_money_line, :draw_money_line, :away_money_line,
                            :home_spread, :away_spread, :total_over_point, :total_over_price,
                            :total_under_point, :total_under_price,
                            :home_first_half_goals, :away_first_half_goals,
                            :home_second_half_goals, :away_second_half_goals,
                            :away_overtime, :home_overtime, :start_time
                        )
                        """
                    ),
                    {
                        "odds_id": None,
                        "league": 'LIGUE 1',
                        "game_date": game_date,
                        "home_team_id": home_id,
                        "away_team_id": away_id,
                        "home_team_name": home_name,
                        "away_team_name": away_name,
                        "home_goals": FTHG,
                        "total_goals": total_goals,
                        "away_goals": FTAG,
                        "home_money_line": B365H,
                        "draw_money_line": B365D,
                        "away_money_line": B365A,
                        "home_spread": AHCh,
                        "away_spread": -AHCh if AHCh is not None else None,
                        "total_over_point": 2.5,
                        "total_over_price": over_price,
                        "total_under_point": 2.5,
                        "total_under_price": under_price,
                        "home_first_half_goals": HTHG,
                        "away_first_half_goals": HTAG,
                        "home_second_half_goals": home_second_half,
                        "away_second_half_goals": away_second_half,
                        "away_overtime": None,
                        "home_overtime": None,
                        "start_time": start_time,
                    }
                )
                processed_rows += 1

    if missing_team_rows:
        lines = [
            f"{m['csv_file']} date={m['date']} - " + ", ".join(
                f"{k}={v!r}" for k, v in m.items() if k not in ('csv_file', 'date')
            )
            for m in missing_team_rows
        ]
        summary = (
            f"Missing team mappings detected in {len(missing_team_rows)} row(s).\n" +
            "Add the missing teams to the `teams` table (sport='SOCCER') or update your translation helper.\n" +
            "Missing rows:\n" + "\n".join(lines)
        )
        raise RuntimeError(summary)
    else:
        print(f"[alembic] processed {processed_rows} rows from {len(csv_files)} CSV file(s).")


def downgrade() -> None:
    pass
