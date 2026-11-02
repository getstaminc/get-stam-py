#!/usr/bin/env python3
"""Fallback fill for NCAAB games: fetches yesterday's games from SDQL (the
same query the old jobs/ncaab_seed_yesterdays_games.py used) and fills in
ONLY whatever is still NULL on the matching ncaab_games row -- never
overwrites a value jobs/ncaab_odds_api_seed_yesterdays_games.py already
supplied. If a game is missing entirely (rare -- ESPN's Division I
scoreboard should have caught nearly everything SDQL finds for D-I; non-D-I
games depend on this job for everything), inserts it fresh from SDQL with
odds_event_id left NULL.

SDQL's NCAABB query has no quarter/half-score field at all -- this job
never touches home/away_quarter_scores or the half/OT point columns; those
stay NULL if job 1's ESPN enrichment also missed them.

SDQL emits one row per team for neutral-site games, with home/away
reversed between the two rows for the same real game (both pass the
`site IN ('home','neutral')` filter). This job dedupes those in memory
before processing, and its existing-row check tests BOTH orientations --
an exact-orientation match is a fill target, a reversed-orientation match
means the game is already represented and this row is skipped entirely
(no fill, to avoid needing to swap home/away values). Without this guard,
every neutral-site game would get a second, duplicate row -- confirmed as
a real production bug during the NCAAF migration.

Scheduled to run AFTER jobs/ncaab_odds_api_seed_yesterdays_games.py, later
in the day (SDQL's data becomes reliably available later than Odds API's).
"""
import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'


def get_yesterdays_sdql_games(retries=3, delay=1):
    """Same SDQL query the old job used -- unchanged."""
    sdql_url = "https://s3.sportsdatabase.com/NCAABB/query"
    today = datetime.today().strftime('%Y%m%d')
    two_days_ago = (datetime.today() - timedelta(days=2)).strftime('%Y%m%d')
    sdql_query = (
        f"date,site,team,o:team,points,o:points,total,margin,line,o:line,"
        f"playoffs,money line,o:money line,_t,start time"
        f"@(site='home' or site='neutral') and date<{today} and date>={two_days_ago}"
    )
    headers = {'user': SDQL_USERNAME, 'token': SDQL_TOKEN}
    data = {'sdql': sdql_query}

    for i in range(retries):
        try:
            response = requests.get(sdql_url, headers=headers, params=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result.get('headers') and result.get('groups'):
                headers_list = result['headers']
                rows = result['groups'][0]['columns']
                formatted = [dict(zip(headers_list, row)) for row in zip(*rows)]
                for game in formatted:
                    game['date'] = datetime.strptime(str(game['date']), '%Y%m%d').strftime('%Y-%m-%d')
                return formatted
            return []
        except requests.exceptions.RequestException as e:
            print(f"SDQL request failed (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
        except ValueError as e:
            print(f"Error parsing SDQL response: {e}")
            return []
    return []


def fill_yesterdays_ncaab_games_from_sdql():
    print("Starting NCAAB SDQL fallback fill...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        games = get_yesterdays_sdql_games()
        print(f"Fetched {len(games)} SDQL games to use as fallback data")

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAB'")).mappings()
        }

        # Resolve team ids and dedupe SDQL's per-team mirrored rows for
        # neutral-site games BEFORE processing -- same (date, frozenset of
        # team ids) key used for NCAAF's equivalent fix.
        resolved = {}
        for game in games:
            if game.get('points') is None or game.get('o:points') is None:
                continue
            home_team_id = teams_dict.get(game['team'])
            away_team_id = teams_dict.get(game['o:team'])
            if home_team_id is None or away_team_id is None:
                continue
            key = (game['date'], frozenset({home_team_id, away_team_id}))
            resolved.setdefault(key, []).append((game, home_team_id, away_team_id))

        filled = 0
        inserted = 0
        skipped_duplicate = 0
        for (_, _), candidates in resolved.items():
            game, home_team_id, away_team_id = candidates[0]

            def to_number(value):
                return value if isinstance(value, (int, float)) else None

            total_value = to_number(game.get('total'))
            home_line = to_number(game.get('line'))
            away_line = to_number(game.get('o:line'))
            home_money = to_number(game.get('money line'))
            away_money = to_number(game.get('o:money line'))

            params = {
                "game_date": game['date'], "game_site": game.get('site') or 'home',
                "home_team_id": home_team_id, "away_team_id": away_team_id,
                "home_team_name": game['team'], "away_team_name": game['o:team'],
                "home_points": game['points'], "away_points": game['o:points'],
                "total_points": game['points'] + game['o:points'], "total_margin": game.get('margin'),
                "home_line": home_line, "away_line": away_line,
                "home_money_line": home_money, "away_money_line": away_money,
                "playoffs": bool(game.get('playoffs', 0)), "total": total_value,
            }

            exact = conn.execute(text("""
                SELECT game_id FROM ncaab_games
                WHERE game_date = :game_date AND home_team_id = :home_team_id AND away_team_id = :away_team_id
            """), {
                "game_date": game['date'], "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()

            if exact:
                conn.execute(text("""
                    UPDATE ncaab_games SET
                        game_site = COALESCE(game_site, :game_site),
                        home_points = COALESCE(home_points, :home_points),
                        away_points = COALESCE(away_points, :away_points),
                        total_points = COALESCE(total_points, :total_points),
                        total_margin = COALESCE(total_margin, :total_margin),
                        home_line = COALESCE(home_line, :home_line),
                        away_line = COALESCE(away_line, :away_line),
                        home_money_line = COALESCE(home_money_line, :home_money_line),
                        away_money_line = COALESCE(away_money_line, :away_money_line),
                        playoffs = COALESCE(playoffs, :playoffs),
                        total = COALESCE(total, :total)
                    WHERE game_id = :game_id
                """), {**params, "game_id": exact[0]})
                filled += 1
                continue

            reversed_match = conn.execute(text("""
                SELECT 1 FROM ncaab_games
                WHERE game_date = :game_date AND home_team_id = :away_team_id AND away_team_id = :home_team_id
            """), {
                "game_date": game['date'], "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()
            if reversed_match:
                # Already represented (job 1, or SDQL's own mirrored row for this
                # neutral-site game via a different (date, team-pair) candidate)
                # under the opposite home/away orientation -- skip entirely rather
                # than inserting a second, duplicate row for the same real game.
                skipped_duplicate += 1
                continue

            conn.execute(text("""
                INSERT INTO ncaab_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_points, away_points, total_points, total_margin, home_line, away_line,
                    home_money_line, away_money_line, playoffs, total
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                    :home_money_line, :away_money_line, :playoffs, :total
                )
            """), params)
            inserted += 1

        conn.commit()
        print(f"Done. Rows filled (existing, NULL-only): {filled}. Rows inserted fresh: {inserted}. "
              f"Duplicate neutral-site rows skipped: {skipped_duplicate}.")
    except Exception as e:
        print(f"Error during SDQL fallback fill: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    fill_yesterdays_ncaab_games_from_sdql()
