#!/usr/bin/env python3
"""Fallback fill for NCAAF games: fetches yesterday's games from SDQL (the
same query the old jobs/ncaaf_seed_yesterdays_games.py used) and fills in
ONLY whatever is still NULL on the matching ncaaf_games row -- never
overwrites a value jobs/ncaaf_odds_api_seed_yesterdays_games.py already
supplied. If a game is missing entirely (rare -- ESPN's broad scoreboard
should have caught nearly everything SDQL finds), inserts it fresh from
SDQL with odds_event_id left NULL.

Scheduled to run AFTER jobs/ncaaf_odds_api_seed_yesterdays_games.py, later
in the day (SDQL's data becomes reliably available later than Odds API's).
"""
import os
import sys
import json
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


def convert_sdql_start_time_to_time(start_time):
    try:
        if start_time is None:
            return None
        start_time_str = str(start_time)
        if len(start_time_str) == 3:
            start_time_str = '0' + start_time_str
        if len(start_time_str) == 4:
            hour = int(start_time_str[:2])
            minute = int(start_time_str[2:])
            return f"{hour:02d}:{minute:02d}:00"
        return None
    except (ValueError, TypeError):
        return None


def get_yesterdays_sdql_games(retries=3, delay=1):
    """Same SDQL query the old job used -- unchanged."""
    sdql_url = "https://s3.sportsdatabase.com/NCAAFB/query"
    today = datetime.today().strftime('%Y%m%d')
    two_days_ago = (datetime.today() - timedelta(days=2)).strftime('%Y%m%d')
    sdql_query = (
        f"date,site,team,o:team,points,o:points,total,margin,line,o:line,"
        f"quarter scores,o:quarter scores,playoffs,money line,o:money line,start time,_t"
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


def fill_yesterdays_ncaaf_games_from_sdql():
    print("Starting NCAAF SDQL fallback fill...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        games = get_yesterdays_sdql_games()
        print(f"Fetched {len(games)} SDQL games to use as fallback data")

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAF'")).mappings()
        }

        # SDQL emits one row per team for a neutral-site game, and BOTH rows pass
        # the site filter in get_yesterdays_sdql_games with home/away reversed
        # (e.g. "Georgia vs Florida" and "Florida vs Georgia" for the same real
        # game). Resolve team ids first, then dedupe by (date, the two teams
        # involved) so each real game is only processed once below.
        deduped_games = []
        seen_keys = set()
        for game in games:
            if game.get('points') is None or game.get('o:points') is None:
                continue

            home_team_id = teams_dict.get(game['team'])
            away_team_id = teams_dict.get(game['o:team'])
            if home_team_id is None or away_team_id is None:
                continue

            key = (game['date'], frozenset({home_team_id, away_team_id}))
            if key in seen_keys:
                continue
            seen_keys.add(key)

            game['_home_team_id'] = home_team_id
            game['_away_team_id'] = away_team_id
            deduped_games.append(game)

        filled = 0
        inserted = 0
        skipped_reversed = 0
        for game in deduped_games:
            home_team_id = game['_home_team_id']
            away_team_id = game['_away_team_id']

            try:
                home_qs = json.loads(game['quarter scores']) if game.get('quarter scores') else None
                away_qs = json.loads(game['o:quarter scores']) if game.get('o:quarter scores') else None
            except (TypeError, json.JSONDecodeError):
                home_qs = away_qs = None

            if home_qs and away_qs:
                home_first_half = sum(home_qs[:2])
                away_first_half = sum(away_qs[:2])
                home_second_half = sum(home_qs[2:4])
                away_second_half = sum(away_qs[2:4])
                home_overtime = home_qs[4] if len(home_qs) > 4 else None
                away_overtime = away_qs[4] if len(away_qs) > 4 else None
            else:
                home_first_half = away_first_half = None
                home_second_half = away_second_half = None
                home_overtime = away_overtime = None

            start_time_raw = game.get('start time')
            start_time = None
            if start_time_raw and start_time_raw != 0:
                start_time = convert_sdql_start_time_to_time(str(start_time_raw))

            total_raw = game.get('total')
            total_value = total_raw if isinstance(total_raw, (int, float)) else None
            home_line_raw = game.get('line')
            away_line_raw = game.get('o:line')
            home_line = home_line_raw if isinstance(home_line_raw, (int, float)) else None
            away_line = away_line_raw if isinstance(away_line_raw, (int, float)) else None
            home_money_raw = game.get('money line')
            away_money_raw = game.get('o:money line')
            home_money = int(home_money_raw) if isinstance(home_money_raw, (int, float)) else None
            away_money = int(away_money_raw) if isinstance(away_money_raw, (int, float)) else None

            existing = conn.execute(text("""
                SELECT game_id, home_team_id, away_team_id FROM ncaaf_games
                WHERE game_date = :game_date
                  AND ((home_team_id = :home_team_id AND away_team_id = :away_team_id)
                       OR (home_team_id = :away_team_id AND away_team_id = :home_team_id))
            """), {
                "game_date": game['date'], "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()

            params = {
                "game_date": game['date'], "game_site": game.get('site') or 'home',
                "home_team_id": home_team_id, "away_team_id": away_team_id,
                "home_team_name": game['team'], "away_team_name": game['o:team'],
                "home_points": game['points'], "away_points": game['o:points'],
                "total_points": game['points'] + game['o:points'], "total_margin": game.get('margin'),
                "home_line": home_line, "away_line": away_line,
                "home_quarter_scores": json.dumps(home_qs) if home_qs is not None else None,
                "away_quarter_scores": json.dumps(away_qs) if away_qs is not None else None,
                "home_first_half_points": home_first_half, "away_first_half_points": away_first_half,
                "home_second_half_points": home_second_half, "away_second_half_points": away_second_half,
                "home_overtime_points": home_overtime, "away_overtime_points": away_overtime,
                "home_money_line": home_money, "away_money_line": away_money,
                "playoffs": bool(game.get('playoffs', 0)), "start_time": start_time, "total": total_value,
            }

            if existing:
                existing_game_id, existing_home_id, existing_away_id = existing
                if existing_home_id == home_team_id and existing_away_id == away_team_id:
                    conn.execute(text("""
                        UPDATE ncaaf_games SET
                            game_site = COALESCE(game_site, :game_site),
                            home_points = COALESCE(home_points, :home_points),
                            away_points = COALESCE(away_points, :away_points),
                            total_points = COALESCE(total_points, :total_points),
                            total_margin = COALESCE(total_margin, :total_margin),
                            home_line = COALESCE(home_line, :home_line),
                            away_line = COALESCE(away_line, :away_line),
                            home_quarter_scores = COALESCE(home_quarter_scores, :home_quarter_scores),
                            away_quarter_scores = COALESCE(away_quarter_scores, :away_quarter_scores),
                            home_first_half_points = COALESCE(home_first_half_points, :home_first_half_points),
                            away_first_half_points = COALESCE(away_first_half_points, :away_first_half_points),
                            home_second_half_points = COALESCE(home_second_half_points, :home_second_half_points),
                            away_second_half_points = COALESCE(away_second_half_points, :away_second_half_points),
                            home_overtime_points = COALESCE(home_overtime_points, :home_overtime_points),
                            away_overtime_points = COALESCE(away_overtime_points, :away_overtime_points),
                            home_money_line = COALESCE(home_money_line, :home_money_line),
                            away_money_line = COALESCE(away_money_line, :away_money_line),
                            playoffs = COALESCE(playoffs, :playoffs),
                            start_time = COALESCE(start_time, :start_time),
                            total = COALESCE(total, :total)
                        WHERE game_id = :game_id
                    """), {**params, "game_id": existing_game_id})
                    filled += 1
                else:
                    # Existing row has home/away reversed relative to this SDQL
                    # row (the other half of a neutral-site mirrored pair, or a
                    # pre-existing row seeded with the opposite orientation).
                    # Filling would mean writing this row's "home" values into
                    # the existing row's "away" columns -- a full field swap --
                    # which isn't worth the complexity/corruption risk for a
                    # betting-line-only fill. Leave it exactly as job 1 left it.
                    skipped_reversed += 1
            else:
                conn.execute(text("""
                    INSERT INTO ncaaf_games (
                        game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                        home_points, away_points, total_points, total_margin, home_line, away_line,
                        home_quarter_scores, away_quarter_scores, home_first_half_points, away_first_half_points,
                        home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                        home_money_line, away_money_line, playoffs, start_time, total
                    ) VALUES (
                        :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                        :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                        :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                        :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points,
                        :home_money_line, :away_money_line, :playoffs, :start_time, :total
                    )
                """), params)
                inserted += 1

        conn.commit()
        print(f"Done. Rows filled (existing, NULL-only): {filled}. Rows inserted fresh: {inserted}. "
              f"Rows skipped (reversed neutral-site duplicate): {skipped_reversed}.")
    except Exception as e:
        print(f"Error during SDQL fallback fill: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    fill_yesterdays_ncaaf_games_from_sdql()
