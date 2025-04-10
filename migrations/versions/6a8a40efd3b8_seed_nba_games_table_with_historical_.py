"""Seed nba_games table with historical data

Revision ID: 6a8a40efd3b8
Revises: 0d53b6f42a64
Create Date: 2025-04-08 21:25:13.306349

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
revision: str = '6a8a40efd3b8'
down_revision: Union[str, None] = '0d53b6f42a64'
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

    # Get all teams from the teams table
    teams = conn.execute(text("SELECT team_name FROM teams")).fetchall()
    teams = [team[0] for team in teams]

    for team in teams:
        games = get_historical_games(team)
        for game in games:
            # Skip games with missing points
            if game['points'] is None or game['o:points'] is None:
                print(f"Skipping game due to missing points: {game}")
                continue

            # Modify sdql_game_id to make it unique by appending the game_date
            unique_sdql_game_id = f"{game['_t']}_{game['date']}"

            # Check if the game already exists in the nba_games table
            existing_game = conn.execute(text("""
                SELECT 1 FROM nba_games WHERE sdql_game_id = :sdql_game_id
            """), {'sdql_game_id': unique_sdql_game_id}).fetchone()

            if existing_game:
                raise ValueError(f"Duplicate game detected with sdql_game_id: {unique_sdql_game_id}")

            # Deserialize quarter scores back to lists
            home_quarter_scores = json.loads(game['quarter scores'])
            away_quarter_scores = json.loads(game['o:quarter scores'])

            # Insert data into nba_games table
            conn.execute(text("""
                INSERT INTO nba_games (
                    game_date, game_site, home_team_id, away_team_id, home_points, away_points,
                    total_points, total_margin, home_line, away_line, home_quarter_scores,
                    away_quarter_scores, home_halftime_points, away_halftime_points, sdql_game_id
                ) VALUES (
                    :game_date, :game_site, 
                    (SELECT team_id FROM teams WHERE team_name = :home_team),
                    (SELECT team_id FROM teams WHERE team_name = :away_team),
                    :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                    :home_quarter_scores, :away_quarter_scores, :home_halftime_points, :away_halftime_points, :sdql_game_id
                )
            """), {
                'game_date': game['date'],
                'game_site': game['site'],
                'home_team': game['team'],
                'away_team': game['o:team'],
                'home_points': game['points'],
                'away_points': game['o:points'],
                'total_points': game['points'] + game['o:points'],
                'total_margin': game['margin'],
                'home_line': game['line'],
                'away_line': game['o:line'],
                'home_quarter_scores': game['quarter scores'],
                'away_quarter_scores': game['o:quarter scores'],
                'home_halftime_points': sum(home_quarter_scores[:2]),
                'away_halftime_points': sum(away_quarter_scores[:2]),
                'sdql_game_id': unique_sdql_game_id  # Use the unique sdql_game_id
            })

def downgrade():
    # No downgrade logic for historical data
    pass