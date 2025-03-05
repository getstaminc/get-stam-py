import time
import requests
from datetime import datetime
from shared_utils import convert_team_name, convert_sport_key
import logging
import os
# Configure logging to write to a file
if not os.path.exists('logs'):
    os.makedirs('logs')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('logs/app.log')
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_last_5_games(team, date, sport_key, retries=3, delay=1):
    today_date = datetime.today().strftime('%Y%m%d')
    logger.info(f"Fetching last 5 games for team: {team}, date: {date}, sport_key: {sport_key}")

    # Convert full team name to mascot name for SDQL query
    team = convert_team_name(team)
    sport_key = convert_sport_key(sport_key)
    sdql_url = f"https://s3.sportsdatabase.com/{sport_key}/query"

    if sport_key == 'MLB':
        sdql_query = f"date,team,site,runs,total,o:team,o:line,o:runs,line@team='{team}' and date<{today_date} and date<{today_date} and (_tNNNNN is None or N5:date>{today_date})" 
    elif sport_key == 'NHL':
        sdql_query = f"date,team,site,goals,total,o:team,o:line,o:goals,line@team='{team}' and date<{today_date} and (_tNNNNN is None or N5:date>{today_date})"          
    elif sport_key in ['NFL', 'NCAAFB', 'NBA', 'NCAABB']:
        sdql_query = f"date,team,site,points,total,o:team,o:line,o:points,line@team='{team}' and date<{today_date} and (_tNNNNN is None or N5:date>{today_date})"
    else:
        # Handle other sports or raise an error
        raise ValueError(f"Unsupported league: {sport_key}")
    
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

                last_5_games = formatted_result[-5:] if formatted_result else []
                return last_5_games
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"SDQL request failed: {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
        except ValueError as e:
            print(f"Error parsing SDQL response JSON: {e}")
            print(f"Response content: {response.content.decode('utf-8')}")
            return None
    
def get_last_5_games_vs_opponent(sport_key, team, opponent, today_date, retries=3, delay=1):
    today_date = datetime.today().strftime('%Y%m%d')
    # Convert full team name to mascot name for SDQL query
    team = convert_team_name(team)
    opponent = convert_team_name(opponent)
    sport_key = convert_sport_key(sport_key)

    sdql_url = f"https://s3.sportsdatabase.com/{sport_key}/query"

    if sport_key == 'MLB':
        sdql_query = f"date,team,site,runs,total,o:team,o:line,o:runs,line@team='{team}' and o:team='{opponent}' and date<{today_date} and (_tNNNNNN is None or N6:date>{today_date})" 
    elif sport_key == 'NHL':
        sdql_query = f"date,team,site,goals,total,o:team,o:line,o:goals,line@team='{team}' and o:team='{opponent}' and date<{today_date} and (_tNNNNNN is None or N6:date>{today_date})"         
    elif sport_key in ['NFL', 'NCAAFB', 'NBA', 'NCAABB']:
        sdql_query = f"date,team,site,points,total,o:team,o:line,o:points,line@team='{team}' and o:team='{opponent}' and date<{today_date} and (_tNNNNNN is None or N6:date>{today_date})"
    else:
        raise ValueError(f"Unsupported league3: {sport_key}")

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

                last_5_games_vs_opponent = formatted_result[-5:] if formatted_result else []
                return last_5_games_vs_opponent
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"SDQL request failed: {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
        except ValueError as e:
            print(f"Error parsing SDQL response JSON: {e}")
            print(f"Response content: {response.content.decode('utf-8')}")
            return None

