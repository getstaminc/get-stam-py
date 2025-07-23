import os
from flask import Blueprint, request, jsonify, abort
from datetime import datetime, timedelta, date
import pytz
from dateutil import parser
from ..external_requests.odds_api import get_odds_data
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")

games_bp = Blueprint('games', __name__)
eastern_tz = pytz.timezone('US/Eastern')

@games_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

def convert_to_eastern(dt):
    return dt.astimezone(eastern_tz)

def get_next_game_date_within_7_days(scores, selected_date_start):
    today = datetime.now(pytz.utc)
    eastern = pytz.timezone('US/Eastern')
    for score in scores:
        commence_time_str = score['commence_time']
        commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
        commence_date_eastern = commence_date.astimezone(eastern)
        if commence_date_eastern.date() > selected_date_start.date() and commence_date_eastern.date() <= (today + timedelta(days=7)).date():
            return commence_date_eastern.strftime('%Y-%m-%d')
    return None

@games_bp.route('/api/games/<sport_key>', methods=['GET'])
def get_sport_games(sport_key):
    current_date = request.args.get('date', None)
    selected_date_start = None
    if current_date:
        selected_date_start = eastern_tz.localize(datetime.strptime(current_date, '%Y-%m-%d'))

    scores, odds = get_odds_data(sport_key, selected_date_start)
    if scores is None or odds is None:
        return jsonify({'error': 'Error fetching odds data, route'}), 500

    filtered_scores = []
    if selected_date_start:
        for score in scores:
            commence_time_str = score['commence_time']
            commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
            if convert_to_eastern(commence_date).date() == selected_date_start.date():
                filtered_scores.append(score)
    else:
        filtered_scores = scores  # Return all games if no date

    next_game_date = None
    if selected_date_start and not filtered_scores:
        next_game_date = get_next_game_date_within_7_days(scores, selected_date_start)

    formatted_scores = []
    for match in filtered_scores:
        home_team = match.get('home_team', 'N/A')
        away_team = match.get('away_team', 'N/A')

        # Score: int if available, else None
        home_score = None
        away_score = None
        if match.get('scores'):
            try:
                home_score = int(match['scores'][0]['score'])
            except (KeyError, ValueError, TypeError):
                home_score = None
            try:
                away_score = int(match['scores'][1]['score'])
            except (KeyError, ValueError, TypeError):
                away_score = None

        match_odds = next((o for o in odds if o['id'] == match['id']), None)

        home_odds = {"h2h": None, "spread_point": None, "spread_price": None}
        away_odds = {"h2h": None, "spread_point": None, "spread_price": None}
        totals = {"over_point": None, "over_price": None, "under_point": None, "under_price": None}

        if match_odds:
            for bookmaker in match_odds['bookmakers']:
                for market in bookmaker['markets']:
                    market_key = market['key']
                    if market_key == "h2h":
                        for outcome in market['outcomes']:
                            price = int(outcome['price']) if 'price' in outcome else None
                            if outcome['name'] == home_team:
                                home_odds["h2h"] = price
                            elif outcome['name'] == away_team:
                                away_odds["h2h"] = price
                    elif market_key == "spreads":
                        for outcome in market['outcomes']:
                            point = float(outcome['point']) if 'point' in outcome else None
                            price = int(outcome['price']) if 'price' in outcome else None
                            if outcome['name'] == home_team:
                                home_odds["spread_point"] = point
                                home_odds["spread_price"] = price
                            elif outcome['name'] == away_team:
                                away_odds["spread_point"] = point
                                away_odds["spread_price"] = price
                    elif market_key == "totals":
                        for outcome in market['outcomes']:
                            point = float(outcome['point']) if 'point' in outcome else None
                            price = int(outcome['price']) if 'price' in outcome else None
                            if outcome['name'].lower() == "over":
                                totals["over_point"] = point
                                totals["over_price"] = price
                            elif outcome['name'].lower() == "under":
                                totals["under_point"] = point
                                totals["under_price"] = price

        # Build the dict in the desired order
        formatted_scores.append({
            "game_id": match['id'],
            "isToday": selected_date_start and selected_date_start.date() == date.today(),
            "totals": totals,
            "home": {
                "team": home_team,
                "score": home_score,
                "odds": home_odds
            },
            "away": {
                "team": away_team,
                "score": away_score,
                "odds": away_odds
            }
        })

    response = {
        'games': formatted_scores,
        'nextGameDate': next_game_date
    }
    return jsonify(response)