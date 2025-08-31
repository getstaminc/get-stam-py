"""Seed yesterday's NFL games into the nfl_games table."""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import json
import os
import time

# Load environment variables from .env file
load_dotenv()

# Load the DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

# SDQL credentials
SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def convert_start_time_to_time(start_time: str) -> str:
    """
    Convert military time (e.g., '1838') to a string in 'HH:MM:SS' format.
    """
    try:
        # Handle specific invalid cases where start_time starts with "243"
        if start_time.startswith("243"):
            print(f"Correcting invalid start time: {start_time} to 1230")
            start_time = "1230"

        # Handle specific invalid cases where start_time starts with "245"
        elif start_time.startswith("245") or start_time.startswith("244"):
            print(f"Correcting invalid start time: {start_time} to 1300")
            start_time = "1300"

        # Convert to 'HH:MM:SS' format
        return datetime.strptime(start_time, "%H%M").strftime("%H:%M:%S")
    except ValueError as e:
        raise ValueError(f"Invalid start time format: {start_time}. Error: {e}")

def get_yesterdays_games(retries=3, delay=1):
    """Fetch all of yesterday's NFL games from the SDQL API."""
    sdql_url = f"https://s3.sportsdatabase.com/NFL/query"
    print(f"Connecting to database: {DATABASE_URL}")
    
    # Calculate yesterday's date in the required format (YYYYMMDD)
    yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y%m%d')
    
    # SDQL query to fetch all games for yesterday (including neutral games to avoid duplicates)
    sdql_query = f"date,site,team,o:team,points,o:points,total,margin,line,o:line,quarter scores,o:quarter scores,playoffs,money line,o:money line,start time,_t@(site='home' or site='neutral') and date={yesterday}"

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

                # Convert game_date to YYYY-MM-DD format and cast quarter scores to JSON
                for game in formatted_result:
                    game['date'] = datetime.strptime(str(game['date']), '%Y%m%d').strftime('%Y-%m-%d')
                    game['quarter scores'] = json.dumps(game['quarter scores'])  # Cast to JSON
                    game['o:quarter scores'] = json.dumps(game['o:quarter scores'])  # Cast to JSON

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

