"""NFL Historical Games API routes - Database data only."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ...services.historical.nfl_service import NFLService

load_dotenv()
API_KEY = os.getenv("API_KEY")

nfl_historical_bp = Blueprint('nfl_historical', __name__)

@nfl_historical_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

# =============================================================================
# NFL HISTORICAL GAMES ENDPOINTS (Database Data)
# =============================================================================

@nfl_historical_bp.route('/api/historical/nfl/games', methods=['GET'])
def get_nfl_games():
    """Get NFL historical games from database."""
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    team = request.args.get('team')
    playoffs = request.args.get('playoffs', type=bool)
    
    games, error = NFLService.get_games(limit, start_date, end_date, team, playoffs)
    
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
        'sport': 'NFL'
    })


@nfl_historical_bp.route('/api/historical/nfl/teams/<int:team_id>/games', methods=['GET'])
def get_nfl_team_games_by_id(team_id):
    """Get games for a specific NFL team by ID."""
    limit = request.args.get('limit', 50, type=int)
    
    games, error = NFLService.get_team_games_by_id(team_id, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NFL',
        'team_id': team_id,
        'limit': limit
    })


@nfl_historical_bp.route('/api/historical/nfl/teams/<team_name>/games', methods=['GET'])
def get_nfl_team_games(team_name):
    """Get games for a specific NFL team by name."""
    limit = request.args.get('limit', 50, type=int)
    
    games, error = NFLService.get_team_games_by_name(team_name, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NFL',
        'team_name': team_name,
        'limit': limit
    })


@nfl_historical_bp.route('/api/historical/nfl/teams/<int:team_id>/vs/<int:opponent_id>', methods=['GET'])
def get_nfl_head_to_head_by_id(team_id, opponent_id):
    """Get head-to-head games between two NFL teams by ID."""
    limit = request.args.get('limit', 10, type=int)
    
    games, error = NFLService.get_head_to_head_games_by_id(team_id, opponent_id, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NFL',
        'team_id': team_id,
        'opponent_id': opponent_id,
        'limit': limit
    })


@nfl_historical_bp.route('/api/historical/nfl/teams/<home_team>/vs/<away_team>', methods=['GET'])
def get_nfl_head_to_head(home_team, away_team):
    """Get head-to-head games between two NFL teams by name."""
    limit = request.args.get('limit', 10, type=int)
    
    games, error = NFLService.get_head_to_head_games_by_name(home_team, away_team, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NFL',
        'home_team': home_team,
        'away_team': away_team,
        'limit': limit
    })
