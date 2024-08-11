import requests
from datetime import datetime

SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_last_5_games(team, date):
    today_date = datetime.today().strftime('%Y%m%d')
    sdql_query = f"date,team,site,runs,total,o:team,o:line,o:runs,line@team='Angels' and date<{today_date} and n5:date>={today_date}"           
    sdql_url = "https://s3.sportsdatabase.com/MLB/query"
    
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

        '''if 'headers' in result and 'groups' in result:
            headers = result['headers']
            rows = result['groups'][0]['rows']

            # Format the result into a list of dictionaries
            formatted_result = [dict(zip(headers, row)) for row in rows]'''


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
