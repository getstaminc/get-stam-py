from flask import Flask, render_template, jsonify, request, render_template_string, Blueprint, redirect, url_for
from datetime import datetime, timedelta  # Import timedelta here
import pytz
from dateutil import parser
from odds_api import get_odds_data, get_sports
from historical_odds import get_sdql_data
from single_game_data import get_game_details
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent
from utils import convert_sport_key, mlb_totals, other_totals, convert_to_eastern, check_for_trends
from betting_guide import betting_guide
from flask_caching import Cache
import logging
import os
from dotenv import load_dotenv
from constants import EXCLUDED_SPORTS
from celery_config import celery
from tasks import show_trends_task  # Import the task from tasks module
import subprocess
import redis
from urllib.parse import urlparse, parse_qs
import ssl

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
port = 5000

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

# Define the Eastern timezone
eastern_tz = pytz.timezone('US/Eastern')

# Determine if caching should be enabled based on the environment
if os.getenv('FLASK_ENV') == 'development':
    cache = Cache(config={'CACHE_TYPE': 'null'})  # Disable caching in development
else:
    cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})  # Enable caching with 5-minute timeout
cache.init_app(app)


# Configure Redis using the Redis URL from environment variables
redis_url = os.getenv('REDIS_URL')
if not redis_url:
    raise ValueError("REDIS_URL environment variable is not set")

# Parse the Redis URL to extract the SSL parameters
url = urlparse(redis_url)
query_params = parse_qs(url.query)
ssl_cert_reqs = ssl.CERT_NONE if query_params.get('ssl_cert_reqs', [''])[0] == 'CERT_NONE' else ssl.CERT_REQUIRED

try:
    redis_client = redis.StrictRedis(
        host=url.hostname,
        port=url.port,
        password=url.password,
        ssl=True,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_keyfile=None,
        ssl_certfile=None,
        ssl_ca_certs=None,
        socket_timeout=5,  # Adjust as needed
        socket_connect_timeout=5  # Adjust as needed
    )
except Exception as e:
    raise ValueError(f"Error configuring Redis client: {e}")

# Endpoint to get cache key value
@app.route('/cache/<cache_key>')
def get_cache_value(cache_key):
    try:
        cache_value = redis_client.get(cache_key)
        if cache_value:
            cache_value = cache_value.decode('utf-8') if isinstance(cache_value, bytes) else cache_value
            return jsonify({cache_key: cache_value})
        else:
            return jsonify({'error': 'Cache key not found'}), 404
    except Exception as e:
        logging.error(f"Error fetching cache key {cache_key}: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500 

# app.py
from betting_guide import betting_guide  # Add this line

app.register_blueprint(betting_guide)  # Register the blueprint

def filter_scores_by_date(scores, selected_date_start):
    filtered_scores = []
    for score in scores:
        commence_time_str = score['commence_time']
        commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
        commence_date_eastern = convert_to_eastern(commence_date)

        if commence_date_eastern.date() == selected_date_start.date():
            filtered_scores.append(score)
    return filtered_scores

@app.route('/trends')
def show_trends():
    try:
        sport_key = request.args.get('sport_key')
        date = request.args.get('date')
        logging.info(f"Received request for sport_key: {sport_key}, date: {date}")

        if not sport_key or not date:
            return jsonify({'error': 'Missing sport_key or date'}), 400
        
        cache_key = f"trends:{sport_key}:{date}"
        cache_value = redis_client.get(cache_key)

        if cache_value:
            logger.info(f"Cache hit for key: {cache_key}")
            cache_value = cache_value.decode('utf-8') if isinstance(cache_value, bytes) else cache_value
            return jsonify(cache_value)
        else:
            logger.info(f"Cache miss for key: {cache_key}")
            # Proceed with fetching new data and setting the cache

        # Fetch the scores to determine the number of games
        selected_date_start = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=eastern_tz)
        scores, _ = get_odds_data(sport_key, selected_date_start)

        if scores is None:
            return jsonify({'error': 'Error fetching odds data'}), 500

        filtered_scores = filter_scores_by_date(scores, selected_date_start)
        task = show_trends_task.apply_async(args=[sport_key, date])
        return jsonify({'task_id': task.id, 'num_games': len(filtered_scores)}), 202
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return "Internal Server Error", 500

    # IF WE DELETE THIS SOME DAY, DELETE the /immediate_trends route
    # # If there are more than 5 games, use the background queue
    # if len(filtered_scores) > 5:
    #     task = show_trends_task.apply_async(args=[sport_key, date])
    #     return jsonify({'task_id': task.id}), 202
    # else:
    #     # Process trends immediately if there are 5 or fewer games
    #     return process_trends_immediately(sport_key, date)
    
