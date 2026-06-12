#!/usr/bin/env python3
"""
Seed yesterday's completed international soccer games into international_soccer_games.

Cron example:
  0 6 * * *  cd /path/to/get-stam-py && ./venv/bin/python jobs/intl_soccer_seed_yesterdays_games.py >> logs/intl_soccer_seed.log 2>&1
"""

import os
import sys
import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

SPORT_KEY = "soccer_fifa_world_cup"
LEAGUE    = "INTL"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Odds API team name → DB team name
# Only entries that differ are listed; all others pass through unchanged.
# ---------------------------------------------------------------------------
# DB team names match Odds API names exactly — no translation needed.
ODDS_API_TO_DB = {}


def _db_name(odds_api_name: str) -> str:
    return ODDS_API_TO_DB.get(odds_api_name, odds_api_name)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def get_yesterdays_scores(retries=3, delay=1):
    """Fetch completed international soccer games from yesterday."""
    print("Fetching international soccer scores from Odds API...")

    url = (
        f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/scores/"
        f"?daysFrom=3&apiKey={ODDS_API_KEY}"
    )

    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            games = response.json()

            yesterday_games = [
                g for g in games
                if g.get('completed') and g.get('scores')
            ]

            print(f"Found {len(yesterday_games)} completed international games (last 3 days)")
            return yesterday_games

        except requests.exceptions.RequestException as e:
            print(f"Error fetching scores (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise

    return []


def get_historical_odds(date_str, retries=3, delay=1):
    """Fetch historical Odds API data for the given date."""
    print(f"Fetching historical odds for {date_str}...")

    url = (
        f"https://api.the-odds-api.com/v4/historical/sports/{SPORT_KEY}/odds"
        f"?apiKey={ODDS_API_KEY}"
        f"&bookmakers=bovada"
        f"&markets=h2h,spreads,totals"
        f"&oddsFormat=american"
        f"&date={date_str}T00:00:00Z"
    )

    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            games = data.get('data', [])
            print(f"Found odds for {len(games)} games")
            return games

        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(f"Failed to fetch odds after {retries} attempts")
                return []

    return []


def parse_odds(odds_game):
    """Extract money lines, spreads, and totals from a Bovada odds record."""
    info = {
        'home_money_line': None, 'draw_money_line': None, 'away_money_line': None,
        'home_spread': None,     'away_spread': None,
        'total_over_point': None, 'total_over_price': None,
        'total_under_point': None, 'total_under_price': None,
    }

    bookmakers = odds_game.get('bookmakers') or []
    bovada = next((b for b in bookmakers if b['key'] == 'bovada'), None)
    if not bovada:
        return info

    home_team = odds_game['home_team']
    away_team = odds_game['away_team']

    for market in bovada.get('markets', []):
        key = market['key']
        outcomes = market.get('outcomes', [])

        if key == 'h2h':
            for o in outcomes:
                if o['name'] == home_team:
                    info['home_money_line'] = o['price']
                elif o['name'] == away_team:
                    info['away_money_line'] = o['price']
                elif o['name'] == 'Draw':
                    info['draw_money_line'] = o['price']

        elif key == 'spreads':
            for o in outcomes:
                if o['name'] == home_team:
                    info['home_spread'] = o['point']
                elif o['name'] == away_team:
                    info['away_spread'] = o['point']

        elif key == 'totals':
            for o in outcomes:
                if o['name'] == 'Over':
                    info['total_over_point'] = o['point']
                    info['total_over_price'] = o['price']
                elif o['name'] == 'Under':
                    info['total_under_point'] = o['point']
                    info['total_under_price'] = o['price']

    return info


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------

def seed_yesterdays_intl_soccer_games():
    print("Starting international soccer game seeding...")

    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    try:
        games = get_yesterdays_scores()
        if not games:
            print("No completed international games found for yesterday.")
            return

        # Collect unique dates from game commence_times and fetch odds for each
        unique_dates = sorted({g['commence_time'][:10] for g in games})
        odds_lookup = {}
        for date_str in unique_dates:
            for g in get_historical_odds(date_str):
                ht = g['home_team']
                at = g['away_team']
                odds_lookup[f"{ht}_{at}"] = g
                odds_lookup[f"{at}_{ht}"] = g

        # Load all INTL_SOCCER teams from DB
        teams_dict = {
            row['team_name']: row['team_id']
            for row in conn.execute(
                text("SELECT team_id, team_name FROM teams WHERE sport = 'INTL_SOCCER'")
            ).mappings()
        }
        print(f"Found {len(teams_dict)} INTL_SOCCER teams in database")

        # Auto-insert any teams not yet in the DB
        all_team_names = set()
        for game in games:
            all_team_names.add(_db_name(game['home_team']))
            all_team_names.add(_db_name(game['away_team']))

        new_teams = all_team_names - set(teams_dict.keys())
        for team_name in sorted(new_teams):
            conn.execute(
                text("INSERT INTO teams (team_name, sport) VALUES (:name, 'INTL_SOCCER')"),
                {'name': team_name}
            )
            print(f"  Auto-inserted new team: {team_name}")

        if new_teams:
            conn.commit()
            # Reload teams dict to pick up new IDs
            teams_dict = {
                row['team_name']: row['team_id']
                for row in conn.execute(
                    text("SELECT team_id, team_name FROM teams WHERE sport = 'INTL_SOCCER'")
                ).mappings()
            }

        inserted = 0

        for game in games:
            # Map Odds API names → DB names
            home_odds_name = game['home_team']
            away_odds_name = game['away_team']
            home_db_name = _db_name(home_odds_name)
            away_db_name = _db_name(away_odds_name)

            print(f"\nProcessing: {home_odds_name} vs {away_odds_name}")

            home_team_id = teams_dict.get(home_db_name)
            away_team_id = teams_dict.get(away_db_name)

            if not home_team_id or not away_team_id:
                print(
                    f"  Skipping — missing team ID. "
                    f"Home: '{home_db_name}' (id={home_team_id}), "
                    f"Away: '{away_db_name}' (id={away_team_id})"
                )
                continue

            # Extract scores
            home_goals = away_goals = None
            for score in game.get('scores', []):
                if score['name'] == home_odds_name:
                    home_goals = int(score['score'])
                elif score['name'] == away_odds_name:
                    away_goals = int(score['score'])

            if home_goals is None or away_goals is None:
                print("  Skipping — could not find scores for both teams")
                continue

            total_goals = home_goals + away_goals

            commence_time_utc = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            commence_time_et = commence_time_utc.astimezone(ZoneInfo("America/New_York"))
            game_date = commence_time_et.date()
            start_time = commence_time_et.time()

            # Idempotency check
            existing = conn.execute(text("""
                SELECT 1 FROM international_soccer_games
                WHERE odds_id = :odds_id
                   OR (game_date = :game_date
                       AND home_team_name = :home_name
                       AND away_team_name = :away_name)
            """), {
                'odds_id':   game['id'],
                'game_date': game_date,
                'home_name': home_db_name,
                'away_name': away_db_name,
            }).fetchone()

            if existing:
                print("  Already exists, skipping.")
                continue

            # Odds (keyed by Odds API names since that's what odds_lookup uses)
            matchup_key = f"{home_odds_name}_{away_odds_name}"
            odds_info = parse_odds(odds_lookup[matchup_key]) if matchup_key in odds_lookup else {
                'home_money_line': None, 'draw_money_line': None, 'away_money_line': None,
                'home_spread': None, 'away_spread': None,
                'total_over_point': None, 'total_over_price': None,
                'total_under_point': None, 'total_under_price': None,
            }
            if matchup_key not in odds_lookup:
                print(f"  No odds found for {home_odds_name} vs {away_odds_name}")

            try:
                conn.execute(text("""
                    INSERT INTO international_soccer_games (
                        odds_id, league, game_date,
                        home_team_id, away_team_id,
                        home_team_name, away_team_name,
                        home_goals, away_goals, total_goals,
                        home_money_line, draw_money_line, away_money_line,
                        home_spread, away_spread,
                        total_over_point, total_over_price,
                        total_under_point, total_under_price,
                        start_time
                    ) VALUES (
                        :odds_id, :league, :game_date,
                        :home_team_id, :away_team_id,
                        :home_name, :away_name,
                        :home_goals, :away_goals, :total_goals,
                        :home_ml, :draw_ml, :away_ml,
                        :home_spread, :away_spread,
                        :total_over_point, :total_over_price,
                        :total_under_point, :total_under_price,
                        :start_time
                    )
                """), {
                    'odds_id':          game['id'],
                    'league':           LEAGUE,
                    'game_date':        game_date,
                    'home_team_id':     home_team_id,
                    'away_team_id':     away_team_id,
                    'home_name':        home_db_name,
                    'away_name':        away_db_name,
                    'home_goals':       home_goals,
                    'away_goals':       away_goals,
                    'total_goals':      total_goals,
                    'home_ml':          odds_info['home_money_line'],
                    'draw_ml':          odds_info['draw_money_line'],
                    'away_ml':          odds_info['away_money_line'],
                    'home_spread':      odds_info['home_spread'],
                    'away_spread':      odds_info['away_spread'],
                    'total_over_point':  odds_info['total_over_point'],
                    'total_over_price':  odds_info['total_over_price'],
                    'total_under_point': odds_info['total_under_point'],
                    'total_under_price': odds_info['total_under_price'],
                    'start_time':        start_time,
                })
                print(f"  Inserted: {home_db_name} {home_goals}-{away_goals} {away_db_name}")
                inserted += 1

            except Exception as e:
                print(f"  Error inserting game: {e}")
                continue

        conn.commit()
        print(f"\nDone. Inserted {inserted} international soccer games.")

    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_intl_soccer_games()
