import os
import redis
import json
from celery_app import celery
from odds_api import get_odds_data
from datetime import datetime
import pytz
from dateutil import parser
from utils import convert_to_eastern, check_for_trends
import logging
import ssl
from urllib.parse import urlparse, parse_qs
from retrying import retry

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

eastern_tz = pytz.timezone('US/Eastern')

@retry(stop_max_attempt_number=3, wait_fixed=2000)
def get_redis_cache(key):
    return redis_client.get(key)

@retry(stop_max_attempt_number=3, wait_fixed=2000)
def set_redis_cache(key, value, ttl):
    redis_client.setex(key, ttl, value)

def filter_games_with_trends(formatted_scores, selected_date_start, sport_key):
    return [game for game in formatted_scores if check_for_trends(game, selected_date_start, sport_key)['trend_detected']]

@celery.task
def show_trends_task(sport_key, date):
    cache_key = f"trends:{sport_key}:{date}"
    selected_date_start = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=eastern_tz)
    scores, odds = get_odds_data(sport_key, selected_date_start)
    if scores is None or odds is None:
        logger.error('Error fetching odds data')
        return {'error': 'Error fetching odds data'}

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
            'homeScore': home_score,
            'awayScore': away_score,
            'odds': odds_data,
            'game_id': match['id'],
        })

    # Use the function to filter games with trends
    games_with_trends = filter_games_with_trends(formatted_scores, selected_date_start, sport_key)
    logger.info(f"Games with trends: {games_with_trends}")
    result = {
        'result': games_with_trends,
        'sport_key': sport_key,
        'current_date': date,
    }

    # Cache the result for 6 hours (21600 seconds)
    try:
        logger.info("Setting cache")
        set_redis_cache(cache_key, json.dumps(result), 21600)
        logger.info(f"Cache set for key: {cache_key}")
    except Exception as e:
        logger.error(f"Error setting cache in Redis: {e}")

    return result