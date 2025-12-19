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
ODDS_API_KEY = 'e143ef401675904470a5b72e6145091a'

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def get_yesterdays_afcon_scores(retries=3, delay=1):
    """Fetch AFCON scores from the last 3 days to get yesterday's completed games"""
    print("Fetching AFCON scores from Odds API...")

    url = f"https://api.the-odds-api.com/v4/sports/soccer_africa_cup_of_nations/scores/?daysFrom=3&apiKey={ODDS_API_KEY}"

    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            games = response.json()
            
            # Filter for completed games from yesterday only
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            yesterday_games = []
            for game in games:
                if game.get('completed') and game.get('scores'):
                    game_date = game['commence_time'][:10]  # Extract YYYY-MM-DD
                    if game_date == yesterday:
                        yesterday_games.append(game)

            print(f"Found {len(yesterday_games)} completed AFCON games from yesterday ({yesterday})")
            return yesterday_games
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching scores (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
    
    return []


def get_historical_odds_for_date(date_str, retries=3, delay=1):
    """Fetch historical odds for a specific date"""
    print(f"Fetching historical odds for {date_str}...")
    
    # Format date for API (needs to be in ISO format with time)
    url = f"https://api.the-odds-api.com/v4/historical/sports/soccer_africa_cup_of_nations/odds?apiKey={ODDS_API_KEY}&regions=us,uk,eu&bookmakers=bovada&markets=h2h,spreads,totals&oddsFormat=american&date={date_str}T00:00:00Z"

    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            odds_data = response.json()
            
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
        'draw_money_line': None,
        'away_money_line': None,
        'home_spread': None,
        'away_spread': None,
        'total_over_point': None,
        'total_over_price': None,
        'total_under_point': None,
        'total_under_price': None
    }
    
    if not odds_game.get('bookmakers'):
        return odds_info
    
    # Use Bovada bookmaker data
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
            # Money lines
            for outcome in market['outcomes']:
                if outcome['name'] == home_team:
                    odds_info['home_money_line'] = outcome['price']
                elif outcome['name'] == away_team:
                    odds_info['away_money_line'] = outcome['price']
                elif outcome['name'] == 'Draw':
                    odds_info['draw_money_line'] = outcome['price']
        
        elif market['key'] == 'spreads':
            # Spreads
            for outcome in market['outcomes']:
                if outcome['name'] == home_team:
                    odds_info['home_spread'] = outcome['point']
                elif outcome['name'] == away_team:
                    odds_info['away_spread'] = outcome['point']
        
        elif market['key'] == 'totals':
            # Totals
            for outcome in market['outcomes']:
                if outcome['name'] == 'Over':
                    odds_info['total_over_point'] = outcome['point']
                    odds_info['total_over_price'] = outcome['price']
                elif outcome['name'] == 'Under':
                    odds_info['total_under_point'] = outcome['point']
                    odds_info['total_under_price'] = outcome['price']
    
    return odds_info


