from flask import Flask, render_template, jsonify, request, render_template_string, Blueprint, redirect, url_for
from datetime import datetime, timedelta  # Import timedelta here
import pytz
from dateutil import parser
from odds_api import get_odds_data, get_sports
from historical_odds import get_sdql_data
from single_game_data import get_game_details
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent
from utils import convert_sport_key, mlb_totals, other_totals
from betting_guide import betting_guide

app = Flask(__name__)
port = 5000

# Define the Eastern timezone
eastern_tz = pytz.timezone('US/Eastern')

# app.py
from betting_guide import betting_guide  # Add this line

app.register_blueprint(betting_guide)  # Register the blueprint


# Route to fetch available sports
@app.route('/api/sports')
def api_get_sports():
    sports = get_sports()
    if sports is not None:
        return jsonify(sports)
    else:
        return jsonify({'error': 'Internal Server Error'}), 500
    
# Function to convert UTC time to Eastern time
def convert_to_eastern(utc_time):
    if utc_time is None:
        return None
    utc_time = utc_time.replace(tzinfo=pytz.utc)
    eastern_time = utc_time.astimezone(eastern_tz)
    return eastern_time

# Route to fetch scores and odds for a specific sport and date
@app.route('/sports/<sport_key>')
def get_sport_scores(sport_key):
    try:
        current_date = request.args.get('date', None)
        if not current_date:
            current_date = datetime.now(eastern_tz).strftime('%Y-%m-%d')

        selected_date_start = datetime.strptime(current_date, '%Y-%m-%d').replace(tzinfo=eastern_tz)
        selected_date_end = selected_date_start + timedelta(hours=23, minutes=59, seconds=59)

        sdql_sport_key = convert_sport_key(sport_key)

        if selected_date_start.date() < datetime.now(eastern_tz).date():
            sdql_data = get_sdql_data(sdql_sport_key, selected_date_start)
            return render_template_string("""
                <html>
                <head>
                    <!-- Google tag (gtag.js) -->
                    <script async src="https://www.googletagmanager.com/gtag/js?id=G-578SDWQPSK"></script>
                    <script>
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    gtag('js', new Date());

                    gtag('config', 'G-578SDWQPSK');
                    </script>                      
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
                commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
                commence_date_eastern = convert_to_eastern(commence_date)

                if commence_date_eastern.date() == selected_date_start.date():
                    filtered_scores.append(score)

            formatted_scores = []
            for match in filtered_scores:
                home_team = match.get('home_team', 'N/A')
                away_team = match.get('away_team', 'N/A')
                home_score = match['scores'][0]['score'] if match.get('scores') else 'N/A'
                away_score = match['scores'][1]['score'] if match.get('scores') else 'N/A'

                match_odds = next((odds_match for odds_match in odds if odds_match['id'] == match['id']), None)
                odds_data = {'h2h': [], 'spreads': [], 'totals': []}

                if match_odds:
                    for bookmaker in match_odds['bookmakers']:
                        for market in bookmaker['markets']:
                            market_key = market['key']
                            for outcome in market['outcomes']:
                                outcome_text = f"{outcome['name']}"
                                if market_key in ['spreads', 'totals'] and 'point' in outcome:
                                    outcome_text += f": {outcome['point']}"
                                if market_key == 'h2h':
                                    price = outcome['price']
                                    if price > 0:
                                        outcome_text += f": +{price}"
                                    else:
                                        outcome_text += f": {price}"
                                else:
                                    price = outcome['price']
                                    if price > 0:
                                        outcome_text += f" +{price}"
                                    else:
                                        outcome_text += f" {price}"
                                odds_data[market_key].append(outcome_text)

                formatted_scores.append({
                    'homeTeam': home_team,
                    'awayTeam': away_team,
                    #cores are purposefully switched investigating why they're backwards
                    'homeScore': away_score,
                    'awayScore': home_score,
                    'odds': odds_data,
                    'game_id': match['id'],
                })

            return render_template_string("""
                <html>
                <head>
                    <title>Game Info</title>
                    <style>
                        table {
                            width: 80%;
                            border-collapse: collapse;
                            margin-left: auto;
                            margin-right: auto;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #007bff;
                            color: white;
                        }
                        tr:nth-child(even) {
                            background-color: #d8ebff;
                        }
                        tr:nth-child(odd) {
                            background-color: #FFFFFF;
                        }
                        .odds-category {
                            margin-top: 10px;
                        }
                        .odds-category h4 {
                            margin-bottom: 5px;
                            color: #007bff;
                        }
                        .odds-category ul {
                            list-style-type: none;
                            padding: 0;
                        }
                        .center {
                            text-align: center;
                        }
                        
                    </style>
                </head>
                <body>
                    <h1 class="center">Game Information</h1>
                    {% if result %}
                        <table>
                            <thead>
                                <tr>
                                    <th>Home Team</th>
                                    <th>Away Team</th>
                                    <th>Home Score</th>
                                    <th>Away Score</th>
                                    <th>Odds</th>
                                    {% if sport_key not in ['mma_mixed_martial_arts', 'soccer_epl', 'soccer_france_ligue_one', 'soccer_germany_bundesliga', 'soccer_italy_serie_a', 'soccer_spain_la_liga', 'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'boxing_boxing'] %}
                                        <th>Details</th>
                                          
                                    {% endif %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for match in result %}
                                    <tr>
                                        <td>{{ match.homeTeam }}</td>
                                        <td>{{ match.awayTeam }}</td>
                                        <td>{{ match.awayScore }}</td>
                                        <td>{{ match.homeScore }}</td>
                                        <td>
                                            <div class="odds-category">
                                                <h4>H2H:</h4>
                                                <ul>
                                                    {% for odd in match.odds.h2h %}
                                                        <li>{{ odd }}</li>
                                                    {% endfor %}
                                                </ul>
                                                <h4>Spreads:</h4>
                                                <ul>
                                                    {% for odd in match.odds.spreads %}
                                                        <li>{{ odd }}</li>
                                                    {% endfor %}
                                                </ul>
                                                <h4>Totals:</h4>
                                                <ul>
                                                    {% for odd in match.odds.totals %}
                                                        <li>{{ odd }}</li>
                                                    {% endfor %}
                                                </ul>
                                            </div>
                                        </td>
                                        {% if sport_key not in ['mma_mixed_martial_arts', 'soccer_epl', 'soccer_france_ligue_one', 'soccer_germany_bundesliga', 'soccer_italy_serie_a', 'soccer_spain_la_liga', 'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'boxing_boxing'] %}
                                            <td>
                                                <a href="/game/{{ match.game_id }}?sport_key={{ sport_key }}&date={{ current_date }}">View Details</a>
                                            </td>
                                        {% endif %}
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% else %}
                        <p class="center">No games on this date</p>
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
        selected_date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=eastern_tz)
        game_details = get_game_details(sport_key, selected_date, game_id)

        if not game_details:
            return redirect(url_for('home'))

        try:
            home_team_last_5 = get_last_5_games(game_details['homeTeam'], selected_date, sport_key) or []
            away_team_last_5 = get_last_5_games(game_details['awayTeam'], selected_date, sport_key) or []

            # Fetch the last 5 games between the home team and the away team
            last_5_vs_opponent = get_last_5_games_vs_opponent(
                team=game_details['homeTeam'],
                opponent=game_details['awayTeam'],
                today_date=selected_date,
                sport_key=sport_key
            ) or []
        except Exception as e:
            print('Error fetching last 5 games:', str(e))
            home_team_last_5 = []
            away_team_last_5 = []
            last_5_vs_opponent = []

        # Prepare data for rendering
        for game in home_team_last_5 + away_team_last_5 + last_5_vs_opponent:
            if 'date' in game:
                date_str = str(game['date'])  # Ensure the date is a string
                game['date'] = f"{date_str[4:6]}/{date_str[6:8]}/{date_str[:4]}"

        # Define mlb_totals function for MLB games
        def mlb_totals(runs, o_runs, total):
            try:
                if runs is None or o_runs is None or total is None:
                    return False, ''
                total_score = runs + o_runs
                if total_score > total:
                    return True, 'green-bg'
                elif total_score < total:
                    return False, 'red-bg'
                else:
                    return False, 'grey-bg'
            except TypeError:
                return False, ''

        # Define other_totals function for non-MLB games
        def other_totals(points, o_points, total):
            try:
                if points is None or o_points is None or total is None:
                    return False, ''
                total_score = points + o_points
                if total_score > total:
                    return True, 'green-bg'
                elif total_score < total:
                    return False, 'red-bg'
                else:
                    return False, 'grey-bg'
            except TypeError:
                return False, ''

        # Determine winner for MLB games
        def mlb_winner(runs, o_runs):
            if runs is not None and o_runs is not None:
                return runs > o_runs
            return None
        
        # Define nhl_totals function for NHL games
        def nhl_totals(goals, o_goals, total):
            try:
                if goals is None or o_goals is None or total is None:
                    return False, ''
                total_score = goals + o_goals
                if total_score > total:
                    return True, 'green-bg'
                elif total_score < total:
                    return False, 'red-bg'
                else:
                    return False, 'grey-bg'
            except TypeError:
                return False, ''

        # Determine winner for NHL games
        def nhl_winner(goals, o_goals):
            if goals is not None and o_goals is not None:
                return goals > o_goals
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
                    return None, None  # Incomplete data, can't determine line result
                # Line evaluation based on spread value
                result = (points + line) > opponent_points  # True if win
                if result:
                    return True, 'green-bg'  # Win
                elif (points + line) < opponent_points:
                    return False, 'red-bg'  # Loss
                else:
                    return False, 'grey-bg'  # Push
            except TypeError:
                return None, None

        # MLB template rendering
        mlb_template = render_template_string("""
           <html>
                <head>
                    <!-- Google tag (gtag.js) -->
                    <script async src="https://www.googletagmanager.com/gtag/js?id=G-578SDWQPSK"></script>
                    <script>
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    gtag('js', new Date());

                    gtag('config', 'G-578SDWQPSK');
                    </script>                          
                    <title>Game Details</title>
                    <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
                    <style>
                        body {
                            background-color: #f9f9f9; /* Light background */
                            font-family: 'Poppins', sans-serif;
                            margin: 0;
                            padding: 20px;
                        }

                        header {
                            background-color: #007bff; /* Primary color */
                            padding: 10px 20px;
                            text-align: center;
                            color: white;
                        }

                        nav a {
                            color: white;
                            text-decoration: none;
                            margin: 0 10px;
                            display: block;                  
                        }

                        h1 {
                            margin: 20px 0;
                        }

                        h2 {
                            margin-top: 30px;
                        }

                        table {
                            width: 90%;
                            border-collapse: collapse;
                            margin-bottom: 20px;
                        }

                        table, th, td {
                            border: 1px solid black;
                        }

                        th, td {
                            padding: 4px;
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

                        .grey-bg {
                            background-color: grey;
                        }

                        #gamesList {
                        list-style-type: none;
                        padding: 0;
                        }
                
                        .game-card {
                            border: 1px solid #ddd;
                            border-radius: 8px;
                            padding: 20px;
                            margin: 10px 0;
                            background-color: #fff; /* Card background */
                            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                        }

                        button, a {
                            background-color: #007bff; /* Primary color */
                            color: white;
                            border: none;
                            border-radius: 5px;
                            padding: 10px 15px;
                            text-decoration: none;
                            transition: background-color 0.3s;
                        }

                        button:hover, a:hover {
                            background-color: #0056b3; /* Darker shade on hover */
                        }

                        /* Responsive Styles */
                        @media only screen and (max-width: 600px) {
                            body {
                                font-size: 14px;
                            }
                        }
                        @media only screen and (min-width: 601px) and (max-width: 768px) {
                            body {
                                font-size: 16px;
                            }
                        }
                        @media only screen and (min-width: 769px) {
                            body {
                                font-size: 18px;
                            }
                        }
                        .info-icon {
                            cursor: pointer;
                            color: black; /* Color of the info icon */
                            margin-left: 1px; /* Space between title and icon */
                            padding: 1px;
                            border: 1px solid black; /* Border color */
                            border-radius: 50%; /* Makes the icon circular */
                            width: 10px; /* Width of the icon */
                            height: 10px; /* Height of the icon */
                            display: inline-flex; /* Allows for centering */
                            align-items: center; /* Center content vertically */
                            justify-content: center; /* Center content horizontally */
                            font-size: 14px; /* Font size of the "i" */
                        }

                        .info-icon:hover::after {
                            content: attr(title);
                            position: absolute;
                            background: #fff;
                            border: 1px solid #ccc;
                            padding: 5px;
                            border-radius: 4px;
                            white-space: nowrap;
                            z-index: 10;
                            top: 20px; /* Adjust as needed */
                            left: 0;
                            box-shadow: 0 0 10px rgba(0,0,0,0.2);
                        }               
                        .color-keys {
                            margin: 20px 0;
                            padding: 15px;
                            border: 1px solid #ddd;
                            background-color: #f9f9f9;
                        }

                        .color-key h2 {
                            margin: 0 0 10px;
                        }

                        .color-key table {
                            width: 100%;
                            border-collapse: collapse;
                        }

                        .color-key th, .color-key td {
                            padding: 8px;
                            text-align: left;
                            border: 1px solid #ccc;
                        }

                        .color-key th {
                            background-color: #f2f2f2;
                        }
                        .color-key {
                            display: none; /* Hide by default */
                            background-color: #f9f9f9; /* Background color for the key */
                            border: 1px solid #ccc; /* Border for the key */
                            padding: 5px;
                            position: absolute; /* Position it relative to the header */
                            z-index: 10; /* Ensure it appears above other elements */
                        }

                        th {
                            position: relative; /* Needed for absolute positioning of the color key */
                        }

                        th:hover .color-key {
                            display: block; /* Show the key on hover */
                        }                      
                      
                    </style>

                </head>
                <body>
                     <header>
                        <nav>
                            <a href="/">Home</a>
                        </nav>
                    </header>                         
                    <h1>Game Details</h1>
                    <table >
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
                       <div class="game-card">                       
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Site</th>
                                    <th>Team <span class="info-icon">i</span>
                                       <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>       
                                    </th>
                                    <th>Runs <span class="info-icon">i</span>
                                    
                                        <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>      
                                    </th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Runs</th>
                                    <th>Opponent Line</th>
                                    <th>Total <span class="info-icon">i</span>
                                         <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>     
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for game in home_team_last_5 %}
                                    {% set is_total_exceeded, total_class = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                                    {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                                    <tr>
                                        <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
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
                                        <td class="{{ total_class }}">
                                            {{ game['total'] }}
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                      </div>                        
                    {% else %}
                        <p class="center">No games on this date</p>
                    {% endif %}
                    
                    <h2>Last 5 Games - Away Team</h2>
                    {% if away_team_last_5 %}
                      <div class="game-card">                        
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Site</th>
                                    <th>Team <span class="info-icon">i</span>
                                       <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>       
                                    </th>
                                    <th>Runs <span class="info-icon">i</span>
                                        <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>      
                                    </th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Runs</th>
                                    <th>Opponent Line</th>
                                    <th>Total <span class="info-icon">i</span>
                                         <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>     
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for game in away_team_last_5 %}
                                    {% set is_total_exceeded, total_class = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                                    {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                                    <tr>
                                        <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
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
                                        <td class="{{ total_class }}">
                                            {{ game['total'] }}
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                      </div>                        
                    {% else %}
                        <p class="center">No games on this date</p>
                    {% endif %}
                    
                    <h2>Last 5 Games Between {{ game.homeTeam }} and {{ game.awayTeam }}</h2>
                    {% if last_5_vs_opponent %}
                       <div class="game-card">                       
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Site</th>
                                    <th>Team <span class="info-icon">i</span>
                                       <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>       
                                    </th>
                                    <th>Runs <span class="info-icon">i</span>
                                        <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>      
                                    </th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Runs</th>
                                    <th>Opponent Line</th>
                                    <th>Total <span class="info-icon">i</span>
                                         <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>     
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for game in last_5_vs_opponent %}
                                    {% set is_total_exceeded, total_class = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                                    {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                                    <tr>
                                        <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
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
                                        <td class="{{ total_class }}">
                                            {{ game['total'] }}
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                       </div>                        
                    {% else %}
                        <p class="center">No games on this date</p>
                    {% endif %}
                </body>
                </html>
            """, game=game_details, home_team_last_5=home_team_last_5, away_team_last_5=away_team_last_5, last_5_vs_opponent=last_5_vs_opponent, mlb_totals=mlb_totals, mlb_winner=mlb_winner)
        
        # NHL template rendering
        nhl_template = render_template_string("""
            <html>
            <head>
                <!-- Google tag (gtag.js) -->
                    <script async src="https://www.googletagmanager.com/gtag/js?id=G-578SDWQPSK"></script>
                    <script>
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    gtag('js', new Date());

                    gtag('config', 'G-578SDWQPSK');
                    </script>                              
                <title>Game Details</title>
                <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
                <style>
                        body {
                            background-color: #f9f9f9; /* Light background */
                            font-family: 'Poppins', sans-serif;
                            margin: 0;
                            padding: 20px;
                        }

                        header {
                            background-color: #007bff; /* Primary color */
                            padding: 10px 20px;
                            text-align: center;
                            color: white;
                        }

                        nav a {
                            color: white;
                            text-decoration: none;
                            margin: 0 10px;
                            display: block;                  
                        }

                        h1 {
                            margin: 20px 0;
                        }

                        h2 {
                            margin-top: 30px;
                        }

                        table {
                            width: 90%;
                            border-collapse: collapse;
                            margin-bottom: 20px;
                        }

                        table, th, td {
                            border: 1px solid black;
                        }

                        th, td {
                            padding: 4px;
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

                        .grey-bg {
                            background-color: grey;
                        }

                        #gamesList {
                        list-style-type: none;
                        padding: 0;
                        }
                
                        .game-card {
                            border: 1px solid #ddd;
                            border-radius: 8px;
                            padding: 20px;
                            margin: 10px 0;
                            background-color: #fff; /* Card background */
                            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                        }

                        button, a {
                            background-color: #007bff; /* Primary color */
                            color: white;
                            border: none;
                            border-radius: 5px;
                            padding: 10px 15px;
                            text-decoration: none;
                            transition: background-color 0.3s;
                        }

                        button:hover, a:hover {
                            background-color: #0056b3; /* Darker shade on hover */
                        }

                        /* Responsive Styles */
                        @media only screen and (max-width: 600px) {
                            body {
                                font-size: 14px;
                            }
                        }
                        @media only screen and (min-width: 601px) and (max-width: 768px) {
                            body {
                                font-size: 16px;
                            }
                        }
                        @media only screen and (min-width: 769px) {
                            body {
                                font-size: 18px;
                            }
                        }
                        .info-icon {
                            cursor: pointer;
                            color: black; /* Color of the info icon */
                            margin-left: 1px; /* Space between title and icon */
                            padding: 1px;
                            border: 1px solid black; /* Border color */
                            border-radius: 50%; /* Makes the icon circular */
                            width: 10px; /* Width of the icon */
                            height: 10px; /* Height of the icon */
                            display: inline-flex; /* Allows for centering */
                            align-items: center; /* Center content vertically */
                            justify-content: center; /* Center content horizontally */
                            font-size: 14px; /* Font size of the "i" */
                        }

                        .info-icon:hover::after {
                            content: attr(title);
                            position: absolute;
                            background: #fff;
                            border: 1px solid #ccc;
                            padding: 5px;
                            border-radius: 4px;
                            white-space: nowrap;
                            z-index: 10;
                            top: 20px; /* Adjust as needed */
                            left: 0;
                            box-shadow: 0 0 10px rgba(0,0,0,0.2);
                        }               
                        .color-keys {
                            margin: 20px 0;
                            padding: 15px;
                            border: 1px solid #ddd;
                            background-color: #f9f9f9;
                        }

                        .color-key h2 {
                            margin: 0 0 10px;
                        }

                        .color-key table {
                            width: 100%;
                            border-collapse: collapse;
                        }

                        .color-key th, .color-key td {
                            padding: 8px;
                            text-align: left;
                            border: 1px solid #ccc;
                        }

                        .color-key th {
                            background-color: #f2f2f2;
                        }
                        .color-key {
                            display: none; /* Hide by default */
                            background-color: #f9f9f9; /* Background color for the key */
                            border: 1px solid #ccc; /* Border for the key */
                            padding: 5px;
                            position: absolute; /* Position it relative to the header */
                            z-index: 10; /* Ensure it appears above other elements */
                        }

                        th {
                            position: relative; /* Needed for absolute positioning of the color key */
                        }

                        th:hover .color-key {
                            display: block; /* Show the key on hover */
                        }                      
                      
                    </style>
            </head>
            <body>
                <header>
                        <nav>
                            <a href="/">Home</a>
                        </nav>
                    </header>                               
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
                <div><p>Hover over column titles for color meanings</p></div>
                <h2>Last 5 Games - Home Team</h2>
                {% if home_team_last_5 %}
                    <table>
                        <thead>
                            <tr>
                                    <th>Date</th>
                                    <th>Site</th>
                                    <th>Team <span class="info-icon">i</span>
                                       <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>       
                                    </th>
                                    <th>Goals <span class="info-icon">i</span>
                                        <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>      
                                    </th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Goals</th>
                                    <th>Opponent Line</th>
                                    <th>Total <span class="info-icon">i</span>
                                         <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>     
                                    </th>
                                </tr>
                        </thead>
                        <tbody>
                            {% for game in home_team_last_5 %}
                                {% set is_total_exceeded, total_class = nhl_totals(game.get('goals', 0), game.get('o:goals', 0), game.get('total', 0)) %}
                                {% set is_winner = nhl_winner(game.get('goals', 0), game.get('o:goals', 0)) %}
                                <tr>
                                    <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                                    <td>{{ game['site'] }}</td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                        {{ game['team'] }}
                                    </td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                        {{ game['goals'] }}
                                    </td>
                                    <td>{{ game['line'] }}</td>
                                    <td>{{ game['o:team'] }}</td>
                                    <td>{{ game['o:goals'] }}</td>
                                    <td>{{ game['o:line'] }}</td>
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No games on this date</p>
                {% endif %}

                <h2>Last 5 Games - Away Team</h2>
                {% if away_team_last_5 %}
                    <table>
                        <thead>
                            <tr>
                                    <th>Date</th>
                                    <th>Site</th>
                                    <th>Team <span class="info-icon">i</span>
                                       <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>       
                                    </th>
                                    <th>Goals <span class="info-icon">i</span>
                                        <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>      
                                    </th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Goals</th>
                                    <th>Opponent Line</th>
                                    <th>Total <span class="info-icon">i</span>
                                         <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>     
                                    </th>
                                </tr>
                        </thead>
                        <tbody>
                            {% for game in away_team_last_5 %}
                                {% set is_total_exceeded, total_class = nhl_totals(game.get('goals', 0), game.get('o:goals', 0), game.get('total', 0)) %}
                                {% set is_winner = nhl_winner(game.get('goals', 0), game.get('o:goals', 0)) %}
                                <tr>
                                    <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                                    <td>{{ game['site'] }}</td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                        {{ game['team'] }}
                                    </td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                        {{ game['goals'] }}
                                    </td>
                                    <td>{{ game['line'] }}</td>
                                    <td>{{ game['o:team'] }}</td>
                                    <td>{{ game['o:goals'] }}</td>
                                    <td>{{ game['o:line'] }}</td>
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No games on this date</p>
                {% endif %}

                <h2>Last 5 Games Between {{ game.homeTeam }} and {{ game.awayTeam }}</h2>
                {% if last_5_vs_opponent %}
                    <table>
                        <thead>
                            <tr>
                                    <th>Date</th>
                                    <th>Site</th>
                                    <th>Team <span class="info-icon">i</span>
                                       <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>       
                                    </th>
                                    <th>Goals <span class="info-icon">i</span>
                                        <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>      
                                    </th>
                                    <th>Line</th>
                                    <th>Opponent</th>
                                    <th>Opponent Goals</th>
                                    <th>Opponent Line</th>
                                    <th>Total <span class="info-icon">i</span>
                                         <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>     
                                    </th>
                                </tr>
                        </thead>
                        <tbody>
                            {% for game in last_5_vs_opponent %}
                                {% set is_total_exceeded, total_class = nhl_totals(game.get('goals', 0), game.get('o:goals', 0), game.get('total', 0)) %}
                                {% set is_winner = nhl_winner(game.get('goals', 0), game.get('o:goals', 0)) %}
                                <tr>
                                    <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                                    <td>{{ game['site'] }}</td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['team'] }}</td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['goals'] }}</td>             
                                    <td>{{ game['line'] }}</td>
                                    <td>{{ game['o:team'] }}</td>
                                    <td>{{ game['o:goals'] }}</td>
                                    <td>{{ game['o:line'] }}</td>
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No games on this date</p>
                {% endif %}
            </body>
            </html>
        """, game=game_details, home_team_last_5=home_team_last_5, away_team_last_5=away_team_last_5, last_5_vs_opponent=last_5_vs_opponent, nhl_totals=nhl_totals, nhl_winner=nhl_winner)

        # Other sports template rendering
        others_template = render_template_string("""
            <html>
            <head>
                <!-- Google tag (gtag.js) -->
                    <script async src="https://www.googletagmanager.com/gtag/js?id=G-578SDWQPSK"></script>
                    <script>
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    gtag('js', new Date());

                    gtag('config', 'G-578SDWQPSK');
                    </script>                                 
                <title>Game Details</title>
                <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
                <style>
                        body {
                            background-color: #f9f9f9; /* Light background */
                            font-family: 'Poppins', sans-serif;
                            margin: 0;
                            padding: 20px;
                        }

                        header {
                            background-color: #007bff; /* Primary color */
                            padding: 10px 20px;
                            text-align: center;
                            color: white;
                            border-radius: 5px;                     
                        }

                        nav a {
                            color: white;
                            text-decoration: none;
                            margin: 0 10px;
                            display: block;                     
                        }

                        h1 {
                            margin: 20px 0;
                        }

                        h2 {
                            margin-top: 30px;
                        }

                        table {
                            width: 90%;
                            border-collapse: collapse;
                            margin-bottom: 20px;
                        }

                        table, th, td {
                            border: 1px solid black;
                        }

                        th, td {
                            padding: 4px;
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

                        .grey-bg {
                            background-color: grey;
                        }

                        #gamesList {
                        list-style-type: none;
                        padding: 0;
                        }
                
                        .game-card {
                            border: 1px solid #ddd;
                            border-radius: 8px;
                            padding: 20px;
                            margin: 10px 0;
                            background-color: #fff; /* Card background */
                            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                        }

                        button, a {
                            background-color: #007bff; /* Primary color */
                            color: white;
                            border: none;
                            border-radius: 5px;
                            padding: 10px 15px;
                            text-decoration: none;
                            transition: background-color 0.3s;
                        }

                        button:hover, a:hover {
                            background-color: #0056b3; /* Darker shade on hover */
                        }
                        .info-icon {
                            cursor: pointer;
                            color: black; /* Color of the info icon */
                            margin-left: 1px; /* Space between title and icon */
                            padding: 1px;
                            border: 1px solid black; /* Border color */
                            border-radius: 50%; /* Makes the icon circular */
                            width: 10px; /* Width of the icon */
                            height: 10px; /* Height of the icon */
                            display: inline-flex; /* Allows for centering */
                            align-items: center; /* Center content vertically */
                            justify-content: center; /* Center content horizontally */
                            font-size: 14px; /* Font size of the "i" */
                        }

                        .info-icon:hover::after {
                            content: attr(title);
                            position: absolute;
                            background: #fff;
                            border: 1px solid #ccc;
                            padding: 5px;
                            border-radius: 4px;
                            white-space: nowrap;
                            z-index: 10;
                            top: 20px; /* Adjust as needed */
                            left: 0;
                            box-shadow: 0 0 10px rgba(0,0,0,0.2);
                        }                         
                                                 
                        .color-keys {
                            margin: 20px 0;
                            padding: 15px;
                            border: 1px solid #ddd;
                            background-color: #f9f9f9;
                        }

                        .color-key h2 {
                            margin: 0 0 10px;
                        }

                        .color-key table {
                            width: 100%;
                            border-collapse: collapse;
                        }

                        .color-key th, .color-key td {
                            padding: 8px;
                            text-align: left;
                            border: 1px solid #ccc;
                        }

                        .color-key th {
                            background-color: #f2f2f2;
                        }
                        .color-key {
                            display: none; /* Hide by default */
                            background-color: #f9f9f9; /* Background color for the key */
                            border: 1px solid #ccc; /* Border for the key */
                            padding: 5px;
                            position: absolute; /* Position it relative to the header */
                            z-index: 10; /* Ensure it appears above other elements */
                        }

                        th {
                            position: relative; /* Needed for absolute positioning of the color key */
                        }

                        th:hover .color-key {
                            display: block; /* Show the key on hover */
                        }                         

                        /* Responsive Styles */
                        @media only screen and (max-width: 600px) {
                            body {
                                font-size: 14px;
                            }
                        }
                        @media only screen and (min-width: 601px) and (max-width: 768px) {
                            body {
                                font-size: 16px;
                            }
                        }
                        @media only screen and (min-width: 769px) {
                            body {
                                font-size: 18px;
                            }
                        }
                    </style>
            </head>
            <body>
                <header>
                  <nav>
                    <a href="/">Home</a>
                    </nav>
                </header> 
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
                                <th>Team <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                                <th>Points <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>                 
                                <th>Spread <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Spread was covered</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Spread was not covered</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Spread was a push</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                                <th>Opponent</th>
                                <th>Opponent Points</th>
                                <th>Opponent Line</th>
                                <th>Total <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for game in home_team_last_5 %}
                                {% set is_total_exceeded, total_class = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                                {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                                {% set line_win, line_class = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}                 
                                <tr>
                                    <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                                    <td>{{ game['site'] }}</td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                        {{ game['team'] }}
                                    </td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                        {{ game['points'] }}
                                    </td>
                                    <td class="{{ line_class }}">
                                        {{ game['line'] }}
                                    </td>             
                                    <td>{{ game['o:team'] }}</td>
                                    <td>{{ game['o:points'] }}</td>
                                    <td>{{ game['o:line'] }}</td>
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No games on this date</p>
                {% endif %}

                <h2>Last 5 Games - Away Team</h2>
                {% if away_team_last_5 %}
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Site</th>
                                <th>Team <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                                <th>Points <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>                 
                                <th>Spread <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Spread was covered</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Spread was not covered</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Spread was a push</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                                <th>Opponent</th>
                                <th>Opponent Points</th>
                                <th>Opponent Line</th>
                                <th>Total <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for game in away_team_last_5 %}
                                {% set is_total_exceeded, total_class = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                                {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                                {% set line_win, line_class = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}
                                <tr>
                                    <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                                    <td>{{ game['site'] }}</td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                        {{ game['team'] }}
                                    </td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                        {{ game['points'] }}
                                    </td>             
                                    <td class="{{ line_class }}">
                                        {{ game['line'] }}
                                    </td>
                                    <td>{{ game['o:team'] }}</td>
                                    <td>{{ game['o:points'] }}</td>             
                                    <td>{{ game['o:line'] }}</td>
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No games on this date</p>
                {% endif %}

                <h2>Last 5 Games Between {{ game.homeTeam }} and {{ game.awayTeam }}</h2>
                {% if last_5_vs_opponent %}
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Site</th>
                                <th>Team <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                                <th>Points <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Team won</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Team lost</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>                 
                                <th>Spread <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Spread was covered</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Spread was not covered</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Spread was a push</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                                <th>Opponent</th>
                                <th>Opponent Points</th>
                                <th>Opponent Line</th>
                                <th>Total <span class="info-icon">i</span>
                                    <span class="color-key">
                                              <div class="color-keys">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                <th>Color</th>
                                                                <th>Meaning</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr>
                                                                <td style="background-color: green;">&nbsp;</td>
                                                                <td>Total went over</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: red;">&nbsp;</td>
                                                                <td>Total went under</td>
                                                            </tr>
                                                            <tr>
                                                                <td style="background-color: grey;">&nbsp;</td>
                                                                <td>Push (tie with total)</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div> 
                                        </span>             
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for game in last_5_vs_opponent %}
                                {% set is_total_exceeded, total_class = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                                {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                                {% set line_win, line_class = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}
                                <tr>
                                    <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                                    <td>{{ game['site'] }}</td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['team'] }}</td>
                                    <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['points'] }}</td>             
                                    <td class="{{ line_class }}">
                                        {{ game['line'] }}
                                    </td>
                                    <td>{{ game['o:team'] }}</td>
                                    <td>{{ game['o:points'] }}</td>
                                    <td>{{ game['o:line'] }}</td>
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No games on this date</p>
                {% endif %}
            </body>
            </html>
        """, game=game_details, home_team_last_5=home_team_last_5, away_team_last_5=away_team_last_5, last_5_vs_opponent=last_5_vs_opponent, other_totals=other_totals, other_winner=other_winner, calculate_line_result=calculate_line_result)    

        if sport_key == 'baseball_mlb':
            return mlb_template 
        elif sport_key == 'icehockey_nhl':
            return nhl_template         
        elif sport_key in ['americanfootball_nfl', 'americanfootball_ncaaf', 'basketball_nba', 'basketball_ncaab']:
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