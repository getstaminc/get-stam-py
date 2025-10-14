#!/usr/bin/env python3

import os
import sys
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load the DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

# Odds API credentials
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
if not ODDS_API_KEY:
    raise RuntimeError("ODDS_API_KEY not set in environment variables.")

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from sqlalchemy import create_engine, text
# Import convert_team_name from shared_utils
import importlib.util
shared_utils_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared_utils.py')
spec = importlib.util.spec_from_file_location('shared_utils', shared_utils_path)
shared_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared_utils)

def get_yesterdays_nhl_scores(retries=3, delay=1):
    """Fetch NHL scores from the last 2 days to get yesterday's completed games"""
    print("Fetching NHL scores from Odds API...")
    url = f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/scores/?daysFrom=3&apiKey={ODDS_API_KEY}&dateFormat=iso"
    print(url)
    
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            games = response.json()
            print("\n[DEBUG] Full games data fetched from API:")
            print(json.dumps(games, indent=2))
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
            yesterday = '2025-10-11'

            print(f"Yesterday: {yesterday}")
            yesterday_games = []
            for game in games:
                if game.get('completed') and game.get('scores'):
                    # Convert commence_time to Eastern and compare date
                    commence_time_utc = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                    commence_time_eastern = shared_utils.convert_to_eastern(commence_time_utc)
                    eastern_date = str(commence_time_eastern.date())
                    if eastern_date == yesterday:
                        yesterday_games.append(game)
            print(f"Found {len(yesterday_games)} completed NHL games from yesterday ({yesterday})")
            return yesterday_games
        except requests.exceptions.RequestException as e:
            print(f"Error fetching scores (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
    return []

def get_historical_odds_for_date(date_str, retries=3, delay=1):
    """Fetch historical odds for a specific date for NHL"""
    print(f"Fetching historical odds for {date_str}...")
    url = f"https://api.the-odds-api.com/v4/historical/sports/icehockey_nhl/odds?apiKey={ODDS_API_KEY}&regions=us&bookmakers=draftkings&markets=h2h,spreads,totals&oddsFormat=american&date={date_str}T00:00:00Z"
    print(url)
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            odds_data = response.json()
            print("\n[DEBUG] Full odds data fetched from API:")
            print(json.dumps(odds_data, indent=2))
            if 'data' in odds_data:
                print(f"Found odds data for {len(odds_data['data'])} games")
                return odds_data['data']
            else:
                print("No odds data found")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                print(f"Failed to fetch odds after {retries} attempts")
                return []
    return []

def parse_odds_data(odds_game):
    """Extract odds information from a game's odds data"""
    odds_info = {
        'home_money_line': None,
        'away_money_line': None
    }
    if not odds_game.get('bookmakers'):
        return odds_info
    bovada_data = None
    for bookmaker in odds_game['bookmakers']:
        if bookmaker['key'] == 'bovada':
            bovada_data = bookmaker
            break
    if not bovada_data or not bovada_data.get('markets'):
        return odds_info
    home_team = odds_game['home_team']
    away_team = odds_game['away_team']
    for market in bovada_data['markets']:
        if market['key'] == 'h2h':
            for outcome in market['outcomes']:
                if outcome['name'] == home_team:
                    odds_info['home_money_line'] = outcome['price']
                elif outcome['name'] == away_team:
                    odds_info['away_money_line'] = outcome['price']
    return odds_info

def seed_yesterdays_nhl_games():
    """Main function to seed yesterday's NHL games"""
    print("Starting NHL game seeding...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        games = get_yesterdays_nhl_scores()
        if not games:
            print("No completed NHL games found for yesterday")
            return
        yesterday = '2025-10-11'
        odds_data = get_historical_odds_for_date(yesterday)
        odds_lookup = {}
        for game in odds_data:
            home_vs_away = f"{game['home_team']}_{game['away_team']}"
            away_vs_home = f"{game['away_team']}_{game['home_team']}"
            odds_lookup[home_vs_away] = game
            odds_lookup[away_vs_home] = game
        teams_dict = {
            team['team_name']: team['team_id']
            for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NHL' ")).mappings()
        }
        print(f"Found {len(teams_dict)} NHL teams in database")
        new_games_count = 0
        inserted_games = []
        skipped_games = []
        for game in games:
            print(f"\nProcessing game: {game['home_team']} vs {game['away_team']}")
            print(f"  Raw commence_time (UTC): {game['commence_time']}")
            commence_time_utc = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            commence_time_eastern = shared_utils.convert_to_eastern(commence_time_utc)
            print(f"  Commence time Eastern: {commence_time_eastern} (date: {commence_time_eastern.date()})")
            db_home_team = shared_utils.convert_team_name(game['home_team'])
            db_away_team = shared_utils.convert_team_name(game['away_team'])
            print(f"  DB home: {db_home_team}, DB away: {db_away_team}")
            home_team_id = teams_dict.get(db_home_team)
            away_team_id = teams_dict.get(db_away_team)
            print(f"  Home team ID: {home_team_id}, Away team ID: {away_team_id}")
            if home_team_id is None or away_team_id is None:
                reason = f"Missing team IDs. Home: {game['home_team']} (DB: {db_home_team}, ID: {home_team_id}), Away: {game['away_team']} (DB: {db_away_team}, ID: {away_team_id})"
                print(f"Skipping game - {reason}")
                skipped_games.append({
                    'home': game['home_team'],
                    'away': game['away_team'],
                    'reason': reason
                })
                continue
            home_goals = None
            away_goals = None
            for score in game['scores']:
                score_name = shared_utils.convert_team_name(score['name'])
                print(f"    Score: {score['name']} (DB: {score_name}) = {score['score']}")
                if score_name == db_home_team:
                    home_goals = int(score['score'])
                elif score_name == db_away_team:
                    away_goals = int(score['score'])
            print(f"  home_goals: {home_goals}, away_goals: {away_goals}")
            if home_goals is None or away_goals is None:
                reason = "Could not find scores for both teams"
                print(f"Skipping game - {reason}")
                skipped_games.append({
                    'home': game['home_team'],
                    'away': game['away_team'],
                    'reason': reason
                })
                continue
            game_date = commence_time_eastern.date()
            if str(game_date) != yesterday:
                reason = f"Commence date in Eastern ({game_date}) does not match yesterday ({yesterday})"
                print(f"Skipping game - {reason}")
                skipped_games.append({
                    'home': game['home_team'],
                    'away': game['away_team'],
                    'reason': reason
                })
                continue
            existing_game = conn.execute(text("""
                SELECT 1 FROM nhl_games 
                WHERE game_date = :game_date AND home_team_name = :home_team AND away_team_name = :away_team
            """), {
                'game_date': game_date,
                'home_team': db_home_team,
                'away_team': db_away_team
            }).fetchone()
            if existing_game:
                reason = "Game already exists"
                print(f"Game already exists, skipping...")
                skipped_games.append({
                    'home': game['home_team'],
                    'away': game['away_team'],
                    'reason': reason
                })
                continue
            team_matchup = f"{game['home_team']}_{game['away_team']}"
            odds_info = {}
            if team_matchup in odds_lookup:
                odds_info = parse_odds_data(odds_lookup[team_matchup])
                print(f"Found odds data for game by team matchup")
            else:
                print(f"No odds data found for matchup: {game['home_team']} vs {game['away_team']}")
                odds_info = {
                    'home_money_line': None,
                    'away_money_line': None
                }
            try:
                result = conn.execute(text("""
                    INSERT INTO nhl_games (
                        game_date, game_site, home_team_id, away_team_id,
                        home_team_name, away_team_name, home_goals, away_goals,
                        home_money_line, away_money_line
                    ) VALUES (
                        :game_date, :game_site, :home_team_id, :away_team_id,
                        :home_team_name, :away_team_name, :home_goals, :away_goals,
                        :home_money_line, :away_money_line
                    )
                """), {
                    'game_date': game_date,
                    'game_site': 'home',
                    'home_team_id': home_team_id,
                    'away_team_id': away_team_id,
                    'home_team_name': db_home_team,
                    'away_team_name': db_away_team,
                    'home_goals': home_goals,
                    'away_goals': away_goals,
                    'home_money_line': odds_info['home_money_line'],
                    'away_money_line': odds_info['away_money_line']
                })
                print(f"Successfully inserted game: {db_home_team} {home_goals}-{away_goals} {db_away_team}")
                inserted_games.append({
                    'home': db_home_team,
                    'away': db_away_team,
                    'home_goals': home_goals,
                    'away_goals': away_goals
                })
                new_games_count += 1
            except Exception as e:
                reason = f"Error inserting game: {e}"
                print(f"Error inserting game: {e}")
                skipped_games.append({
                    'home': game['home_team'],
                    'away': game['away_team'],
                    'reason': reason
                })
                continue
        conn.commit()
        print(f"\nSuccessfully seeded {new_games_count} NHL games from yesterday")
        print("\n[DEBUG] Inserted games:")
        print(json.dumps(inserted_games, indent=2))
        print("\n[DEBUG] Skipped games:")
        print(json.dumps(skipped_games, indent=2))
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    seed_yesterdays_nhl_games()
