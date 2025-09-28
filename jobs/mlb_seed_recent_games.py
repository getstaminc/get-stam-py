#!/usr/bin/env python3

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load the DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

# SDQL credentials
SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def convert_start_time_to_time(start_time):
    """Convert SDQL start_time to SQL TIME format"""
    try:
        # Handle None case
        if start_time is None:
            return None
            
        # Convert to string if it's not already
        start_time_str = str(start_time)
        
        # SDQL returns times like '1530' (3:30 PM) or '730' (7:30 PM)
        if len(start_time_str) == 3:
            start_time_str = '0' + start_time_str  # Pad to 4 digits
        
        if len(start_time_str) == 4:
            hour = int(start_time_str[:2])
            minute = int(start_time_str[2:])
            return f"{hour:02d}:{minute:02d}:00"
        
        return None
    except (ValueError, TypeError):
        return None


def get_recent_mlb_games(retries=3, delay=1):
    """Fetch MLB games from yesterday"""
    print(f"Fetching MLB games from yesterday...")
    
    # Calculate yesterday's date in the required format (YYYYMMDD)
    yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y%m%d')
    
    print(f"Date: {yesterday}")
    
    # SDQL query for MLB games with all required fields (matching migration field names)
    sdql_url = f"https://s3.sportsdatabase.com/MLB/query"
    sdql_query = f"date,site,team,o:team,runs,o:runs,total,margin,line,o:line,playoffs,start time,_t,starter,o:starter,line F5,o:line F5,total F5,total over F5 odds,inning runs,o:inning runs@(site='home' or site='neutral') and date={yesterday}"

    headers = {
        'user': SDQL_USERNAME,
        'token': SDQL_TOKEN
    }

    data = {
        'sdql': sdql_query
    }
    
    for i in range(retries):
        try:
            response = requests.get(sdql_url, headers=headers, params=data)
            response.raise_for_status()
            try:
                result = response.json()
            except requests.exceptions.JSONDecodeError as e:
                print(f"Failed to decode JSON response: {response.text}")
                raise

            if result.get('headers') and result.get('groups'):
                headers = result['headers']
                rows = result['groups'][0]['columns']
                formatted_result = [dict(zip(headers, row)) for row in zip(*rows)]

                # Convert game_date to YYYY-MM-DD format and cast inning runs to JSON
                for game in formatted_result:
                    game['date'] = datetime.strptime(str(game['date']), '%Y%m%d').strftime('%Y-%m-%d')
                    game['inning runs'] = json.dumps(game['inning runs'])  # Cast to JSON
                    game['o:inning runs'] = json.dumps(game['o:inning runs'])  # Cast to JSON

                print(f"Successfully fetched {len(formatted_result)} games for {yesterday}.")
                return formatted_result
            else:
                print("No games found for yesterday.")
                return []
        except requests.exceptions.RequestException as e:
            print(f"SDQL request failed: {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
        except ValueError as e:
            print(f"Error parsing SDQL response JSON: {e}")
            return []


def seed_recent_games():
    """Main function to seed recent MLB games"""
    print("Starting MLB recent games seeding...")
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    # Fetch recent games
    games = get_recent_mlb_games()
    print(f"Processing {len(games)} games.")

    # Fetch all MLB teams from the database and store them in a dictionary
    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'MLB'")).mappings()
    }
    
    # Counter for new games
    new_games_count = 0

    for game in games:
        # Skip games with missing runs
        if game['runs'] is None or game['o:runs'] is None:
            print(f"Skipping game due to missing runs: {game}")
            continue

        # Use the dictionary for team lookups
        home_team_id = teams_dict.get(game['team'])
        away_team_id = teams_dict.get(game['o:team'])

        if home_team_id is None or away_team_id is None:
            print(f"Skipping game due to missing team ID - Home: '{game['team']}' (ID: {home_team_id}), Away: '{game['o:team']}' (ID: {away_team_id})")
            print(f"Available teams in database: {list(teams_dict.keys())}")
            continue

        # Handle start time conversion
        if game['start time'] is None:
            print(f"Game with missing start time: {game}")
            start_time = None
        else:
            if not isinstance(game['start time'], str):
                game['start time'] = str(game['start time'])
            start_time = convert_start_time_to_time(game['start time'])

        # Check if this exact game already exists OR if either team is already playing at this time
        existing_game = conn.execute(text("""
            SELECT 1 FROM mlb_games
            WHERE game_date = :game_date
            AND start_time = :start_time
            AND ((home_team_name = :home_team AND away_team_name = :away_team)
                 OR home_team_name = :home_team OR away_team_name = :home_team
                 OR home_team_name = :away_team OR away_team_name = :away_team)
        """), {
            'game_date': game['date'],
            'home_team': game['team'],
            'away_team': game['o:team'],
            'start_time': start_time
        }).fetchone()

        if existing_game:
            print(f"Skipping duplicate or conflicting game: {game['team']} vs {game['o:team']} on {game['date']} at {start_time}")
            continue

        # This is a new game, insert it
        print(f"Inserting new game: {game['team']} vs {game['o:team']} on {game['date']}")

        # Handle inning scores
        try:
            home_inning_scores_raw = game['inning runs']
            away_inning_scores_raw = game['o:inning runs']

            # Handle string-encoded JSON
            if isinstance(home_inning_scores_raw, str):
                home_inning_scores_raw = json.loads(home_inning_scores_raw)
            if isinstance(away_inning_scores_raw, str):
                away_inning_scores_raw = json.loads(away_inning_scores_raw)

            # Ensure final deserialization
            if isinstance(home_inning_scores_raw, str):
                home_inning_scores = json.loads(home_inning_scores_raw)
            else:
                home_inning_scores = home_inning_scores_raw

            if isinstance(away_inning_scores_raw, str):
                away_inning_scores = json.loads(away_inning_scores_raw)
            else:
                away_inning_scores = away_inning_scores_raw
            
            # Ensure inning scores are valid lists
            if not isinstance(home_inning_scores, list) or not isinstance(away_inning_scores, list):
                print(f"Skipping game due to invalid inning scores: {game}")
                continue

        except (TypeError, json.JSONDecodeError) as e:
            print(f"Invalid inning scores detected! Raw game data: {game}")
            print(f"Skipping game due to inning score error: {e}")
            continue

        # Calculate derived stats
        home_first_half_runs = sum(home_inning_scores[:5]) if len(home_inning_scores) >= 5 else None
        away_first_half_runs = sum(away_inning_scores[:5]) if len(away_inning_scores) >= 5 else None

        # Remaining runs after first 5 innings
        home_remaining_runs = sum(home_inning_scores[5:]) if len(home_inning_scores) > 5 else None
        away_remaining_runs = sum(away_inning_scores[5:]) if len(away_inning_scores) > 5 else None

        # Parse first 5 over/under odds if available (match migration logic)
        first_5_over_odds = None
        first_5_under_odds = None
        if game.get('total over F5 odds') and isinstance(game['total over F5 odds'], list) and len(game['total over F5 odds']) >= 2:
            first_5_over_odds = game['total over F5 odds'][0]
            first_5_under_odds = game['total over F5 odds'][1]
        elif game.get('total over F5 odds') is not None and game.get('total under F5 odds') is not None:
            first_5_over_odds = game.get('total over F5 odds')
            first_5_under_odds = game.get('total under F5 odds')

        # Insert new game with retry logic
        for retry in range(3):
            try:
                result = conn.execute(text("""
                    INSERT INTO mlb_games (
                        game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name, 
                        home_runs, away_runs, total, total_runs, total_margin, home_line, away_line,
                        home_money_line, away_money_line, playoffs, start_time, 
                        home_first_5_line, away_first_5_line, total_first_5, 
                        first_5_over_odds, first_5_under_odds,
                        home_starting_pitcher, away_starting_pitcher,
                        home_inning_runs, away_inning_runs,
                        home_first_5_runs, away_first_5_runs, 
                        home_remaining_runs, away_remaining_runs
                    ) VALUES (
                        :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                        :home_runs, :away_runs, :total, :total_runs, :total_margin, :home_line, :away_line,
                        :home_money_line, :away_money_line, :playoffs, :start_time,
                        :home_first_5_line, :away_first_5_line, :total_first_5,
                        :first_5_over_odds, :first_5_under_odds,
                        :home_starting_pitcher, :away_starting_pitcher,
                        :home_inning_runs, :away_inning_runs,
                        :home_first_5_runs, :away_first_5_runs,
                        :home_remaining_runs, :away_remaining_runs
                    )
                """), {
                    'game_date': game['date'],
                    'game_site': game['site'],
                    'home_team_id': home_team_id,
                    'away_team_id': away_team_id,
                    'home_team_name': game['team'],
                    'away_team_name': game['o:team'],
                    'home_runs': game['runs'],
                    'away_runs': game['o:runs'],
                    'total': game['total'],
                    'total_runs': game['runs'] + game['o:runs'],
                    'total_margin': game['margin'],
                    'home_line': game['line'],
                    'away_line': game['o:line'],
                    'home_money_line': game.get('money line'),
                    'away_money_line': game.get('o:money line'),
                    'playoffs': bool(game.get('playoffs', 0)),
                    'start_time': start_time,
                    'home_first_5_line': game.get('line F5'),
                    'away_first_5_line': game.get('o:line F5'),
                    'total_first_5': game.get('total F5'),
                    'first_5_over_odds': first_5_over_odds,
                    'first_5_under_odds': first_5_under_odds,
                    'home_starting_pitcher': game.get('starter'),
                    'away_starting_pitcher': game.get('o:starter'),
                    'home_inning_runs': json.dumps(home_inning_scores),
                    'away_inning_runs': json.dumps(away_inning_scores),
                    'home_first_5_runs': home_first_half_runs,
                    'away_first_5_runs': away_first_half_runs,
                    'home_remaining_runs': home_remaining_runs,
                    'away_remaining_runs': away_remaining_runs
                })
                
                print(f"Rows affected: {result.rowcount}")
                new_games_count += 1
                break  # Success, exit retry loop
                
            except Exception as e:
                if retry < 2:  # If not last retry
                    print(f"Database insert failed (attempt {retry + 1}), retrying: {e}")
                    time.sleep(5)  # Wait before retry
                else:
                    print(f"Database insert failed after 3 attempts, skipping game: {e}")
                    continue  # Skip this game and continue with next

    # Commit the transaction
    conn.commit()
    print(f"Transaction committed successfully. New games: {new_games_count}")
    conn.close()
    print("MLB recent games seeding completed successfully.")


if __name__ == "__main__":
    seed_recent_games()
