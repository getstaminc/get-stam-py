# Add cache import
from cache import cache

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv
from ..services.game_service import GameService
from ..services.player_props_service import (
    get_structured_player_props, 
    get_structured_player_props_venue, 
    get_structured_player_props_vs_opponent
)

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

# =============================================================================
# PLAYER PROPS ENDPOINTS
# =============================================================================

@odds_bp.route('/api/odds/nba/player-props/<event_id>', methods=['GET'])
@cache.cached(timeout=900, query_string=True)
def get_player_props_for_event(event_id):
    """Get player props for a specific NBA event/game by event_id"""
    try:
        limit = request.args.get('limit', 5, type=int)
        response, error = get_structured_player_props(event_id, limit)
        if error:
            if 'not found' in error.lower() or 'no player props' in error.lower():
                return jsonify({'error': error}), 404
            return jsonify({'error': error}), 500
        return jsonify(response)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@odds_bp.route('/api/odds/nba/player-props/<event_id>/home-games', methods=['GET'])
@cache.cached(timeout=900, query_string=True)
def get_home_player_props_home_games(event_id):
    """Get home team player props for their home games"""
    try:
        limit = request.args.get('limit', 5, type=int)
        response, error = get_structured_player_props_venue(event_id, 'home', limit)
        if error:
            if 'not found' in error.lower() or 'no player props' in error.lower():
                return jsonify({'error': error}), 404
            return jsonify({'error': error}), 500
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@odds_bp.route('/api/odds/nba/player-props/<event_id>/away-games', methods=['GET'])
@cache.cached(timeout=900, query_string=True)
def get_away_player_props_away_games(event_id):
    """Get away team player props for their away games"""
    try:
        limit = request.args.get('limit', 5, type=int)
        response, error = get_structured_player_props_venue(event_id, 'away', limit)
        if error:
            if 'not found' in error.lower() or 'no player props' in error.lower():
                return jsonify({'error': error}), 404
            return jsonify({'error': error}), 500
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@odds_bp.route('/api/odds/nba/player-props/<event_id>/home-vs-opponent', methods=['GET'])
@cache.cached(timeout=900, query_string=True)
def get_home_player_props_vs_opponent(event_id):
    """Get home team player props for home games against the away opponent"""
    try:
        limit = request.args.get('limit', 5, type=int)
        response, error = get_structured_player_props_vs_opponent(event_id, 'home', limit)
        if error:
            if 'not found' in error.lower() or 'no player props' in error.lower():
                return jsonify({'error': error}), 404
            return jsonify({'error': error}), 500
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@odds_bp.route('/api/odds/nba/player-props/<event_id>/away-vs-opponent', methods=['GET'])
@cache.cached(timeout=900, query_string=True)
def get_away_player_props_vs_opponent(event_id):
    """Get away team player props for away games against the home opponent"""
    try:
        limit = request.args.get('limit', 5, type=int)
        response, error = get_structured_player_props_vs_opponent(event_id, 'away', limit)
        if error:
            if 'not found' in error.lower() or 'no player props' in error.lower():
                return jsonify({'error': error}), 404
            return jsonify({'error': error}), 500
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
