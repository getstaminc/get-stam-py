#!/usr/bin/env python3

import os
import sys
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
if not ODDS_API_KEY:
    raise RuntimeError("ODDS_API_KEY not set in environment variables.")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import importlib.util

shared_utils_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared_utils.py')
spec = importlib.util.spec_from_file_location('shared_utils', shared_utils_path)
shared_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared_utils)


def get_yesterdays_mlb_scores(retries=3, delay=1):
    """Fetch completed MLB games from yesterday via Odds API scores endpoint."""
    print("Fetching MLB scores from Odds API...")
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/scores/?daysFrom=3&apiKey={ODDS_API_KEY}&dateFormat=iso"

    eastern_tz = pytz.timezone('US/Eastern')
    yesterday = (datetime.now(eastern_tz) - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Filtering for Eastern date: {yesterday}")

    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            games = response.json()
            yesterday_games = []
            for game in games:
                if game.get('completed') and game.get('scores'):
                    commence_time_utc = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                    commence_time_eastern = shared_utils.convert_to_eastern(commence_time_utc)
                    if str(commence_time_eastern.date()) == yesterday:
                        yesterday_games.append(game)

            print(f"Found {len(yesterday_games)} completed MLB games from yesterday ({yesterday})")
            return yesterday_games, yesterday
        except requests.exceptions.RequestException as e:
            print(f"Error fetching scores (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
    return [], None


def get_historical_odds_at_time(snapshot_time, retries=3, delay=1):
    """Fetch historical odds snapshot at a specific UTC datetime."""
    time_str = snapshot_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f"  Fetching historical odds at {time_str}...")
    url = (
        f"https://api.the-odds-api.com/v4/historical/sports/baseball_mlb/odds/"
        f"?apiKey={ODDS_API_KEY}&regions=us&bookmakers=draftkings"
        f"&markets=h2h,spreads,totals&oddsFormat=american&date={time_str}"
    )

    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            odds_data = response.json()
            if 'data' in odds_data:
                return odds_data['data']
            return []
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching odds (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                print(f"  Failed to fetch odds after {retries} attempts")
                return []
    return []


def build_odds_lookup(games):
    """
    Build an odds lookup dict keyed by event ID.
    For each unique commence_time, fetch odds 1 hour before that time.
    Games sharing a start time share one API call.
    """
    # Collect unique commence times
    unique_times = sorted(set(
        datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00'))
        for g in games
    ))

    print(f"Fetching pre-game odds for {len(unique_times)} unique start time(s)...")
    odds_lookup = {}

    for commence_utc in unique_times:
        snapshot_time = commence_utc - timedelta(hours=1)
        data = get_historical_odds_at_time(snapshot_time)
        for odds_game in data:
            odds_lookup[odds_game['id']] = odds_game
        time.sleep(0.5)  # be polite to the API

    print(f"Odds lookup built for {len(odds_lookup)} event(s)")
    return odds_lookup


def parse_odds(odds_game):
    """Extract h2h and totals odds from a DraftKings bookmaker entry."""
    result = {
        'home_money_line': None,
        'away_money_line': None,
        'home_line': None,
        'away_line': None,
        'total': None,
    }

    if not odds_game.get('bookmakers'):
        return result

    draftkings = next((b for b in odds_game['bookmakers'] if b['key'] == 'draftkings'), None)
    if not draftkings:
        return result

    home_team = odds_game['home_team']
    away_team = odds_game['away_team']

    for market in draftkings.get('markets', []):
        if market['key'] == 'h2h':
            for outcome in market['outcomes']:
                if outcome['name'] == home_team:
                    result['home_money_line'] = outcome['price']
                    result['home_line'] = outcome['price']
                elif outcome['name'] == away_team:
                    result['away_money_line'] = outcome['price']
                    result['away_line'] = outcome['price']
        elif market['key'] == 'totals':
            over = next((o for o in market['outcomes'] if o['name'] == 'Over'), None)
            if over:
                result['total'] = over.get('point')

    return result


def seed_yesterdays_mlb_games():
    """Main function to seed yesterday's MLB games from the Odds API."""
    print("Starting MLB games seeding (Odds API)...")

    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    try:
        games, yesterday = get_yesterdays_mlb_scores()
        if not games:
            print("No completed MLB games found for yesterday")
            return

        odds_lookup = build_odds_lookup(games)

        teams_dict = {
            row['team_name']: row['team_id']
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'MLB'")).mappings()
        }
        print(f"Loaded {len(teams_dict)} MLB teams from database")

        new_games_count = 0
        skipped = []

        for game in games:
            event_id = game['id']
            home_team_full = game['home_team']
            away_team_full = game['away_team']

            db_home = shared_utils.convert_team_name(home_team_full)
            db_away = shared_utils.convert_team_name(away_team_full)

            home_team_id = teams_dict.get(db_home)
            away_team_id = teams_dict.get(db_away)

            if home_team_id is None or away_team_id is None:
                reason = f"Missing team ID — home: '{home_team_full}' → '{db_home}' ({home_team_id}), away: '{away_team_full}' → '{db_away}' ({away_team_id})"
                print(f"  Skipping: {reason}")
                skipped.append({'home': home_team_full, 'away': away_team_full, 'reason': reason})
                continue

            # Extract scores
            home_runs = None
            away_runs = None
            for score in game['scores']:
                score_name = shared_utils.convert_team_name(score['name'])
                if score_name == db_home:
                    home_runs = int(score['score'])
                elif score_name == db_away:
                    away_runs = int(score['score'])

            if home_runs is None or away_runs is None:
                reason = "Could not parse scores for both teams"
                print(f"  Skipping {home_team_full} vs {away_team_full}: {reason}")
                skipped.append({'home': home_team_full, 'away': away_team_full, 'reason': reason})
                continue

            # Timezone conversion
            commence_utc = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            commence_eastern = shared_utils.convert_to_eastern(commence_utc)
            game_date = commence_eastern.date()
            start_time = commence_eastern.time()

            # Derived fields
            total_runs = home_runs + away_runs
            total_margin = home_runs - away_runs

            # Odds
            odds = parse_odds(odds_lookup[event_id]) if event_id in odds_lookup else {
                'home_money_line': None, 'away_money_line': None,
                'home_line': None, 'away_line': None, 'total': None,
            }
            if event_id not in odds_lookup:
                print(f"  No odds found for event {event_id} ({db_home} vs {db_away})")

            # Deduplication
            existing = conn.execute(text(
                "SELECT 1 FROM mlb_games WHERE odds_event_id = :event_id"
            ), {'event_id': event_id}).fetchone()

            if existing:
                print(f"  Already exists: {db_home} vs {db_away} on {game_date}")
                continue

            print(f"  Inserting: {db_home} {home_runs}-{away_runs} {db_away} on {game_date}")

            conn.execute(text("""
                INSERT INTO mlb_games (
                    game_date, game_site, home_team_id, away_team_id,
                    home_team_name, away_team_name,
                    home_runs, away_runs, total_runs, total_margin,
                    total, home_line, away_line, home_money_line, away_money_line,
                    playoffs, start_time, odds_event_id
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id,
                    :home_team_name, :away_team_name,
                    :home_runs, :away_runs, :total_runs, :total_margin,
                    :total, :home_line, :away_line, :home_money_line, :away_money_line,
                    :playoffs, :start_time, :odds_event_id
                )
            """), {
                'game_date': game_date,
                'game_site': 'home',
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_team_name': db_home,
                'away_team_name': db_away,
                'home_runs': home_runs,
                'away_runs': away_runs,
                'total_runs': total_runs,
                'total_margin': total_margin,
                'total': odds['total'],
                'home_line': odds['home_line'],
                'away_line': odds['away_line'],
                'home_money_line': odds['home_money_line'],
                'away_money_line': odds['away_money_line'],
                'playoffs': False,
                'start_time': start_time,
                'odds_event_id': event_id,
            })
            new_games_count += 1

        conn.commit()
        print(f"\nDone. Inserted {new_games_count} game(s). Skipped {len(skipped)}.")
        if skipped:
            print("Skipped games:")
            for s in skipped:
                print(f"  {s['home']} vs {s['away']}: {s['reason']}")

    except Exception as e:
        print(f"Fatal error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_mlb_games()
