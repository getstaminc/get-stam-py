"""2 seed mlb games

Revision ID: 9a3ae0a8320a
Revises: 015d122ed2e4
Create Date: 2025-08-30 19:06:37.155173

"""
from typing import Sequence, Union
import json
import time
import requests
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '9a3ae0a8320a'
down_revision: Union[str, None] = '015d122ed2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'


def convert_start_time_to_time(start_time: str) -> datetime.time:
    """
    Convert military time (e.g., '1838') to a datetime.time object.
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
        return datetime.strptime(start_time, "%H%M").time()
    except ValueError as e:
        raise ValueError(f"Invalid start time format: {start_time}. Error: {e}")


def get_historical_games(team, retries=3, delay=1):
    sdql_url = f"https://s3.sportsdatabase.com/MLB/query"
    # Split historical data into chunks - this migration covers 2015-2020
    sdql_query = f"date,site,team,o:team,runs,o:runs,total,margin,line,o:line,playoffs,start time,_t,starter,o:starter,line F5,o:line F5,total F5,total over F5 odds,inning runs,o:inning runs@team='{team}' and site='home' and date>20200101 and date<20250830"

    headers = {
        'user': SDQL_USERNAME,
        'token': SDQL_TOKEN
    }

    data = {
        'sdql': sdql_query
    }

    for i in range(retries):
        try:
            print(f"Querying SDQL for team: {team} (attempt {i+1}/{retries})")
            response = requests.get(sdql_url, headers=headers, params=data)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 500:
                print(f"Server error for {team}. Response: {response.text[:200]}")
                if i < retries - 1:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"Failed after {retries} attempts for {team}, skipping...")
                    return []  # Return empty instead of crashing
            
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

                return formatted_result
            else:
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


def upgrade():
    conn = op.get_bind()

    # Fetch all MLB teams and store them in a dictionary
    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'MLB'")).mappings()
    }
    
    # Create team name mappings for historical names
    team_name_mappings = {
        'Indians': 'Guardians'  # Cleveland team name change
    }

    for team in teams_dict.keys():
        try:
            print(f"\n=== Processing team: {team} ===")
            games = get_historical_games(team)
            print(f"Retrieved {len(games)} games for {team}")
            
            if not games:
                print(f"No games found for {team}, continuing with next team...")
                continue
                
        except Exception as e:
            print(f"Error processing {team}: {e}")
            print(f"Skipping {team} and continuing with next team...")
            continue
            
        for game in games:
            # Skip games with missing runs
            if game['runs'] is None or game['o:runs'] is None:
                print(f"Skipping game due to missing runs: {game}")
                continue

            # Use the dictionary for lookups with team name mapping
            home_team_name = game['team']
            away_team_name = game['o:team']
            
            # Apply team name mappings for historical names
            mapped_home_team = team_name_mappings.get(home_team_name, home_team_name)
            mapped_away_team = team_name_mappings.get(away_team_name, away_team_name)
            
            home_team_id = teams_dict.get(mapped_home_team)
            away_team_id = teams_dict.get(mapped_away_team)

            if home_team_id is None or away_team_id is None:
                print(f"Missing team ID - Home: '{home_team_name}' -> '{mapped_home_team}' (ID: {home_team_id}), Away: '{away_team_name}' -> '{mapped_away_team}' (ID: {away_team_id})")
                raise Exception(f"Stopping migration due to missing team ID for game: {game}")

            # Check if start time is None or not a string
            if game['start time'] is None:
                print(f"Game with missing start time: {game}")
                raise Exception("Encountered a game with missing start time. Stopping migration.")
            elif not isinstance(game['start time'], str):
                print(f"Game with start time format int: {game}")
                game['start time'] = str(game['start time'])  # Convert to string

            # Convert start_time to a datetime.time object
            start_time = convert_start_time_to_time(game['start time'])

            # Deserialize inning runs back to lists
            try:
                home_inning_runs_raw = game['inning runs']
                away_inning_runs_raw = game['o:inning runs']

                # Handle extra quotes around JSON strings
                if isinstance(home_inning_runs_raw, str):
                    home_inning_runs_raw = json.loads(home_inning_runs_raw)
                if isinstance(away_inning_runs_raw, str):
                    away_inning_runs_raw = json.loads(away_inning_runs_raw)

                # Ensure the final deserialization in case of double quotes
                if isinstance(home_inning_runs_raw, str):
                    home_inning_runs = json.loads(home_inning_runs_raw)
                else:
                    home_inning_runs = home_inning_runs_raw

                if isinstance(away_inning_runs_raw, str):
                    away_inning_runs = json.loads(away_inning_runs_raw)
                else:
                    away_inning_runs = away_inning_runs_raw
                
                # Ensure inning runs are valid lists
                if not isinstance(home_inning_runs, list) or not isinstance(away_inning_runs, list):
                    print(f"Skipping game due to invalid inning runs: {game}")
                    continue

            except (TypeError, json.JSONDecodeError) as e:
                print(f"Invalid inning runs detected! Raw game data: {game}")
                raise Exception("Invalid inning runs format. Stopping migration.") from e
            
            # Skip records with missing required fields
            if game['total'] is None or game['margin'] is None or game['line'] is None or game['o:line'] is None:
                print(f"Skipping game due to missing required fields: {game}")
                continue

            # Calculate first 5 innings runs
            home_first_5_runs = sum(home_inning_runs[:5]) if len(home_inning_runs) >= 5 else sum(home_inning_runs)
            away_first_5_runs = sum(away_inning_runs[:5]) if len(away_inning_runs) >= 5 else sum(away_inning_runs)

            # Calculate remaining innings runs (6+)
            home_remaining_runs = sum(home_inning_runs[5:]) if len(home_inning_runs) > 5 else 0
            away_remaining_runs = sum(away_inning_runs[5:]) if len(away_inning_runs) > 5 else 0

            # Parse first 5 over/under odds if available
            first_5_over_odds = None
            first_5_under_odds = None
            if game.get('total over F5 odds') and isinstance(game['total over F5 odds'], list) and len(game['total over F5 odds']) >= 2:
                first_5_over_odds = game['total over F5 odds'][0]
                first_5_under_odds = game['total over F5 odds'][1]

            # Convert inning runs to JSON strings
            home_inning_runs_json = json.dumps(home_inning_runs)
            away_inning_runs_json = json.dumps(away_inning_runs)

            # Insert data into mlb_games table
            conn.execute(text("""
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
                'home_team_name': mapped_home_team,  # Store the mapped name in database
                'away_team_name': mapped_away_team,  # Store the mapped name in database
                'home_runs': game['runs'],
                'away_runs': game['o:runs'],
                'total': game['total'],
                'total_runs': game['runs'] + game['o:runs'],
                'total_margin': game['margin'],
                'home_line': game['line'],
                'away_line': game['o:line'],
                'home_money_line': game.get('line'),  # Using line as money line for now
                'away_money_line': game.get('o:line'),  # Using o:line as away money line for now
                'playoffs': bool(game.get('playoffs', 0)),  # Cast to boolean
                'start_time': start_time,
                'home_first_5_line': game.get('line F5'),
                'away_first_5_line': game.get('o:line F5'),
                'total_first_5': game.get('total F5'),
                'first_5_over_odds': first_5_over_odds,
                'first_5_under_odds': first_5_under_odds,
                'home_starting_pitcher': game.get('starter'),
                'away_starting_pitcher': game.get('o:starter'),
                'home_inning_runs': home_inning_runs_json,
                'away_inning_runs': away_inning_runs_json,
                'home_first_5_runs': home_first_5_runs,
                'away_first_5_runs': away_first_5_runs,
                'home_remaining_runs': home_remaining_runs,
                'away_remaining_runs': away_remaining_runs
            })


def downgrade() -> None:
    pass