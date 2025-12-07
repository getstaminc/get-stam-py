"""NHL Historical Games API routes - Database data only."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ...services.historical.nhl_service import NHLService

load_dotenv()
API_KEY = os.getenv("API_KEY")

nhl_historical_bp = Blueprint('nhl_historical', __name__)

@nhl_historical_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

# =============================================================================
# NHL HISTORICAL GAMES ENDPOINTS (Database Data)
# =============================================================================

@nhl_historical_bp.route('/api/historical/nhl/games', methods=['GET'])
def get_nhl_games():
    """Get NHL historical games from database."""
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    team = request.args.get('team')
    playoffs = request.args.get('playoffs', type=bool)
    
    games, error = NHLService.get_games(limit, start_date, end_date, team, playoffs)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'count': len(games) if games else 0,
        'filters': {
            'limit': limit,
            'start_date': start_date,
            'end_date': end_date,
            'team': team,
            'playoffs': playoffs
        },
        'games': games,
        'sport': 'NHL'
    })

@nhl_historical_bp.route('/api/historical/nhl/games/<int:game_id>', methods=['GET'])
def get_nhl_game_by_id(game_id):
    """Get a specific NHL game by ID."""
    game, error = NHLService.get_game_by_id(game_id)
    
    if error:
        if "not found" in error.lower():
            return jsonify({'error': error}), 404
        return jsonify({'error': error}), 500
    
    return jsonify({'game': game, 'sport': 'NHL'})

@nhl_historical_bp.route('/api/historical/nhl/teams/<team_name>/games', methods=['GET'])
def get_nhl_team_games(team_name):
    """Get games for a specific NHL team."""
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    playoffs = request.args.get('playoffs', type=bool)
    venue = request.args.get('venue')  # 'home', 'away', or None for all games
    
    games, error = NHLService.get_team_games(team_name, limit, start_date, end_date, playoffs, venue)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'team': team_name,
        'sport': 'NHL'
    })

@nhl_historical_bp.route('/api/historical/nhl/teams/<team1>/vs/<team2>', methods=['GET'])
def get_nhl_head_to_head(team1, team2):
    """Get head-to-head games between two NHL teams."""
    limit = request.args.get('limit', 10, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    venue = request.args.get('venue')  # 'home', 'away', or None for all games
    team_perspective = request.args.get('team_perspective')  # Which team's venue to consider
    
    games, error = NHLService.get_head_to_head_games(team1, team2, limit, start_date, end_date, venue, team_perspective)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'team1': team1,
        'team2': team2,
        'sport': 'NHL'
    })

@nhl_historical_bp.route('/api/historical/nhl/goalies', methods=['GET'])
def get_nhl_goalies():
    """Get unique NHL goalies from historical games."""
    goalies, error = NHLService.get_goalies()
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'goalies': goalies,
        'count': len(goalies) if goalies else 0,
        'sport': 'NHL'
    })

# Register this blueprint in your app.py or main Flask app
# app.register_blueprint(nhl_historical_bp)