@app.route('/immediate_trends')
def process_trends_immediately(sport_key, date):
    selected_date_start = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=eastern_tz)
    scores, odds = get_odds_data(sport_key, selected_date_start)
    if scores is None or odds is None:
        return jsonify({'error': 'Error fetching odds data'}), 500

    filtered_scores = filter_scores_by_date(scores, selected_date_start)

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
            'homeScore': home_score,
            'awayScore': away_score,
            'odds': odds_data,
            'game_id': match['id'],
        })

    # Filter the games to include only those with trends
    games_with_trends = [game for game in formatted_scores if check_for_trends(game, selected_date_start, sport_key)['trend_detected']]

    return jsonify({
        'result': games_with_trends,
        'sport_key': sport_key,
        'current_date': date
    })

@app.route('/status/<task_id>')
def task_status(task_id):
    task = show_trends_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'result': task.result
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)  # This will contain the exception raised
        }
    return jsonify(response)

# @celery.task(name='app.show_trends_task')
# def show_trends_task(sport_key, date):
#     # Example task implementation
#     selected_date_start = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=eastern_tz)
#     scores, odds = get_odds_data(sport_key, selected_date_start)
#     if scores is None or odds is None:
#         return {'error': 'Error fetching odds data'}

#     filtered_scores = []
#     for score in scores:
#         commence_time_str = score['commence_time']
#         commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
#         commence_date_eastern = convert_to_eastern(commence_date)

#         if commence_date_eastern.date() == selected_date_start.date():
#             filtered_scores.append(score)

#     formatted_scores = []
#     for match in filtered_scores:
#         home_team = match.get('home_team', 'N/A')
#         away_team = match.get('away_team', 'N/A')
#         home_score = match['scores' ][0]['score'] if match.get('scores') else 'N/A'
#         away_score = match['scores'][1]['score'] if match.get('scores') else 'N/A'

#         match_odds = next((odds_match for odds_match in odds if odds_match['id'] == match['id']), None)
#         odds_data = {'h2h': [], 'spreads': [], 'totals': []}

#         if match_odds:
#             for bookmaker in match_odds['bookmakers']:
#                 for market in bookmaker['markets']:
#                     market_key = market['key']
#                     for outcome in market['outcomes']:
#                         outcome_text = f"{outcome['name']}"
#                         if market_key in ['spreads', 'totals'] and 'point' in outcome:
#                             outcome_text += f": {outcome['point']}"
#                         if market_key == 'h2h':
#                             price = outcome['price']
#                             if price > 0:
#                                 outcome_text += f": +{price}"
#                             else:
#                                 outcome_text += f": {price}"
#                         else:
#                             price = outcome['price']
#                             if price > 0:
#                                 outcome_text += f" +{price}"
#                             else:
#                                 outcome_text += f" {price}"
#                         odds_data[market_key].append(outcome_text)

#         formatted_scores.append({
#             'homeTeam': home_team,
#             'awayTeam': away_team,
#             'homeScore': home_score,
#             'awayScore': away_score,
#             'odds': odds_data,
#             'game_id': match['id'],
#         })
    

#     # Filter the games to include only those with trends
#     games_with_trends = [game for game in formatted_scores if check_for_trends(game, selected_date_start, sport_key)['trend_detected']]

#     return {
#         'result': games_with_trends,
#         'sport_key': sport_key,
#         'current_date': date
#     }

# Route to fetch available sports
@app.route('/api/sports')
@cache.cached(timeout=3600, query_string=True)
def api_get_sports():
    sports = get_sports()
    if sports is not None:
        return jsonify(sports)
    else:
        return jsonify({'error': 'Internal Server Error'}), 500

