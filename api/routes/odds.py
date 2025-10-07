# Add cache import
from cache import cache

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv
from ..services.game_service import GameService

odds_bp = Blueprint('odds', __name__)

load_dotenv()
API_KEY = os.getenv("API_KEY")

@odds_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

# =============================================================================
# ODDS ENDPOINTS (External API Data)
# =============================================================================

@odds_bp.route('/api/odds/<sport_key>', methods=['GET'])
@cache.cached(timeout=120, query_string=True)
def get_odds_for_sport(sport_key):
    """Get all games with odds for a sport, optionally filtered by date"""
    current_date = request.args.get('date', None)
    
    result, error = GameService.get_games_for_date(sport_key, current_date)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(result)

@odds_bp.route('/api/odds/<sport_key>/<game_id>', methods=['GET'])
@cache.cached(timeout=120, query_string=True)
def get_single_game_odds(sport_key, game_id):
    """Get odds details for a single game by game_id"""
    result, error = GameService.get_single_game(sport_key, game_id)
    
    if error:
        if error == 'Game not found':
            return jsonify({'error': error}), 404
        return jsonify({'error': error}), 500
    
    return jsonify(result)