def seed_yesterdays_afcon_games():
    """Main function to seed yesterday's AFCON games"""
    print("Starting AFCON game seeding...")
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Get yesterday's completed games
        games = get_yesterdays_afcon_scores()
        
        if not games:
            print("No completed AFCON games found for yesterday")
            return
        
        # Get yesterday's date for odds lookup
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Get historical odds for yesterday
        odds_data = get_historical_odds_for_date(yesterday)
        
        # Create a lookup dictionary for odds by team matchup instead of game ID
        odds_lookup = {}
        for game in odds_data:
            # Create a key using both possible team combinations (home vs away)
            home_vs_away = f"{game['home_team']}_{game['away_team']}"
            away_vs_home = f"{game['away_team']}_{game['home_team']}"
            odds_lookup[home_vs_away] = game
            odds_lookup[away_vs_home] = game
        
        # Fetch all soccer teams from the database
        teams_dict = {
            team['team_name']: team['team_id']
            for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'SOCCER'")).mappings()
        }
        
        print(f"Found {len(teams_dict)} soccer teams in database")
        
        new_games_count = 0
        
        for game in games:
            print(f"\nProcessing game: {game['home_team']} vs {game['away_team']}")
            
            # Get team IDs
            home_team_id = teams_dict.get(game['home_team'])
            away_team_id = teams_dict.get(game['away_team'])
            
            if home_team_id is None or away_team_id is None:
                print(f"Skipping game - missing team IDs. Home: {game['home_team']} (ID: {home_team_id}), Away: {game['away_team']} (ID: {away_team_id})")
                continue
            
            # Extract scores by matching team names
            home_goals = None
            away_goals = None
            
            for score in game['scores']:
                if score['name'] == game['home_team']:
                    home_goals = int(score['score'])
                elif score['name'] == game['away_team']:
                    away_goals = int(score['score'])
            
            if home_goals is None or away_goals is None:
                print(f"Skipping game - could not find scores for both teams")
                continue
                
            total_goals = home_goals + away_goals
            
            # Extract game date and time
            commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            game_date = commence_time.date()
            start_time = commence_time.time()
            
            # Check if game already exists
            existing_game = conn.execute(text("""
                SELECT 1 FROM soccer_games 
                WHERE odds_id = :odds_id OR 
                      (game_date = :game_date AND home_team_name = :home_team AND away_team_name = :away_team)
            """), {
                'odds_id': game['id'],
                'game_date': game_date,
                'home_team': game['home_team'],
                'away_team': game['away_team']
            }).fetchone()
            
            if existing_game:
                print(f"Game already exists, skipping...")
                continue
            
            # Get odds data for this game by matching team names
            team_matchup = f"{game['home_team']}_{game['away_team']}"
            odds_info = {}
            if team_matchup in odds_lookup:
                odds_info = parse_odds_data(odds_lookup[team_matchup])
                print(f"Found odds data for game by team matchup")
            else:
                print(f"No odds data found for matchup: {game['home_team']} vs {game['away_team']}")
                # Initialize with None values
                odds_info = {
                    'home_money_line': None, 'draw_money_line': None, 'away_money_line': None,
                    'home_spread': None, 'away_spread': None,
                    'total_over_point': None, 'total_over_price': None,
                    'total_under_point': None, 'total_under_price': None
                }
            
            # Insert the game
            try:
                result = conn.execute(text("""
                    INSERT INTO soccer_games (
                        odds_id, league, game_date, home_team_id, away_team_id,
                        home_team_name, away_team_name, home_goals, away_goals, total_goals,
                        home_money_line, draw_money_line, away_money_line,
                        home_spread, away_spread,
                        total_over_point, total_over_price, total_under_point, total_under_price,
                        start_time
                    ) VALUES (
                        :odds_id, :league, :game_date, :home_team_id, :away_team_id,
                        :home_team_name, :away_team_name, :home_goals, :away_goals, :total_goals,
                        :home_money_line, :draw_money_line, :away_money_line,
                        :home_spread, :away_spread,
                        :total_over_point, :total_over_price, :total_under_point, :total_under_price,
                        :start_time
                    )
                """), {
                    'odds_id': game['id'],
                    'league': 'AFCON',
                    'game_date': game_date,
                    'home_team_id': home_team_id,
                    'away_team_id': away_team_id,
                    'home_team_name': game['home_team'],
                    'away_team_name': game['away_team'],
                    'home_goals': home_goals,
                    'away_goals': away_goals,
                    'total_goals': total_goals,
                    'home_money_line': odds_info['home_money_line'],
                    'draw_money_line': odds_info['draw_money_line'],
                    'away_money_line': odds_info['away_money_line'],
                    'home_spread': odds_info['home_spread'],
                    'away_spread': odds_info['away_spread'],
                    'total_over_point': odds_info['total_over_point'],
                    'total_over_price': odds_info['total_over_price'],
                    'total_under_point': odds_info['total_under_point'],
                    'total_under_price': odds_info['total_under_price'],
                    'start_time': start_time
                })
                
                print(f"Successfully inserted game: {game['home_team']} {home_goals}-{away_goals} {game['away_team']}")
                new_games_count += 1
                
            except Exception as e:
                print(f"Error inserting game: {e}")
                continue
        
        # Commit the transaction
        conn.commit()
        print(f"\nSuccessfully seeded {new_games_count} AFCON games from yesterday")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_afcon_games()
