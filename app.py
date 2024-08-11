from flask import Flask, render_template, jsonify, request, render_template_string
import datetime
from dateutil import parser
from odds_api import get_odds_data, get_sports
from historical_odds import get_sdql_data
from single_game_data import get_game_details
from sdql_queries import get_last_5_games

app = Flask(__name__)
port = 5000

# Route to fetch available sports
@app.route('/api/sports')
def api_get_sports():
    sports = get_sports()
    if sports is not None:
        return jsonify(sports)
    else:
        return jsonify({'error': 'Internal Server Error'}), 500

# Route to fetch scores and odds for a specific sport and date
@app.route('/sports/<sport_key>')
def get_sport_scores(sport_key):
    try:
        current_date = request.args.get('date', None)
        if not current_date:
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')

        selected_date_start = datetime.datetime.strptime(current_date, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        selected_date_end = selected_date_start + datetime.timedelta(hours=23, minutes=59, seconds=59)

        sdql_sport_key = convert_sport_key(sport_key)

        if selected_date_start.date() < datetime.datetime.now().date():
            sdql_data = get_sdql_data(sdql_sport_key, selected_date_start)
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
                                    <th>Details</th>
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

    except requests.exceptions.RequestException as e:
        print('Request error:', str(e))
        return jsonify({'error': 'Request Error'}), 500
    except Exception as e:
        print('Error fetching scores:', str(e))
        return jsonify({'error': 'Internal Server Error'}), 500

# Route to fetch and display details for a specific game
@app.route('/game/<game_id>')
def game_details(game_id):
    sport_key = request.args.get('sport_key')
    date = request.args.get('date')
    
    if not sport_key or not date:
        return jsonify({'error': 'Missing sport_key or date'}), 400

    try:
        selected_date = datetime.datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        game_details = get_game_details(sport_key, selected_date, game_id)
        
        if not game_details:
            return jsonify({'error': 'Game not found'}), 404

        try:
            home_team_last_5 = get_last_5_games(game_details['homeTeam'], selected_date)
            away_team_last_5 = get_last_5_games(game_details['awayTeam'], selected_date)
        except Exception as e:
            print('Error fetching last 5 games:', str(e))
            home_team_last_5 = []
            away_team_last_5 = []
            
        return render_template_string("""
            <html>
            <head>
                <title>Game Details</title>
                <style>
                    table {
                        width: 70%;
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
                <table>
                    <tr>
                        <th>Home Team</th>
                        <td>{{ game.homeTeam }}</td>
                    </tr>
                    <tr>
                        <th>Away Team</th>
                        <td>{{ game.awayTeam }}</td>
                    </tr>
                    <tr>
                        <th>Home Score</th>
                        <td>{{ game.homeScore }}</td>
                    </tr>
                    <tr>
                        <th>Away Score</th>
                        <td>{{ game.awayScore }}</td>
                    </tr>
                    <tr>
                        <th>Odds</th>
                        <td>{{ game.oddsText }}</td>
                    </tr>
                </table>
                
                <h2>Last 5 Games - Home Team</h2>
                {% if home_team_last_5 %}
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Team</th>
                                <th>Site</th>
                                <th>Runs</th>
                                <th>Total</th>
                                <th>Opponent</th>
                                <th>Opponent Runs</th>
                                <th>Opponent Line</th>
                                <th>Line</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for game in home_team_last_5 %}
                                <tr>
                                    <td>{{ game['date'] }}</td>
                                    <td>{{ game['team'] }}</td>
                                    <td>{{ game['site'] }}</td>
                                    <td>{{ game['runs'] }}</td>
                                    <td>{{ game['total'] }}</td>
                                    <td>{{ game['o:team'] }}</td>
                                    <td>{{ game['o:runs'] }}</td>
                                    <td>{{ game['o:line'] }}</td>
                                    <td>{{ game['line'] }}</td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p>No data available</p>
                {% endif %}
                
                <h2>Last 5 Games - Away Team</h2>
                {% if away_team_last_5 %}
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Team</th>
                                <th>Site</th>
                                <th>Runs</th>
                                <th>Total</th>
                                <th>Opponent</th>
                                <th>Opponent Runs</th>
                                <th>Opponent Line</th>
                                <th>Line</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for game in away_team_last_5 %}
                                <tr>
                                    <td>{{ game['date'] }}</td>
                                    <td>{{ game['team'] }}</td>
                                    <td>{{ game['site'] }}</td>
                                    <td>{{ game['runs'] }}</td>
                                    <td>{{ game['total'] }}</td>
                                    <td>{{ game['o:team'] }}</td>
                                    <td>{{ game['o:runs'] }}</td>
                                    <td>{{ game['o:line'] }}</td>
                                    <td>{{ game['line'] }}</td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p>No data available</p>
                {% endif %}
            </body>
            </html>
        """, game=game_details, home_team_last_5=home_team_last_5, away_team_last_5=away_team_last_5)

    except Exception as e:
        print('Error fetching game details:', str(e))
        return jsonify({'error': 'Internal Server Error'}), 500



# Helper function to convert sport keys
def convert_sport_key(sport_key):
    sport_mapping = {
        'baseball_mlb': 'MLB',
        'basketball_nba': 'NBA',
        'football_nfl': 'NFL',
        'icehockey_nhl': 'NHL',
        # Add other mappings as needed
    }
    return sport_mapping.get(sport_key, sport_key)

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(port=port)
