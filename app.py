from flask import Flask, jsonify, request, render_template, render_template_string
import requests
import datetime
import json
from dateutil import parser
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress only the single InsecureRequestWarning from urllib3 needed for unverified HTTPS requests.
warnings.simplefilter('ignore', InsecureRequestWarning)

app = Flask(__name__)
port = 3000
api_key = '489331b7e9ff5b17f6f37e664ba10c08'
sdql_token = '3b88dcbtr97bb8e89b74r'
sdql_user = 'TimRoss'

def get_odds_data(sport_key):
    try:
        scores_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?apiKey={api_key}&daysFrom=1&dateFormat=iso"
        odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&bookmakers=bovada&markets=h2h,spreads,totals&oddsFormat=american"

        scores_response = requests.get(scores_url)
        odds_response = requests.get(odds_url)

        scores_response.raise_for_status()
        odds_response.raise_for_status()

        scores = scores_response.json()
        odds = odds_response.json()
        return scores, odds

    except requests.exceptions.RequestException as e:
        print('Request error:', str(e))
        return None, None

def get_sdql_data(sport_key, selected_date_start):
    try:
        sdql_sport_key = convert_sport_key(sport_key)
        sdql_date = selected_date_start.strftime('%Y%m%d')
        sdql_query = f"date,team,site,runs,total,line@date={sdql_date}"
        sdql_url = f"https://s3.sportsdatabase.com/{sdql_sport_key}/query"
        headers = {
            'token': sdql_token,
            'user': sdql_user
        }
        params = {
            'sdql': sdql_query
        }
        print(f"SDQL Query: {sdql_query}")
        print(f"SDQL URL: {sdql_url}")
        response = requests.get(sdql_url, headers=headers, params=params, verify=False)  # Disable SSL verification
        response.raise_for_status()

        # Print raw response text for debugging
        app.logger.debug(f"Raw response text: {response.text}")

        result = response.json()

        # Check the structure of the response
        app.logger.debug(f"Response JSON: {json.dumps(result, indent=2)}")

        # Extract and format the data
        if result.get('headers') and result.get('groups'):
            headers = result['headers']
            rows = result['groups'][0]['columns']

            # Combine headers with their corresponding data
            formatted_result = [dict(zip(headers, row)) for row in rows]
        else:
            formatted_result = None

        return formatted_result

    except requests.exceptions.RequestException as e:
        print('Request error:', str(e))
        return None
    except Exception as e:
        print('Error fetching SDQL data:', str(e))
        return None

@app.route('/api/sports')
def get_sports():
    try:
        api_url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
        response = requests.get(api_url)
        response.raise_for_status()
        sports = response.json()
        return jsonify(sports)
    except Exception as e:
        print('Error fetching sports:', str(e))
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/sports/<sport_key>')
def get_sport_scores(sport_key):
    try:
        current_date = request.args.get('date', None)
        if not current_date:
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')

        selected_date_start = datetime.datetime.strptime(current_date, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        selected_date_end = selected_date_start + datetime.timedelta(hours=23, minutes=59, seconds=59)

        print(f"Selected Date Start (UTC): {selected_date_start}")
        print(f"Selected Date End (UTC): {selected_date_end}")

        scores, odds = get_odds_data(sport_key)
        if scores is None or odds is None:
            return jsonify({'error': 'Error fetching odds data'}), 500

        filtered_scores = []
        for score in scores:
            commence_time_str = score['commence_time']
            commence_date = parser.parse(commence_time_str).astimezone(datetime.timezone.utc).date()
            print(f"Commence Date (UTC): {commence_date}")

            if commence_date == selected_date_start.date():
                filtered_scores.append(score)

        formatted_scores = []
        for match in filtered_scores:
            home_team = match.get('home_team', 'N/A')
            away_team = match.get('away_team', 'N/A')
            home_score = match['scores'][0]['score'] if match.get('scores') else 'N/A'
            away_score = match['scores'][1]['score'] if match.get('scores') else 'N/A'

            match_odds = next((odds_match for odds_match in odds if odds_match['id'] == match['id']), None)
            odds_text = 'N/A'
            if match_odds:
                odds_text_list = []
                for bookmaker in match_odds['bookmakers']:
                    for market in bookmaker['markets']:
                        market_key = market['key']
                        for outcome in market['outcomes']:
                            outcome_text = f"{market_key}: {outcome['name']}"
                            if market_key in ['spreads', 'totals'] and 'point' in outcome:
                                outcome_text += f" - {outcome['point']}"
                            outcome_text += f" - {outcome['price']}"
                            odds_text_list.append(outcome_text)
                odds_text = ', '.join(odds_text_list)

            formatted_scores.append({
                'homeTeam': home_team,
                'awayTeam': away_team,
                'homeScore': home_score,
                'awayScore': away_score,
                'oddsText': odds_text
            })

        if selected_date_start.date() < datetime.datetime.now().date():
            sdql_data = get_sdql_data(sport_key, selected_date_start)
            return render_template_string("""
                <html>
                <head>
                    <title>Game Info</title>
                    <style>
                        table {
                            width: 50%;
                            border-collapse: collapse;
                        }
                        table, th, td {
                            border: 1px solid black;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #f2f2f2;
                        }
                    </style>
                </head>
                <body>
                    <h1>Game Information</h1>
                    {% if result %}
                        <table>
                            <thead>
                                <tr>
                                    {% for header in result[0].keys() %}
                                        <th>{{ header }}</th>
                                    {% endfor %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in result %}
                                    <tr>
                                        {% for value in row.values() %}
                                            <td>{{ value }}</td>
                                        {% endfor %}
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% else %}
                        <p>No data available</p>
                    {% endif %}
                </body>
                </html>
            """, result=sdql_data)
        else:
            return render_template_string("""
                <html>
                <head>
                    <title>Game Info</title>
                    <style>
                        table {
                            width: 50%;
                            border-collapse: collapse;
                        }
                        table, th, td {
                            border: 1px solid black;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #f2f2f2;
                        }
                    </style>
                </head>
                <body>
                    <h1>Game Information</h1>
                    {% if result %}
                        <table>
                            <thead>
                                <tr>
                                    {% for header in result[0].keys() %}
                                        <th>{{ header }}</th>
                                    {% endfor %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in result %}
                                    <tr>
                                        {% for value in row.values() %}
                                            <td>{{ value }}</td>
                                        {% endfor %}
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% else %}
                        <p>No data available</p>
                    {% endif %}
                </body>
                </html>
            """, result=formatted_scores)

    except requests.exceptions.RequestException as e:
        print('Request error:', str(e))
        return jsonify({'error': 'Request Error'}), 500
    except Exception as e:
        print('Error fetching scores:', str(e))
        return jsonify({'error': 'Internal Server Error'}), 500

def convert_sport_key(sport_key):
    sport_mapping = {
        'baseball_mlb': 'MLB',
        'basketball_nba': 'NBA',
        'football_nfl': 'NFL',
        # Add other mappings as needed
    }
    return sport_mapping.get(sport_key, sport_key)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(port=port)
