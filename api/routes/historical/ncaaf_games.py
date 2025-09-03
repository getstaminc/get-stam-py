"""NCAAF Historical Games API routes - Database data only."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ...services.historical.ncaaf_service import NCAAFService

load_dotenv()
API_KEY = os.getenv("API_KEY")

ncaaf_historical_bp = Blueprint('ncaaf_historical', __name__)

@ncaaf_historical_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

# =============================================================================
# NCAAF HISTORICAL GAMES ENDPOINTS (Database Data)
# =============================================================================

@ncaaf_historical_bp.route('/api/historical/ncaaf/games', methods=['GET'])
def get_ncaaf_games():
    """Get NCAAF historical games from database."""
    limit = request.args.get('limit', 50, type=int)
    
    games, error = NCAAFService.get_games(limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAF',
        'limit': limit
    })


@ncaaf_historical_bp.route('/api/historical/ncaaf/teams/<int:team_id>/games', methods=['GET'])
def get_ncaaf_team_games_by_id(team_id):
    """Get games for a specific NCAAF team by ID."""
    limit = request.args.get('limit', 50, type=int)
    
    games, error = NCAAFService.get_team_games_by_id(team_id, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAF',
        'team_id': team_id,
        'limit': limit
    })


@ncaaf_historical_bp.route('/api/historical/ncaaf/teams/<team_name>/games', methods=['GET'])
def get_ncaaf_team_games(team_name):
    """Get games for a specific NCAAF team by name."""
    limit = request.args.get('limit', 50, type=int)
    
    games, error = NCAAFService.get_team_games_by_name(team_name, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAF',
        'team_name': team_name,
        'limit': limit
    })


@ncaaf_historical_bp.route('/api/historical/ncaaf/teams/<int:team_id>/vs/<int:opponent_id>', methods=['GET'])
def get_ncaaf_head_to_head_by_id(team_id, opponent_id):
    """Get head-to-head games between two NCAAF teams by ID."""
    limit = request.args.get('limit', 10, type=int)
    
    games, error = NCAAFService.get_head_to_head_games_by_id(team_id, opponent_id, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAF',
        'team_id': team_id,
        'opponent_id': opponent_id,
        'limit': limit
    })


@ncaaf_historical_bp.route('/api/historical/ncaaf/teams/<home_team>/vs/<away_team>', methods=['GET'])
def get_ncaaf_head_to_head(home_team, away_team):
    """Get head-to-head games between two NCAAF teams by name."""
    limit = request.args.get('limit', 10, type=int)
    
    games, error = NCAAFService.get_head_to_head_games_by_name(home_team, away_team, limit)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAF',
        'home_team': home_team,
        'away_team': away_team,
        'limit': limit
    })
