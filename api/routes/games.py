import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..services.game_service import GameService

load_dotenv()
API_KEY = os.getenv("API_KEY")

games_bp = Blueprint('games', __name__)

@games_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

@games_bp.route('/api/games/<sport_key>', methods=['GET'])
def get_sport_games(sport_key):
    """Get all games for a sport, optionally filtered by date"""
    current_date = request.args.get('date', None)
    
    result, error = GameService.get_games_for_date(sport_key, current_date)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(result)

@games_bp.route('/api/game/<sport_key>/<game_id>', methods=['GET'])
def get_single_game(sport_key, game_id):
    """Get details for a single game by game_id"""
    result, error = GameService.get_single_game(sport_key, game_id)
    
    if error:
        if error == 'Game not found':
            return jsonify({'error': error}), 404
        return jsonify({'error': error}), 500
    
    return jsonify(result)
