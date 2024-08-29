import requests
from datetime import datetime
from utils import convert_team_name, convert_sport_key

SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'



def get_last_5_games(team, date, sport_key):
    today_date = datetime.today().strftime('%Y%m%d')
    # Convert full team name to mascot name for SDQL query
    team = convert_team_name(team)
    sport_key = convert_sport_key(sport_key)
    sdql_url = f"https://s3.sportsdatabase.com/{sport_key}/query"

    if sport_key == 'MLB':
        sdql_query = f"date,team,site,runs,total,o:team,o:line,o:runs,line@team='{team}' and date<{today_date} and n5:date>={today_date}"           
    elif sport_key in ['NFL', 'NCAAFB', 'NBA', 'NHL','NCAAFB']:
        sdql_query = f"date,team,site,points,total,o:team,o:line,o:points,line@team='{team}' and date<{today_date}"
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

    response = requests.get(sdql_url, headers=headers, params=data)

    if response.status_code != 200:
        print(f"SDQL request failed: {response.status_code}")
        return None

    try:
        result = response.json()
        print("SDQL response:", result)  # Print the whole response for debugging


        if result.get('headers') and result.get('groups'):
            headers = result['headers']
            rows = result['groups'][0]['columns']
            formatted_result = [dict(zip(headers, row)) for row in zip(*rows)]





            
            # Get the last 5 games
            last_5_games = formatted_result[-5:] if formatted_result else []

            print(last_5_games)
            return last_5_games

        else:
            return None
    except ValueError as e:
        print(f"Error parsing SDQL response JSON: {e}")
        print(f"Response content: {response.content.decode('utf-8')}")
        return None
    
def get_last_5_games_vs_opponent(sport_key, team, opponent, today_date):
    today_date = datetime.today().strftime('%Y%m%d')
    # Convert full team name to mascot name for SDQL query
    team = convert_team_name(team)
    opponent = convert_team_name(opponent)
    sport_key = convert_sport_key(sport_key)

    sdql_url = f"https://s3.sportsdatabase.com/{sport_key}/query"

    if sport_key == 'MLB':
        sdql_query = f"date,team,site,runs,total,o:team,o:line,o:runs,line@team='{team}' and o:team='{opponent}' and date<{today_date}"             
    elif sport_key in ['NFL', 'NCAAFB', 'NBA', 'NHL','NCAAFB']:
        sdql_query = f"date,team,site,points,total,o:team,o:line,o:points,line@team='{team}' and o:team='{opponent}' and date<{today_date}"
    else:
        raise ValueError(f"Unsupported league: {sport_key}")

    headers = {
        'user': SDQL_USERNAME,
        'token': SDQL_TOKEN
    }

    data = {
        'sdql': sdql_query
    }

    response = requests.get(sdql_url, headers=headers, params=data)

    if response.status_code != 200:
        print(f"SDQL request failed: {response.status_code}")
        return None

    try:
        result = response.json()
        print("SDQL response for last 5 vs opponent:", result)  # Debugging output

        if result.get('headers') and result.get('groups'):
            headers = result['headers']
            rows = result['groups'][0]['columns']
            formatted_result = [dict(zip(headers, row)) for row in zip(*rows)]

            # Get the last 5 games between the teams
            last_5_games_vs_opponent = formatted_result[-5:] if formatted_result else []

            return last_5_games_vs_opponent
        else:
            return None
    except ValueError as e:
        print(f"Error parsing SDQL response JSON: {e}")
        print(f"Response content: {response.content.decode('utf-8')}")
        return None

