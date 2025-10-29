"""5 seed nba games table

Revision ID: e949afd6b3ce
Revises: 9fff514ec21c
Create Date: 2025-10-28 13:51:00.739123

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
revision: str = 'e949afd6b3ce'
down_revision: Union[str, None] = '9fff514ec21c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_historical_games(team, retries=3, delay=1):
    sdql_url = f"https://s3.sportsdatabase.com/NBA/query"
    sdql_query = f"date,site,team,o:team,points,o:points,total,margin,line,o:line,quarter scores,o:quarter scores,playoffs,money line,o:money line,_t,start time@team='{team}' and site='home'and date>20150101 and date<20251029"

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
    # Only load teams that are NBA (sport='NBA') so we don't accidentally map other sports' teams
    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NBA'")).mappings()
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

            # Parse optional start time if present in the SDQL row. SDQL may not provide a
            # time field, so we try several common keys and formats and fall back to None.
            start_time_val = None
            for time_key in ('start_time', 'start', 'time', 'start time'):
                raw_time = game.get(time_key)
                if raw_time:
                    s = str(raw_time).strip()
                    # Try multiple common formats: HH:MM, HHMM, HH:MM:SS, and 12-hour with AM/PM
                    for fmt in ('%H:%M', '%H%M', '%H:%M:%S', '%H%M%S', '%I:%M%p', '%I:%M %p'):
                        try:
                            start_time_val = datetime.strptime(s, fmt).time()
                            break
                        except ValueError:
                            continue
                    # If we parsed a value, stop looking through keys
                    if start_time_val is not None:
                        break

            # Insert data into nba_games_1 table (include start_time)
            conn.execute(text("""
                INSERT INTO nba_games_1 (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name, home_points, away_points,
                    total_points, total_margin, total, home_line, away_line, home_quarter_scores,
                    away_quarter_scores, home_first_half_points, away_first_half_points,
                    home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                    home_money_line, away_money_line, playoffs, start_time
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :total, :home_line, :away_line,
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
                'home_quarter_scores': home_quarter_scores_json,
                'away_quarter_scores': away_quarter_scores_json,
                'home_first_half_points': home_first_half_points,
                'away_first_half_points': away_first_half_points,
                'home_second_half_points': home_second_half_points,
                'away_second_half_points': away_second_half_points,
                'home_overtime_points': home_overtime_points,
                'away_overtime_points': away_overtime_points,
                'home_money_line': game.get('money line'),
                'away_money_line': game.get('o:money line'),
                'playoffs': bool(game.get('playoffs', 0)),  # Cast to boolean
                'total': game.get('total'),  # Added total field
                'start_time': start_time_val
            })


def downgrade() -> None:
    pass

