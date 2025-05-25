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
from shared_utils import convert_roto_team_names
from mlb_pitchers import get_starting_pitchers

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
        ssl_cert_reqs=ssl.CERT_NONE,
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
    games_with_trends = []
    for game in formatted_scores:
        trends = check_for_trends(game, selected_date_start, sport_key)
        game['trends'] = trends['trends']
        if trends['trend_detected']:
            games_with_trends.append(game)
    return games_with_trends

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

    # Load pitcher data (similar to app.py)
    pitchers_data = {}
    if sport_key == 'baseball_mlb':
        try:
            json_path = "mlb_starting_pitchers.json"
            scrape_today = True
            data = []

            # Check if file exists and is valid JSON with today’s data
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r") as f:
                        raw = f.read()
                        if not raw.strip():
                            raise ValueError("Empty file")
                        data = json.loads(raw)
                        if data and data[0].get("date") == datetime.today().strftime("%Y-%m-%d"):
                            scrape_today = False
                except Exception as e:
                    print("Pitcher data file invalid or empty, will attempt to re-scrape:", e)

            # Scrape fresh data if needed
            if scrape_today:
                get_starting_pitchers()  # Will overwrite the file with new data

                # Reload the file after scraping
                with open(json_path, "r") as f:
                    raw = f.read()
                    if not raw.strip():
                        raise ValueError("Scraped file is empty")
                    data = json.loads(raw)

            # Build pitchers_data from parsed JSON
            for game in data:
                key = f"{game['away_team']}@{game['home_team']}"
                pitchers_data[key] = game

        except Exception as e:
            print("Error handling pitcher data:", e)

    # Process scores and add pitcher data
    formatted_scores = []
    for match in filtered_scores:
        home_team = match.get('home_team', 'N/A')
        away_team = match.get('away_team', 'N/A')
        home_score = match['scores'][0]['score'] if match.get('scores') else 'N/A'
        away_score = match['scores'][1]['score'] if match.get('scores') else 'N/A'

        # 🔑 Only MLB: lookup pitcher info
        home_pitcher = away_pitcher = home_pitcher_stats = away_pitcher_stats = ''
        if sport_key == 'baseball_mlb':
            home_abbr = convert_roto_team_names(home_team)
            away_abbr = convert_roto_team_names(away_team)
            key = f"{away_abbr}@{home_abbr}"
            pitcher_info = pitchers_data.get(key, {})
            away_pitcher = pitcher_info.get('away_pitcher', '')
            away_pitcher_stats = pitcher_info.get('away_pitcher_stats', '')
            home_pitcher = pitcher_info.get('home_pitcher', '')
            home_pitcher_stats = pitcher_info.get('home_pitcher_stats', '')

        # Add odds data (reuse existing logic)
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

        # Append to formatted_scores with pitcher data
        formatted_scores.append({
            'homeTeam': home_team,
            'awayTeam': away_team,
            'homeScore': home_score,
            'awayScore': away_score,
            'odds': odds_data,
            'game_id': match['id'],
            'homePitcher': home_pitcher,
            'homePitcherStats': home_pitcher_stats,
            'awayPitcher': away_pitcher,
            'awayPitcherStats': away_pitcher_stats,
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