#Route to clear the cache
@app.route('/clear-cache')
def clear_cache():
    cache.clear()
    logging.info("Cache cleared")
    return "Cache cleared", 200

def get_next_game_date_within_7_days(scores, selected_date_start):
    today = datetime.now(pytz.utc)
    eastern = pytz.timezone('US/Eastern')
    
    # Check if selected_date_start is greater than 7 days from today
    if selected_date_start.date() > (today + timedelta(days=7)).date():
        return False

    if not scores:
        return False

    for score in scores:
        commence_time_str = score['commence_time']
        commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
        commence_date_eastern = commence_date.astimezone(eastern)

        if commence_date_eastern.date() > today.date() and commence_date_eastern.date() > selected_date_start.date() and commence_date_eastern.date() <= (today + timedelta(days=7)).date():
            score['commence_date'] = commence_date_eastern.strftime('%Y-%m-%d')  # YYYY-MM-DD format
            score['pretty_date'] = commence_date_eastern.strftime('%m-%d-%Y')  # MM-DD-YYYY format
            return score
    
    return False

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
                            border: 1.5px solid #ddd;
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

            next_game_date = False
            if not filtered_scores:
                next_game_date = get_next_game_date_within_7_days(scores, selected_date_start)

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
                                    {% if sport_key not in excluded_sports %}
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
                                        {% if sport_key not in excluded_sports %}
                                            <td>
                                                <a href="/game/{{ match.game_id }}?sport_key={{ sport_key }}&date={{ current_date }}" class="view-details">View Details</a>
                                            </td>
                                        {% endif %}
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% elif next_game_date %}
                        <p class="center">No games on this date. The next game is on {{ next_game_date['pretty_date'] }}.</p>
                        <p class="center"><a href="javascript:void(0);" onclick="goToNextGame('{{ next_game_date['commence_date'] }}')" class="button center">Go to Next Game</a></p>
                    {% else %}
                        <p class="center">No games on this date</p>
                    {% endif %}
                </body>
                </html>
            """, result=formatted_scores, sport_key=sport_key, current_date=current_date, next_game_date=next_game_date, excluded_sports=EXCLUDED_SPORTS)

    except requests.exceptions.RequestException as e:
        print('Request error:', str(e))
        return jsonify({'error': 'Request Error'}), 500
    except Exception as e:
        print('Error fetching scores:', str(e))
        return jsonify({'error': 'Internal Server Error'}), 500


# @app.route('/trends')
# @cache.cached(timeout=3600, query_string=True)
# def show_trends():
#     sport_key = request.args.get('sport_key')
#     date = request.args.get('date')

#     if not sport_key or not date:
#         return jsonify({'error': 'Missing sport_key or date'}), 400

#     try:
#         selected_date_start = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=eastern_tz)
#         scores, odds = get_odds_data(sport_key, selected_date_start)
#         if scores is None or odds is None:
#             return jsonify({'error': 'Error fetching odds data'}), 500

#         filtered_scores = []
#         for score in scores:
#             commence_time_str = score['commence_time']
#             commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
#             commence_date_eastern = convert_to_eastern(commence_date)

#             if commence_date_eastern.date() == selected_date_start.date():
#                 filtered_scores.append(score)

#         next_game_date = False
#         if not filtered_scores:
#             next_game_date = get_next_game_date_within_7_days(scores, selected_date_start)

#         formatted_scores = []
#         for match in filtered_scores:
#             home_team = match.get('home_team', 'N/A')
#             away_team = match.get('away_team', 'N/A')
#             home_score = match['scores'][0]['score'] if match.get('scores') else 'N/A'
#             away_score = match['scores'][1]['score'] if match.get('scores') else 'N/A'

#             match_odds = next((odds_match for odds_match in odds if odds_match['id'] == match['id']), None)
#             odds_data = {'h2h': [], 'spreads': [], 'totals': []}

#             if match_odds:
#                 for bookmaker in match_odds['bookmakers']:
#                     for market in bookmaker['markets']:
#                         market_key = market['key']
#                         for outcome in market['outcomes']:
#                             outcome_text = f"{outcome['name']}"
#                             if market_key in ['spreads', 'totals'] and 'point' in outcome:
#                                 outcome_text += f": {outcome['point']}"
#                             if market_key == 'h2h':
#                                 price = outcome['price']
#                                 if price > 0:
#                                     outcome_text += f": +{price}"
#                                 else:
#                                     outcome_text += f": {price}"
#                             else:
#                                 price = outcome['price']
#                                 if price > 0:
#                                     outcome_text += f" +{price}"
#                                 else:
#                                     outcome_text += f" {price}"
#                             odds_data[market_key].append(outcome_text)

#             formatted_scores.append({
#                 'homeTeam': home_team,
#                 'awayTeam': away_team,
#                 'homeScore': away_score,
#                 'awayScore': home_score,
#                 'odds': odds_data,
#                 'game_id': match['id'],
#             })

#         # Filter the games to include only those with trends
#         games_with_trends = [game for game in formatted_scores if check_for_trends(game, selected_date_start, sport_key)['trend_detected']]

#         current_date = request.args.get('date', None)
#         if not current_date:
#             current_date = datetime.now(eastern_tz).strftime('%Y-%m-%d')

#         return render_template('trends_list.html', result=games_with_trends, sport_key=sport_key, current_date=current_date)
#     except Exception as e:
#         print('Error fetching games with trends:', str(e))
#         return jsonify({'error': 'Internal Server Error'}), 500
    
# def detect_trends(games, sport_key):
#     def is_winner(points, o_points):
#         if points is None or o_points is None:
#             return None
#         return points > o_points

#     def calculate_line_result(points, line, o_points):
#         if points is None or line is None or o_points is None:
#             return None, ''
#         if points + line > o_points:
#             return True, 'green-bg'
#         elif points + line < o_points:
#             return False, 'red-bg'
#         else:
#             return None, ''

#     def other_totals(points, o_points, total):
#         if points is None or o_points is None or total is None:
#             return None, ''
#         if points + o_points > total:
#             return True, 'green-bg'
#         elif points + o_points < total:
#             return False, 'red-bg'
#         else:
#             return None, ''

#     if sport_key == 'icehockey_nhl':
#         points_key = 'goals'
#     else:
#         points_key = 'points'

#     # Check for trends in the 'team' column
#     team_colors = []
#     for game in games:
#         result = is_winner(game[points_key], game[f'o:{points_key}'])
#         if result is not None:
#             color = 'green-bg' if result else 'red-bg'
#             team_colors.append(color)
#     if team_colors.count('green-bg') == 5 or team_colors.count('red-bg') == 5:
#         return True

#     # Check for trends in the 'points' column
#     points_colors = []
#     for game in games:
#         result = is_winner(game[points_key], game[f'o:{points_key}'])
#         if result is not None:
#             color = 'green-bg' if result else 'red-bg'
#             points_colors.append(color)
#     if points_colors.count('green-bg') == 5 or points_colors.count('red-bg') == 5:
#         return True

#     # Skip line trend check for NHL
#     if sport_key != 'icehockey_nhl':
#         # Check for trends in the 'line' column
#         line_colors = []
#         for game in games:
#             result, color = calculate_line_result(game[points_key], game['line'], game[f'o:{points_key}'])
#             if result is not None:
#                 line_colors.append(color)
#         if line_colors.count('green-bg') == 5 or line_colors.count('red-bg') == 5:
#             return True

#     # Check for trends in the 'total' column
#     total_colors = []
#     for game in games:
#         result, color = other_totals(game[points_key], game[f'o:{points_key}'], game['total'])
#         if result is not None:
#             total_colors.append(color)
#     if total_colors.count('green-bg') == 5 or total_colors.count('red-bg') == 5:
#         return True

#     return False

# Route to fetch and display details for a specific game
@app.route('/game/<game_id>')
@cache.cached(timeout=3600, query_string=True)
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
                            color: #354050;
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
                            border: 1.5px solid #ddd;
                        }

                        th, td {
                            padding: 4px;
                            text-align: left;                 
                        }

                        th {
                            background-color: #f2f2f2;
                        }

                        .green-bg {
                            background-color: #7ebe7e;
                            color: black;
                        }

                        .red-bg {
                            background-color: #e35a69;
                            color: black;
                        }

                        .grey-bg {
                            background-color: #c6c8ca;
                            color: black;
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

                        button:disabled {
                            background-color: #cccccc; /* Light grey background */
                            color: #666666; /* Dark grey text */
                            cursor: not-allowed; /* Change cursor to not-allowed */
                            opacity: 0.6; /* Reduce opacity */
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
                            <td>{{ game.oddsText.replace('\n', '<br>')|safe }}</td>
                        </tr>
                    </table>
                                              
                                               
                    
                    <h2>Last 5 Games - {{ game.homeTeam }}</h2>
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
                                        <td class="{{ total_class }}">
                                            {{ game['total'] }}
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                      </div>                        
                    {% else %}
                        <p class="center">No data available.</p>
                    {% endif %}
                    
                    <h2>Last 5 Games - {{ game.awayTeam }}</h2>
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
                                        <td class="{{ total_class }}">
                                            {{ game['total'] }}
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                      </div>                        
                    {% else %}
                        <p class="center">No data available.</p>
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
                                        <td class="{{ total_class }}">
                                            {{ game['total'] }}
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                       </div>                        
                    {% else %}
                        <p class="center">No data available.</p>
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
                            color: #354050;
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
                            border: 1.5px solid #ddd;
                        }

                        th, td {
                            padding: 4px;
                            text-align: left;                 
                        }

                        th {
                            background-color: #f2f2f2;
                        }

                        .green-bg {
                            background-color: #7ebe7e;
                            color: black;
                        }

                        .red-bg {
                            background-color: #e35a69;
                            color: black;
                        }

                        .grey-bg {
                            background-color: #c6c8ca;
                            color: black;
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
                                              
                        button:disabled {
                            background-color: #cccccc; /* Light grey background */
                            color: #666666; /* Dark grey text */
                            cursor: not-allowed; /* Change cursor to not-allowed */
                            opacity: 0.6; /* Reduce opacity */
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
                        <td>{{ game.oddsText.replace('\n', '<br>')|safe }}</td>
                    </tr>
                </table>
                <div><p>Hover over column titles for color meanings</p></div>
                <h2>Last 5 Games - {{ game.homeTeam }}</h2>
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
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No data available.</p>
                {% endif %}

                <h2>Last 5 Games - {{ game.awayTeam }}</h2>
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
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No data available.</p>
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
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No data available.</p>
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
                            color: #354050;
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
                            border: 1.5px solid #ddd;
                        }

                        th, td {
                            padding: 4px;
                            text-align: left;                 
                        }

                        th {
                            background-color: #f2f2f2;
                        }

                        .green-bg {
                            background-color: #7ebe7e;
                            color: black;
                        }

                        .red-bg {
                            background-color: #e35a69;
                            color: black;
                        }

                        .grey-bg {
                            background-color: #c6c8ca;
                            color: black;
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
                        
                        button:disabled {
                            background-color: #cccccc; /* Light grey background */
                            color: #666666; /* Dark grey text */
                            cursor: not-allowed; /* Change cursor to not-allowed */
                            opacity: 0.6; /* Reduce opacity */
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
                        <td>{{ game.oddsText.replace('\n', '<br>')|safe }}</td>
                    </tr>
                </table>

                <h2>Last 5 Games - {{ game.homeTeam }}</h2>
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
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No data available.</p>
                {% endif %}

                <h2>Last 5 Games - {{ game.awayTeam }}</h2>
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
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No data available.</p>
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
                                                    <table>can I
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
                                    <td class="{{ total_class }}">
                                        {{ game['total'] }}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="center">No data available.</p>
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
@cache.cached(timeout=3600, query_string=True)
def home():
    return render_template('index.html', excluded_sports=EXCLUDED_SPORTS)

if __name__ == '__main__':
    # Start the Celery worker in a subprocess
    celery_process = subprocess.Popen(["celery", "-A", "celery_config", "worker", "--loglevel=info"])

    # Start the Flask application
    app.run(port=port)

    # Ensure the Celery worker is terminated when the Flask app exits
    celery_process.terminate()
