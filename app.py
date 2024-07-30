from flask import Flask, render_template, render_template_string, request, jsonify
import datetime
import traceback
from single_game_data import get_game_details
from sdql_queries import get_last_5_games
from odds_api import get_sports, get_odds_data
from dateutil import parser

app = Flask(__name__)
port = 5000

@app.route('/')
def home():
    return render_template('index.html')

def convert_sport_key(sport_key):
    # Define a mapping from URL sport keys to SDQL sport keys
    sport_key_mapping = {
        'americanfootball_cfl': 'cfl',
        'baseball_mlb': 'mlb',
        # Add more mappings as needed
    }
    return sport_key_mapping.get(sport_key, sport_key)  # Default to sport_key if not found

@app.route('/game/<game_id>')
def get_single_game(game_id):
    try:
        sport_key = request.args.get('sport_key')
        date = request.args.get('date')

        if not sport_key or not date:
            return "Missing sport_key or date", 400

        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        game_details = get_game_details(sport_key, date_obj, game_id)

        if not game_details:
            return "Error fetching game details", 500

        home_team = game_details.get('homeTeam')
        away_team = game_details.get('awayTeam')
        home_score = game_details.get('homeScore', 'N/A')
        away_score = game_details.get('awayScore', 'N/A')
        odds_text = game_details.get('oddsText', 'N/A')

        home_team_last_5 = get_last_5_games(home_team)
        away_team_last_5 = get_last_5_games(away_team)

        return render_template_string("""
            <html>
            <head>
                <title>Game Details</title>
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
                <h1>Game Details</h1>
                <p>Home Team: {{ home_team }}</p>
                <p>Away Team: {{ away_team }}</p>
                <p>Score: {{ home_score }} - {{ away_score }}</p>
                <p>Odds: {{ odds_text }}</p>
                <h2>Last 5 Games - {{ home_team }}</h2>
                {% if home_team_last_5 %}
                    <table>
                        <thead>
                            <tr>
                                {% for header in home_team_last_5[0].keys() %}
                                    <th>{{ header }}</th>
                                {% endfor %}
                            </tr>
                        </thead>
                        <tbody>
                            {% for game in home_team_last_5 %}
                                <tr>
                                    {% for value in game.values() %}
                                        <td>{{ value }}</td>
                                    {% endfor %}
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p>No data available</p>
                {% endif %}
                <h2>Last 5 Games - {{ away_team }}</h2>
                {% if away_team_last_5 %}
                    <table>
                        <thead>
                            <tr>
                                {% for header in away_team_last_5[0].keys() %}
                                    <th>{{ header }}</th>
                                {% endfor %}
                            </tr>
                        </thead>
                        <tbody>
                            {% for game in away_team_last_5 %}
                                <tr>
                                    {% for value in game.values() %}
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
        """, home_team=home_team, away_team=away_team, home_score=home_score, away_score=away_score, odds_text=odds_text, home_team_last_5=home_team_last_5, away_team_last_5=away_team_last_5)

    except Exception as e:
        print('Error fetching game details:', str(e))
        traceback.print_exc()
        return "Internal Server Error", 500

@app.route('/api/sports')
def api_get_sports():
    sports = get_sports()
    if sports is not None:
        return jsonify(sports)
    else:
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

        sdql_sport_key = convert_sport_key(sport_key)

        if selected_date_start.date() < datetime.datetime.now().date():
            sdql_data = get_sdql_data(sdql_sport_key, selected_date_start)
            print(f"SDQL Data: {sdql_data}")
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
            scores, odds = get_odds_data(sport_key, selected_date_start)
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
                    'oddsText': odds_text,
                    'game_id': match['id']  # Add game ID for hyperlink
                })

            print(f"Formatted Scores: {formatted_scores}")
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
                                    <th>Home Team</th>
                                    <th>Away Team</th>
                                    <th>Home Score</th>
                                    <th>Away Score</th>
                                    <th>Odds</th>
                                    <th>Details</th>  <!-- Add column for game details -->
                                </tr>
                            </thead>
                            <tbody>
                                {% for match in result %}
                                    <tr>
                                        <td>{{ match.homeTeam }}</td>
                                        <td>{{ match.awayTeam }}</td>
                                        <td>{{ match.homeScore }}</td>
                                        <td>{{ match.awayScore }}</td>
                                        <td>{{ match.oddsText }}</td>
                                        <td><a href="/game/{{ match.game_id }}?sport_key={{ sport_key }}&date={{ current_date }}">View Details</a></td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% else %}
                        <p>No data available</p>
                    {% endif %}
                </body>
                </html>
            """, result=formatted_scores, sport_key=sport_key, current_date=current_date)
    except Exception as e:
        print('Error fetching sport scores:', str(e))
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(port=port)
