import requests
import datetime

SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_sdql_data(sport_key, date):

     # Build SDQL query based on sport_key
    if sport_key == 'MLB':
        sdql_query = f"date,team,site,runs,total,line@date={date.strftime('%Y%m%d')}"
    elif sport_key in ['NBA', 'NFL', 'NHL']:
        sdql_query = f"date,team,site,points,total,line@date={date.strftime('%Y%m%d')}"
    else:
        raise ValueError(f"Unsupported sport: {sport_key}")


    sdql_url = f"https://s3.sportsdatabase.com/{sport_key}/query"

    headers = {
        'user': SDQL_USERNAME,
        'token': SDQL_TOKEN
    }

    data = {
        'sdql': sdql_query
    }

    try:
        # Print full request URL and data for debugging
        print(f"Full Request URL: {sdql_url}?{requests.compat.urlencode(data)}")

        response = requests.get(sdql_url, headers=headers, params=data)

        print(f"Request URL: {sdql_url}")
        print(f"Request Headers: {headers}")
        print(f"Request Data: {data}")
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Content: {response.content}")

        if response.status_code != 200:
            print(f"Unexpected Content-Type: {response.headers.get('Content-Type')}")
            print(f"Response content: {response.content.decode('utf-8')}")
            return None

        result = response.json()
        print(f"Response JSON: {result}")

        if result.get('headers') and result.get('groups'):
            headers = result['headers']
            rows = result['groups'][0]['columns']
            formatted_result = [dict(zip(headers, row)) for row in zip(*rows)]
        else:
            formatted_result = None

        return formatted_result
    except ValueError as e:
        print(f"Error parsing JSON response: {str(e)}")
        return None
    except requests.RequestException as e:
        print(f"Request error: {str(e)}")
        return None

