"""3 seed nba table

Revision ID: c988c0cbf26a
Revises: c478dfac5475
Create Date: 2025-05-10 21:42:42.233426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import requests
import time
from sqlalchemy.sql import text
from datetime import datetime
import json

# revision identifiers, used by Alembic.
revision: str = 'c988c0cbf26a'
down_revision: Union[str, None] = 'c478dfac5475'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_historical_games(team, retries=3, delay=1):
    sdql_url = f"https://s3.sportsdatabase.com/NBA/query"
    sdql_query = f"date,site,team,o:team,points,o:points,total,margin,line,o:line,quarter scores,o:quarter scores,_t@team='{team}' and site='home'and date>20150101"

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
            result = response.json()

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

            # Use the dictionary for lookups
            home_team_id = teams_dict.get(game['team'])
            away_team_id = teams_dict.get(game['o:team'])

            if home_team_id is None or away_team_id is None:
                print(f"Skipping game due to missing team ID: {game}")
                continue

            # Deserialize quarter scores back to lists
            try:
                home_quarter_scores_raw = game['quarter scores']
                away_quarter_scores_raw = game['o:quarter scores']

                # Handle extra quotes around JSON strings
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
            except (TypeError, json.JSONDecodeError) as e:
                print(f"Invalid quarter scores detected! Raw game data: {game}")
                raise Exception("Invalid quarter scores format. Stopping migration.") from e

            # Calculate first half points
            home_first_half_points = sum(home_quarter_scores[:2])
            away_first_half_points = sum(away_quarter_scores[:2])

            # Calculate second half points
            home_second_half_points = sum(home_quarter_scores[2:4])
            away_second_half_points = sum(away_quarter_scores[2:4])

            # Calculate overtime points (if any)
            home_overtime_points = home_quarter_scores[4] if len(home_quarter_scores) > 4 else None
            away_overtime_points = away_quarter_scores[4] if len(away_quarter_scores) > 4 else None

            # Convert quarter scores to JSON strings
            home_quarter_scores_json = json.dumps(home_quarter_scores)
            away_quarter_scores_json = json.dumps(away_quarter_scores)

            # Insert data into nba_games table
            conn.execute(text("""
                INSERT INTO nba_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name, home_points, away_points,
                    total_points, total_margin, home_line, away_line, home_quarter_scores,
                    away_quarter_scores, home_first_half_points, away_first_half_points,
                    home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                    :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                    :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points
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
                'home_quarter_scores': home_quarter_scores_json,
                'away_quarter_scores': away_quarter_scores_json,
                'home_first_half_points': home_first_half_points,
                'away_first_half_points': away_first_half_points,
                'home_second_half_points': home_second_half_points,
                'away_second_half_points': away_second_half_points,
                'home_overtime_points': home_overtime_points,
                'away_overtime_points': away_overtime_points
            })

def downgrade():
    # No downgrade logic for historical data
    pass