def seed_yesterdays_games():
    """Seed yesterday's NFL games into the nfl_games table."""
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    # Fetch all games for yesterday
    games = get_yesterdays_games()
    print(f"Processing {len(games)} games.")

    # Fetch all NFL teams from the database and store them in a dictionary
    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NFL'")).mappings()
    }

    for game in games:
        # Skip games with missing points
        if game['points'] is None or game['o:points'] is None:
            print(f"Skipping game due to missing points: {game}")
            continue

        # Skip games with a team of "Bulls" (from migration logic)
        if game['team'] == "Bulls" or game['o:team'] == "Bulls":
            print(f"Skipping non-NFL game: {game}")
            continue

        # Use the dictionary for lookups
        home_team_id = teams_dict.get(game['team'])
        away_team_id = teams_dict.get(game['o:team'])

        if home_team_id is None or away_team_id is None:
            print(f"Skipping game due to missing team ID: {game}")
            continue

        # Check if start time is None or not a string
        if game['start time'] is None:
            print(f"Game with missing start time: {game}")
            start_time = None  # Insert None for missing start time
        else:
            if not isinstance(game['start time'], str):
                print(f"Game with start time format int: {game}")
                game['start time'] = str(game['start time'])  # Convert to string

            # Convert start_time to a string in 'HH:MM:SS' format
            start_time = convert_start_time_to_time(game['start time'])

        # Skip records with missing required fields (from migration logic)
        if game['total'] is None or game['margin'] is None or game['line'] is None or game['o:line'] is None:
            print(f"Skipping game due to missing required fields: {game}")
            continue

        print(f"Inserting game: {game['team']} vs {game['o:team']} on {game['date']}")

        # Check if either team has already played on this date (handles duplicates from neutral games)
        existing_game = conn.execute(text("""
            SELECT 1 FROM nfl_games
            WHERE game_date = :game_date
            AND (home_team_name = :team1 OR away_team_name = :team1 
                 OR home_team_name = :team2 OR away_team_name = :team2)
        """), {
            'game_date': game['date'],
            'team1': game['team'],
            'team2': game['o:team']
        }).fetchone()

        if existing_game:
            print(f"Skipping duplicate - one of these teams already played on {game['date']}: {game['team']} vs {game['o:team']}")
            continue

        # Deserialize quarter scores back to lists with NFL-specific handling
        try:
            home_quarter_scores_raw = game['quarter scores']
            away_quarter_scores_raw = game['o:quarter scores']

            # Handle extra quotes around JSON strings (from migration logic)
            if isinstance(home_quarter_scores_raw, str):
                home_quarter_scores_raw = json.loads(home_quarter_scores_raw)
            if isinstance(away_quarter_scores_raw, str):
                away_quarter_scores_raw = json.loads(away_quarter_scores_raw)

            # Ensure the final deserialization in case of double quotes
            if isinstance(home_quarter_scores_raw, str):
                home_quarter_scores = json.loads(home_quarter_scores_raw)
            else:
                home_quarter_scores = home_quarter_scores_raw

            if isinstance(away_quarter_scores_raw, str):
                away_quarter_scores = json.loads(away_quarter_scores_raw)
            else:
                away_quarter_scores = away_quarter_scores_raw
            
            # Ensure quarter scores are valid lists
            if not isinstance(home_quarter_scores, list) or not isinstance(away_quarter_scores, list):
                print(f"Skipping game due to invalid quarter scores: {game}")
                continue

        except (TypeError, json.JSONDecodeError) as e:
            print(f"Invalid quarter scores detected! Raw game data: {game}")
            print(f"Skipping game due to quarter score error: {e}")
            continue

        # Calculate first half points
        home_first_half_points = sum(home_quarter_scores[:2])
        away_first_half_points = sum(away_quarter_scores[:2])

        # Calculate second half points
        home_second_half_points = sum(home_quarter_scores[2:4])
        away_second_half_points = sum(away_quarter_scores[2:4])

        # Calculate overtime points (if any)
        home_overtime_points = home_quarter_scores[4] if len(home_quarter_scores) > 4 else None
        away_overtime_points = away_quarter_scores[4] if len(away_quarter_scores) > 4 else None

        # Insert data into nfl_games table with retry logic
        for retry in range(3):
            try:
                result = conn.execute(text("""
                    INSERT INTO nfl_games (
                        game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name, home_points, away_points,
                        total_points, total_margin, home_line, away_line, home_quarter_scores,
                        away_quarter_scores, home_first_half_points, away_first_half_points,
                        home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                        home_money_line, away_money_line, playoffs, start_time, total
                    ) VALUES (
                        :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                        :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                        :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                        :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points,
                        :home_money_line, :away_money_line, :playoffs, :start_time, :total
                    )
                """), {
                    'game_date': game['date'],
                    'game_site': game['site'],
                    'home_team_id': home_team_id,
                    'away_team_id': away_team_id,
                    'home_team_name': game['team'],
                    'away_team_name': game['o:team'],
                    'home_points': game['points'],
                    'away_points': game['o:points'],
                    'total_points': game['points'] + game['o:points'],
                    'total_margin': game['margin'],
                    'home_line': game['line'],
                    'away_line': game['o:line'],
                    'home_quarter_scores': json.dumps(home_quarter_scores),
                    'away_quarter_scores': json.dumps(away_quarter_scores),
                    'home_first_half_points': home_first_half_points,
                    'away_first_half_points': away_first_half_points,
                    'home_second_half_points': home_second_half_points,
                    'away_second_half_points': away_second_half_points,
                    'home_overtime_points': home_overtime_points,
                    'away_overtime_points': away_overtime_points,
                    'home_money_line': game.get('money line'),
                    'away_money_line': game.get('o:money line'),
                    'playoffs': bool(game.get('playoffs', 0)),  # Cast to boolean
                    'start_time': start_time,
                    'total': game['total']  # Use the total value as-is for NFL
                })
                
                # Log the response from the database
                print(f"Rows affected: {result.rowcount}")
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
    print("Transaction committed successfully.")
    conn.close()
    print("Seeding completed successfully.")

if __name__ == "__main__":
    seed_yesterdays_games()
