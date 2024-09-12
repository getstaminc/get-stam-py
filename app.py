from flask import Flask, render_template, jsonify, request, render_template_string
import datetime
from dateutil import parser
from odds_api import get_odds_data, get_sports
from historical_odds import get_sdql_data
from single_game_data import get_game_details
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent
from utils import convert_sport_key, mlb_totals, other_totals

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
                        .game-pair {
                            margin-bottom: 20px;
                        }
                    </style>
                </head>
                <body>
                    <h1>Game Information</h1>
                    {% if result %}
                        {% for pair in result %}
                            <div class="game-pair">
                                <table>
                                    <thead>
                                        <tr>
                                            {% for header in pair[0].keys() %}
                                                <th>{{ header }}</th>
                                            {% endfor %}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for game in pair %}
                                            <tr>
                                                {% for value in game.values() %}
                                                    <td>{{ value }}</td>
                                                {% endfor %}
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% endfor %}
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

    except request.exceptions.RequestException as e:
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
            home_team_last_5 = get_last_5_games(game_details['homeTeam'], selected_date, sport_key)
            away_team_last_5 = get_last_5_games(game_details['awayTeam'], selected_date, sport_key)

            # Fetch the last 5 games between the home team and the away team
            last_5_vs_opponent = get_last_5_games_vs_opponent(
                team=game_details['homeTeam'],
                opponent=game_details['awayTeam'],
                today_date=selected_date,
                sport_key=sport_key
            )
        except Exception as e:
            print('Error fetching last 5 games:', str(e))
            home_team_last_5 = []
            away_team_last_5 = []
            last_5_vs_opponent = []

        # Define mlb_totals function for MLB games
        def mlb_totals(runs, o_runs, total):
            try:
                if runs is None or o_runs is None or total is None:
                    return False
                return (runs + o_runs) > total
            except TypeError:
                return False

        # Define other_totals function for non-MLB games
        def other_totals(points, o_points, total):
            try:
                if points is None or o_points is None or total is None:
                    return False
                return (points + o_points) > total
            except TypeError:
                return False

        # Determine winner for MLB games
        def mlb_winner(runs, o_runs):
            if runs is not None and o_runs is not None:
                return runs > o_runs
            return None

        # Determine winner for other sports
        def other_winner(points, o_points):
            if points is not None and o_points is not None:
                return points > o_points
            return None
        
        # Helper function to safely calculate line results
        def calculate_line_result(points, line, opponent_points):
            try:
                if points is None or line is None or opponent_points is None:
                    return None  # Incomplete data, can't determine line result
                # Line evaluation based on spread value
                if line > 0:  # Underdog
                    return (points + line) > opponent_points
                else:  # Favorite
                    return (points + line) > opponent_points
            except TypeError:
                return None

        # MLB template rendering
        mlb_template = render_template_string("""
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
                        .green-bg {
                            background-color: green;
                        }
                        .red-bg {
                            background-color: red;
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
                                    <th>Site</th>
                                    <th>Team</th>
                                    <th>Runs</th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Runs</th>
                                    <th>Opponent Line</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for game in home_team_last_5 %}
                                    {% set is_total_exceeded = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                                    {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                                    <tr>
                                        <td>{{ game['date'] }}</td>
                                        <td>{{ game['site'] }}</td>
                                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                            {{ game['team'] }}
                                        </td>
                                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                            {{ game['runs'] }}
                                        </td>
                                        <td>{{ game['line'] }}</td>
                                        <td>{{ game['o:team'] }}</td>
                                        <td>{{ game['o:runs'] }}</td>
                                        <td>{{ game['o:line'] }}</td>
                                        <td class="{{ 'green-bg' if is_total_exceeded else 'red-bg' }}">
                                            {{ game['total'] }}
                                        </td>
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
                                    <th>Site</th>
                                    <th>Team</th>
                                    <th>Runs</th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Runs</th>
                                    <th>Opponent Line</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for game in away_team_last_5 %}
                                    {% set is_total_exceeded = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                                    {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                                    <tr>
                                        <td>{{ game['date'] }}</td>
                                        <td>{{ game['site'] }}</td>
                                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                            {{ game['team'] }}
                                        </td>
                                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                            {{ game['runs'] }}
                                        </td>
                                        <td>{{ game['line'] }}</td>
                                        <td>{{ game['o:team'] }}</td>
                                        <td>{{ game['o:runs'] }}</td>
                                        <td>{{ game['o:line'] }}</td>
                                        <td class="{{ 'green-bg' if is_total_exceeded else 'red-bg' }}">
                                            {{ game['total'] }}
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% else %}
                        <p>No data available</p>
                    {% endif %}
                    
                    <h2>Last 5 Games Between {{ game.homeTeam }} and {{ game.awayTeam }}</h2>
                    {% if last_5_vs_opponent %}
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Site</th>
                                    <th>Team</th>
                                    <th>Runs</th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Runs</th>
                                    <th>Opponent Line</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for game in last_5_vs_opponent %}
                                    {% set is_total_exceeded = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                                    {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                                    <tr>
                                        <td>{{ game['date'] }}</td>
                                        <td>{{ game['site'] }}</td>
                                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                            {{ game['team'] }}
                                        </td>
                                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                            {{ game['runs'] }}
                                        </td>
                                        <td>{{ game['line'] }}</td>
                                        <td>{{ game['o:team'] }}</td>
                                        <td>{{ game['o:runs'] }}</td>
                                        <td>{{ game['o:line'] }}</td>
                                        <td class="{{ 'green-bg' if is_total_exceeded else 'red-bg' }}">
                                            {{ game['total'] }}
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% else %}
                        <p>No data available</p>
                    {% endif %}
                </body>
                </html>
            """, game=game_details, home_team_last_5=home_team_last_5, away_team_last_5=away_team_last_5, last_5_vs_opponent=last_5_vs_opponent, mlb_totals=mlb_totals, mlb_winner=mlb_winner)
        
        # Other sports template rendering
        others_template = render_template_string("""
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
        .green-bg {
            background-color: green;
        }
        .red-bg {
            background-color: red;
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
                    <th>Site</th>
                    <th>Team</th>
                    <th>Points</th>                 
                    <th>Line</th>
                    <th>Opponent</th>
                    <th>Opponent Points</th>
                    <th>Opponent Line</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                {% for game in home_team_last_5 %}
                    {% set is_total_exceeded = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                    {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                    {% set line_win = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}
                    <tr>
                        <td>{{ game['date'] }}</td>
                        <td>{{ game['site'] }}</td>
                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                            {{ game['team'] }}
                        </td>
                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                            {{ game['points'] }}
                        </td>
                        <td class="{{ 'green-bg' if line_win else 'red-bg' if line_win == False else '' }}">
                            {{ game['line'] }}
                        </td>             
                        <td>{{ game['o:team'] }}</td>
                        <td>{{ game['o:points'] }}</td>
                        <td>{{ game['o:line'] }}</td>
                        <td class="{{ 'green-bg' if is_total_exceeded else 'red-bg' }}">
                            {{ game['total'] }}
                        </td>
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
                    <th>Site</th>
                    <th>Team</th>
                    <th>Points</th>
                    <th>Line</th>                 
                    <th>Opponent</th>
                    <th>Opponent Points</th>
                    <th>Opponent Line</th>                 
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                {% for game in away_team_last_5 %}
                    {% set is_total_exceeded = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                    {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                    {% set line_win = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}
                    <tr>
                        <td>{{ game['date'] }}</td>
                        <td>{{ game['site'] }}</td>
                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                            {{ game['team'] }}
                        </td>
                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                            {{ game['points'] }}
                        </td>             
                        <td class="{{ 'green-bg' if line_win else 'red-bg' if line_win == False else '' }}">
                            {{ game['line'] }}
                        </td>
                        <td>{{ game['o:team'] }}</td>
                        <td>{{ game['o:points'] }}</td>             
                        <td>{{ game['o:line'] }}</td>
                        <td class="{{ 'green-bg' if is_total_exceeded else 'red-bg' }}">
                            {{ game['total'] }}
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        <p>No data available</p>
    {% endif %}

    <h2>Last 5 Games Between {{ game.homeTeam }} and {{ game.awayTeam }}</h2>
    {% if last_5_vs_opponent %}
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Site</th>
                    <th>Team</th>
                    <th>Points</th>                 
                    <th>Line</th>
                    <th>Opponent</th>
                    <th>Opponent Points</th>
                    <th>Opponent Line</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                {% for game in last_5_vs_opponent %}
                    {% set is_total_exceeded = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                    {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                    {% set line_win = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}
                    <tr>
                        <td>{{ game['date'] }}</td>
                        <td>{{ game['site'] }}</td>
                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['team'] }}</td>
                        <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['points'] }}</td>             
                        <td class="{{ 'green-bg' if line_win else 'red-bg' if line_win == False else '' }}">
                            {{ game['line'] }}
                        </td>
                        <td>{{ game['o:team'] }}</td>
                        <td>{{ game['o:points'] }}</td>
                        <td>{{ game['o:line'] }}</td>
                        <td class="{{ 'green-bg' if is_total_exceeded else 'red-bg' }}">
                            {{ game['total'] }}
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        <p>No data available</p>
    {% endif %}
</body>
</html>
""", game=game_details, home_team_last_5=home_team_last_5, away_team_last_5=away_team_last_5, last_5_vs_opponent=last_5_vs_opponent, other_totals=other_totals, other_winner=other_winner, calculate_line_result=calculate_line_result)    

        if sport_key == 'baseball_mlb':
            return mlb_template          
        elif sport_key in ['americanfootball_nfl', 'americanfootball_ncaaf', 'NBA', 'NHL']:
            return others_template
        else:
            raise ValueError(f"Unsupported league: {sport_key}")

    except Exception as e:
        print('Error fetching game details:', str(e))
        return jsonify({'error': 'Internal Server Error'}), 500

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(port=port)