import requests

SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_last_5_games(team):
    sdql_query = f"team='{team}' and season=2024 and date < today() @date,team,opponent,runs"
    sdql_url = "https://s3.sportsdatabase.com/mlb/query"
    
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
        if result.get('headers') and result.get('groups'):
            headers = result['headers']
            rows = result['groups'][0]['columns']
            formatted_result = [dict(zip(headers, row)) for row in zip(*rows)]
        else:
            formatted_result = None

        # Get the last 5 games
        last_5_games = formatted_result[-5:] if formatted_result else []

        return last_5_games
    except ValueError as e:
        print(f"Error parsing SDQL response JSON: {e}")
        return None
