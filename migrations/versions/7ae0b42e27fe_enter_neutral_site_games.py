"""Enter neutral site games

Revision ID: 7ae0b42e27fe
Revises: 8ee3520167f2
Create Date: 2025-06-07 14:18:09.735700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text  # Add this import
import requests
import time
from datetime import datetime
import json


# revision identifiers, used by Alembic.
revision: str = '7ae0b42e27fe'
down_revision: Union[str, None] = '8ee3520167f2'
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
    sdql_url = f"https://s3.sportsdatabase.com/NFL/query"
    sdql_query = f"date,site,team,o:team,points,o:points,total,margin,line,o:line,quarter scores,o:quarter scores,playoffs,money line,o:money line,start time,_t@team='{team}' and site='neutral'and date>20090101"

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

    # Fetch all teams and store them in a dictionary
    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams")).mappings()
    }

    for team in teams_dict.keys():
        games = get_historical_games(team)
        for game in games:
            # Skip games with missing points
            if game['points'] is None or game['o:points'] is None:
                print(f"Skipping game due to missing points: {game}")
                continue

            # Check if the record already exists
            existing_game = conn.execute(text("""
                SELECT 1 FROM nfl_games
                WHERE game_date = :game_date
                AND home_team_name = :away_team_name
            """), {
                'game_date': game['date'],
                'away_team_name': game['o:team']
            }).fetchone()

            if existing_game:
                print(f"Skipping duplicate game: {game}")
                continue

            # Use the dictionary for lookups
            home_team_id = teams_dict.get(game['team'])
            away_team_id = teams_dict.get(game['o:team'])

            if home_team_id is None or away_team_id is None:
                print(f"Skipping game due to missing team ID: {game}")
                continue

            # Check if start time is None or not a string
            if game['start time'] is None:
                if game['team'] == "Fortyniners" and game['o:team'] == "Jaguars":
                    print(f"Assigning start time 1307 (1:07 PM ET) for game: {game}")
                    game['start time'] = "1307"
                else:
                    print(f"Game with missing start time: {game}")
                    raise Exception("Encountered a game with missing start time. Stopping migration.")

            # Convert start_time to a datetime.time object
            start_time = convert_start_time_to_time(game['start time'])

            # Insert the game into the database
            conn.execute(text("""
                INSERT INTO nfl_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name, home_points, away_points,
                    total_points, total_margin, home_line, away_line, home_quarter_scores,
                    away_quarter_scores, home_first_half_points, away_first_half_points,
                    home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                    home_money_line, away_money_line, playoffs, start_time
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                    :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                    :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points,
                    :home_money_line, :away_money_line, :playoffs, :start_time
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
                'home_quarter_scores': json.dumps(json.loads(game['quarter scores'])),
                'away_quarter_scores': json.dumps(json.loads(game['o:quarter scores'])),
                'home_first_half_points': sum(json.loads(game['quarter scores'])[:2]),
                'away_first_half_points': sum(json.loads(game['o:quarter scores'])[:2]),
                'home_second_half_points': sum(json.loads(game['quarter scores'])[2:4]),
                'away_second_half_points': sum(json.loads(game['o:quarter scores'])[2:4]),
                'home_overtime_points': json.loads(game['quarter scores'])[4] if len(json.loads(game['quarter scores'])) > 4 else None,
                'away_overtime_points': json.loads(game['o:quarter scores'])[4] if len(json.loads(game['o:quarter scores'])) > 4 else None,
                'home_money_line': game.get('money line'),
                'away_money_line': game.get('o:money line'),
                'playoffs': bool(game.get('playoffs', 0)),  # Cast to boolean
                'start_time': start_time
            })


def downgrade() -> None:
    pass
