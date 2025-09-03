"""2 ncaaf seed neutral games

Revision ID: 3ffdfc45f1c8
Revises: cf829e881f81
Create Date: 2025-08-24 15:19:45.191031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import requests
import time
from datetime import datetime
import json


# revision identifiers, used by Alembic.
revision: str = '3ffdfc45f1c8'
down_revision: Union[str, None] = 'cf829e881f81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



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

def get_historical_games(team, retries=3, delay=1):
    sdql_url = f"https://s3.sportsdatabase.com/NCAAFB/query"
    sdql_query = f"date,site,team,o:team,points,o:points,total,margin,line,o:line,quarter scores,o:quarter scores,playoffs,money line,o:money line,start time,_t@team='{team}' and site='neutral' and date>20090101"
    
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
    teams = [
        team['team_name']
        for team in conn.execute(text("SELECT team_name FROM teams WHERE sport = 'NCAAF'")).mappings()
    ]
    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAF'")).mappings()
    }
    for team in teams:
        games = get_historical_games(team)
        for game in games:
            if game['points'] is None or game['o:points'] is None:
                continue

            # Handle invalid total values - convert '-' to None for NULL insertion
            total_value = game['total'] if game['total'] != '-' and game['total'] is not None else None

            home_team_id = teams_dict.get(game['team'])
            away_team_id = teams_dict.get(game['o:team'])
            if home_team_id is None or away_team_id is None:
                continue

            # Check if either team has already played a neutral game on this date
            existing_game = conn.execute(text("""
                SELECT 1 FROM ncaaf_games
                WHERE game_date = :game_date
                AND game_site = 'neutral'
                AND (home_team_name = :home_team OR away_team_name = :home_team 
                     OR home_team_name = :away_team OR away_team_name = :away_team)
            """), {
                'game_date': game['date'],
                'home_team': game['team'],
                'away_team': game['o:team']
            }).fetchone()

            if existing_game:
                print(f"Skipping duplicate game: {game}")
                continue

            if game['start time'] is None or game['start time'] == 0:
                start_time = None
            else:
                if not isinstance(game['start time'], str):
                    game['start time'] = str(game['start time'])
                start_time = convert_start_time_to_time(game['start time'])
            conn.execute(text("""
                INSERT INTO ncaaf_games (
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
                'home_quarter_scores': json.dumps(json.loads(game['quarter scores'])),
                'away_quarter_scores': json.dumps(json.loads(game['o:quarter scores'])),
                'home_first_half_points': sum(json.loads(game['quarter scores'])[:2]),
                'away_first_half_points': sum(json.loads(game['o:quarter scores'])[:2]),
                'home_second_half_points': sum(json.loads(game['quarter scores'])[2:4]),
                'away_second_half_points': sum(json.loads(game['o:quarter scores'])[2:4]),
                'home_overtime_points': json.loads(game['quarter scores'])[4] if len(json.loads(game['quarter scores'])) > 4 else None,
                'away_overtime_points': json.loads(game['o:quarter scores'])[4] if len(json.loads(game['o:quarter scores'])) > 4 else None,
                'home_money_line': -999999 if game.get('money line') == 'NL' else game.get('money line') if isinstance(game.get('money line'), int) else None,
                'away_money_line': -999999 if game.get('o:money line') == 'NL' else game.get('o:money line') if isinstance(game.get('o:money line'), int) else None,
                'playoffs': bool(game.get('playoffs', 0)),
                'start_time': start_time,
                'total': total_value  # Use the cleaned total value (None if '-')
            })

def downgrade() -> None:
    pass
