import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..services.game_service import GameService
from ..services.database_service import DatabaseService

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

# =============================================================================
# ODDS ENDPOINTS (External API Data)
# =============================================================================

@games_bp.route('/api/odds/<sport_key>', methods=['GET'])
def get_odds_for_sport(sport_key):
    """Get all games with odds for a sport, optionally filtered by date"""
    current_date = request.args.get('date', None)
    
    result, error = GameService.get_games_for_date(sport_key, current_date)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(result)

@games_bp.route('/api/odds/<sport_key>/<game_id>', methods=['GET'])
def get_single_game_odds(sport_key, game_id):
    """Get odds details for a single game by game_id"""
    result, error = GameService.get_single_game(sport_key, game_id)
    
    if error:
        if error == 'Game not found':
            return jsonify({'error': error}), 404
        return jsonify({'error': error}), 500
    
    return jsonify(result)

# =============================================================================
# HISTORICAL GAMES ENDPOINTS (Database Data)
# =============================================================================

@games_bp.route('/api/games/<sport_key>', methods=['GET'])
def get_historical_games(sport_key):
    """Get historical games from database for a sport"""
    limit = request.args.get('limit', 50, type=int)  # Default to 50 games
    
    games, error = DatabaseService.get_historical_games(sport_key, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games),
        'sport': sport_key,
        'limit': limit
    })

@games_bp.route('/api/games/<sport_key>/<int:team_id>', methods=['GET'])
def get_team_games(sport_key, team_id):
    """Get historical games for a specific team"""
    limit = request.args.get('limit', 10, type=int)
    
    games, error = DatabaseService.get_team_games(sport_key, team_id, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games),
        'sport': sport_key,
        'team_id': team_id,
        'limit': limit
    })

@games_bp.route('/api/games/<sport_key>/team/<string:team_name>', methods=['GET'])
def get_team_games_by_name(sport_key, team_name):
    """Get historical games for a specific team by team name"""
    limit = request.args.get('limit', 10, type=int)
    
    games, error = DatabaseService.get_team_games_by_name(sport_key, team_name, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games),
        'sport': sport_key,
        'team_name': team_name,
        'limit': limit
    })

@games_bp.route('/api/games/<sport_key>/<int:team_id>/vs/<int:opponent_id>', methods=['GET'])
def get_head_to_head_games(sport_key, team_id, opponent_id):
    """Get head-to-head games between two teams"""
    limit = request.args.get('limit', 5, type=int)
    
    games, error = DatabaseService.get_head_to_head_games(sport_key, team_id, opponent_id, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games),
        'sport': sport_key,
        'team_id': team_id,
        'opponent_id': opponent_id,
        'limit': limit
    })

@games_bp.route('/api/games/<sport_key>/team/<string:home_team>/vs/<string:away_team>', methods=['GET'])
def get_head_to_head_games_by_name(sport_key, home_team, away_team):
    """Get head-to-head games between two teams by team names"""
    limit = request.args.get('limit', 5, type=int)
    
    games, error = DatabaseService.get_head_to_head_games_by_name(sport_key, home_team, away_team, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games),
        'sport': sport_key,
        'home_team': home_team,
        'away_team': away_team,
        'limit': limit
    })
