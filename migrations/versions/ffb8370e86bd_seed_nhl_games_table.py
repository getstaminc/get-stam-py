"""seed nhl games table

Revision ID: ffb8370e86bd
Revises: b12efd95e5d6
Create Date: 2025-10-04 15:10:57.608581

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text
import sqlalchemy as sa
import requests
import time
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'ffb8370e86bd'
down_revision: Union[str, None] = 'b12efd95e5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_historical_nhl_games(team, retries=3, delay=1):
    sdql_url = "https://s3.sportsdatabase.com/NHL/query"
    sdql_query = f"date,site,team,line,goals,o:team,o:line,o:goals,total,period scores, o:period scores, goalie,o:goalie,playoffs,power play goals,o:power play goals, shoot out, overtime@team='{team}' and (site='home' or site='neutral') and date>20150101 and date<20251005"
    headers = {'user': SDQL_USERNAME, 'token': SDQL_TOKEN}
    data = {'sdql': sdql_query}

    for i in range(retries):
        try:
            response = requests.get(sdql_url, headers=headers, params=data)
            if response.status_code == 500:
                if i < retries - 1:
                    time.sleep(delay)
                    continue
                else:
                    return []
            response.raise_for_status()
            result = response.json()
            if result.get('headers') and result.get('groups'):
                headers = result['headers']
                rows = result['groups'][0]['columns']
                formatted_result = [dict(zip(headers, row)) for row in zip(*rows)]
                for game in formatted_result:
                    game['date'] = datetime.strptime(str(game['date']), '%Y%m%d').strftime('%Y-%m-%d')
                return formatted_result
            else:
                return []
        except Exception:
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise

def upgrade():
    conn = op.get_bind()
    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NHL'")).mappings()
    }
    processed_games = set()

    # Add 'Hockey Club' to the list of teams to query
    teams_to_query = list(teams_dict.keys())
    if "Hockey Club" not in teams_to_query:
        teams_to_query.append("Hockey Club")

    for team in teams_to_query:
        print(f"\n=== Processing team: {team} ===")
        try:
            games = get_historical_nhl_games(team)
            if not games:
                continue
        except Exception:
            continue

        for game in games:
            # Skip games with missing goals
            if game['goals'] is None or game['o:goals'] is None:
                continue
            home_team_name = game['team']
            away_team_name = game['o:team']

            # Map "Hockey Club" to "Mammoth"
            if home_team_name == "Hockey Club":
                home_team_name = "Mammoth"
            if away_team_name == "Hockey Club":
                away_team_name = "Mammoth"

            home_team_id = teams_dict.get(home_team_name)
            away_team_id = teams_dict.get(away_team_name)

            if home_team_id is None or away_team_id is None:
                raise Exception(
                    f"Missing team ID - Home: '{home_team_name}' (ID: {home_team_id}), "
                    f"Away: '{away_team_name}' (ID: {away_team_id})"
                )

            dedup_key = (game['date'], home_team_name, away_team_name)
            if dedup_key in processed_games:
                continue
            processed_games.add(dedup_key)

            # Use home_period_goals and away_period_goals arrays
            home_period_goals = game.get('period scores', []) or []
            away_period_goals = game.get('o:period scores', []) or []

            conn.execute(text("""
                INSERT INTO nhl_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_goals, away_goals, home_money_line, away_money_line, home_period_goals, away_period_goals,
                    home_starting_goalie, away_starting_goalie, home_powerplay_goals, away_powerplay_goals,
                    total, overtime, shoot_out, playoffs, sdql_game_id, created_date, modified_date
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_goals, :away_goals, :home_money_line, :away_money_line, :home_period_goals, :away_period_goals,
                    :home_starting_goalie, :away_starting_goalie, :home_powerplay_goals, :away_powerplay_goals,
                    :total, :overtime, :shoot_out, :playoffs, :sdql_game_id, :created_date, :modified_date
                )
            """), {
                'game_date': game['date'],
                'game_site': game['site'],
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_team_name': home_team_name,
                'away_team_name': away_team_name,
                'home_goals': game['goals'],
                'away_goals': game['o:goals'],
                'home_money_line': game.get('line'),
                'away_money_line': game.get('o:line'),
                'home_period_goals': home_period_goals,
                'away_period_goals': away_period_goals,
                'home_starting_goalie': game.get('goalie'),
                'away_starting_goalie': game.get('o:goalie'),
                'home_powerplay_goals': game.get('power play goals'),
                'away_powerplay_goals': game.get('o:power play goals'),
                'total': game.get('total'),
                'overtime': bool(game.get('overtime', 0)),
                'shoot_out': bool(game.get('shoot out', 0)),
                'playoffs': bool(game.get('playoffs', 0)),
                'sdql_game_id': game.get('sdql_game_id'),
                'created_date': datetime.now(),
                'modified_date': datetime.now()
            })

def downgrade() -> None:
    pass
