from flask import Flask, render_template, jsonify, request, render_template_string, Blueprint, redirect, url_for
from datetime import datetime, timedelta  # Import timedelta here
import pytz
from dateutil import parser
from odds_api import get_odds_data, get_sports
from historical_odds import get_sdql_data
from single_game_data import get_game_details
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent
from utils import convert_sport_key, mlb_totals, other_totals, convert_to_eastern, check_for_trends, convert_team_name
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
import requests
from urllib.parse import urlparse, parse_qs
import ssl
import json
#from shared_utils import convert_roto_team_names
#from mlb_pitchers import get_starting_pitchers
from scores_templates import (
    historical_template,
    default_template,
    baseball_template,
    soccer_template
)
from game_details_templates import mlb_template, nhl_template, others_template

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
        ssl_cert_reqs=ssl.CERT_NONE,
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

        sdql_sport_key = convert_sport_key(sport_key)

        # Historical path
        if selected_date_start.date() < datetime.now(eastern_tz).date():
            sdql_data = get_sdql_data(sdql_sport_key, selected_date_start)
            return render_template_string(historical_template, result=sdql_data)

        # Live/future path
        scores, odds = get_odds_data(sport_key, selected_date_start)
        if scores is None or odds is None:
            return jsonify({'error': 'Error fetching odds data'}), 500

        filtered_scores = []
        for score in scores:
            commence_time_str = score['commence_time']
            commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
            if convert_to_eastern(commence_date).date() == selected_date_start.date():
                filtered_scores.append(score)

        next_game_date = False
        if not filtered_scores:
            next_game_date = get_next_game_date_within_7_days(scores, selected_date_start)

        # ✅ Load pitcher data ONCE if sport is MLB
        #pitchers_data = {}
        #if sport_key == 'baseball_mlb':
            #try:
                # Only scrape if JSON doesn't exist or isn't from today
                #json_path = "mlb_starting_pitchers.json"
                #scrape_today = True

                #if os.path.exists(json_path):
                    #with open(json_path, "r") as f:
                        #data = json.load(f)
                        #if data and data[0].get("date") == datetime.today().strftime("%Y-%m-%d"):
                            #scrape_today = False

                #if scrape_today:
                    #get_starting_pitchers()  # Will update JSON

                # Load pitcher data from JSON
               # with open(json_path, "r") as f:
                    #for game in json.load(f):
                       # key = f"{game['away_team']}@{game['home_team']}"
                       # pitchers_data[key] = game

            #except Exception as e:
               # print("Error handling pitcher data:", e)

        formatted_scores = []
        for match in filtered_scores:
            home_team = match.get('home_team', 'N/A')
            away_team = match.get('away_team', 'N/A')
            home_score = match['scores'][0]['score'] if match.get('scores') else 'N/A'
            away_score = match['scores'][1]['score'] if match.get('scores') else 'N/A'

            # 🔑 Only MLB: lookup pitcher info
            #home_pitcher = away_pitcher = home_pitcher_stats = away_pitcher_stats = ''
            #if sport_key == 'baseball_mlb':
                #home_abbr = convert_roto_team_names(home_team)
                #away_abbr = convert_roto_team_names(away_team)
                #key = f"{away_abbr}@{home_abbr}"
                #pitcher_info = pitchers_data.get(key, {})
                #away_pitcher = pitcher_info.get('away_pitcher', '')
                #away_pitcher_stats = pitcher_info.get('away_pitcher_stats', '')
                #home_pitcher = pitcher_info.get('home_pitcher', '')
                #home_pitcher_stats = pitcher_info.get('home_pitcher_stats', '')

            # Odds
            match_odds = next((o for o in odds if o['id'] == match['id']), None)
            odds_data = {'h2h': [], 'spreads': [], 'totals': []}

            if match_odds:
                for bookmaker in match_odds['bookmakers']:
                    for market in bookmaker['markets']:
                        market_key = market['key']
                        for outcome in market['outcomes']:
                            outcome_text = f"{outcome['name']}"
                            price = outcome['price']
                            if price > 0:
                                outcome_text += f": +{price}"
                            else:
                                outcome_text += f": {price}"
                            if market_key in ['spreads', 'totals'] and 'point' in outcome:
                                outcome_text += f": {outcome['point']}"
                            if sport_key == 'soccer_epl' and market_key == 'h2h':
                                odds_data['h2h'].append(outcome_text)
                            elif sport_key == 'baseball_mlb':
                                if market_key in odds_data:
                                    odds_data[market_key].append(outcome_text)
                            else:
                                odds_data[market_key].append(outcome_text)

            formatted_scores.append({
                'homeTeam': home_team,
                'awayTeam': away_team,
                'homeScore': away_score,
                'awayScore': home_score,
                'odds': odds_data,
                'game_id': match['id'],
                #'homePitcher': home_pitcher,
                #'homePitcherStats': home_pitcher_stats,
                #'awayPitcher': away_pitcher,
                #'awayPitcherStats': away_pitcher_stats,
            })
            #if sport_key == 'baseball_mlb':
                #print(f"{away_team} @ {home_team}")
                #print(f"  Away Pitcher: {away_pitcher} ({away_pitcher_stats})")
                #print(f"  Home Pitcher: {home_pitcher} ({home_pitcher_stats})")

        template = baseball_template if sport_key == 'baseball_mlb' else (
            soccer_template if sport_key == 'soccer_epl' else default_template
        )

        return render_template_string(
            template,
            result=formatted_scores,
            sport_key=sport_key,
            current_date=current_date,
            next_game_date=next_game_date,
            excluded_sports=EXCLUDED_SPORTS
        )

    except requests.exceptions.RequestException as e:
        print('Request error:', e)
        return jsonify({'error': 'Request Error'}), 500
    except Exception as e:
        print('Error fetching scores:', e)
        return jsonify({'error': 'Internal Server Error'}), 500


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
            #print(f"Home Team Last 5: {home_team_last_5}")
            #print(f"Away Team Last 5: {away_team_last_5}")
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

        #pitchers_data = {}
        #try:
            #with open('mlb_starting_pitchers.json', 'r') as f:
                #for game in json.load(f):
                    #key = f"{game['away_team']}@{game['home_team']}"
                    #pitchers_data[key] = game
        #except Exception as e:
            #print("Error loading pitcher data:", e)

        #away_abbr = convert_roto_team_names(game_details["awayTeam"])
        #home_abbr = convert_roto_team_names(game_details["homeTeam"])

        #matchup_key = f"{away_abbr}@{home_abbr}"
        #pitchers = pitchers_data.get(matchup_key, {})
        #print(f"{away_abbr} @ {home_abbr} → Pitchers: {pitchers}")

        print(f"Redirecting to game_details for game_id: {game_id}")
       
        if sport_key == 'baseball_mlb':
            return render_template_string(mlb_template,
                                        game=game_details,
                                        home_team_last_5=home_team_last_5,
                                        away_team_last_5=away_team_last_5,
                                        last_5_vs_opponent=last_5_vs_opponent,
                                        mlb_totals=mlb_totals,
                                        mlb_winner=mlb_winner,
                                        calculate_line_result=calculate_line_result)
                                        #home_pitcher=pitchers.get('home_pitcher'),
                                        #home_stats=pitchers.get('home_pitcher_stats'),
                                        #away_pitcher=pitchers.get('away_pitcher'),
                                        #away_stats=pitchers.get('away_pitcher_stats'))
        elif sport_key == 'icehockey_nhl':
            return render_template_string(nhl_template,
                                        game=game_details,
                                        home_team_last_5=home_team_last_5,
                                        away_team_last_5=away_team_last_5,
                                        last_5_vs_opponent=last_5_vs_opponent,
                                        nhl_totals=nhl_totals,
                                        nhl_winner=nhl_winner,
                                        calculate_line_result=calculate_line_result)
        elif sport_key in ['americanfootball_nfl', 'americanfootball_ncaaf', 'basketball_nba', 'basketball_ncaab']:
            return render_template_string(others_template,
                                        game=game_details,
                                        home_team_last_5=home_team_last_5,
                                        away_team_last_5=away_team_last_5,
                                        last_5_vs_opponent=last_5_vs_opponent,
                                        other_totals=other_totals,
                                        other_winner=other_winner,
                                        calculate_line_result=calculate_line_result)
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

