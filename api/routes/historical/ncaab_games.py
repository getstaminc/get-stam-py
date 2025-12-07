"""NCAAB Historical Games API routes - Database data only."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ...services.historical.ncaab_service import NCAABService

load_dotenv()
API_KEY = os.getenv("API_KEY")

ncaab_historical_bp = Blueprint('ncaab_historical', __name__)


@ncaab_historical_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)


# =============================================================================
# NCAAB HISTORICAL GAMES ENDPOINTS (Database Data)
# =============================================================================


@ncaab_historical_bp.route('/api/historical/ncaab/games', methods=['GET'])
def get_ncaab_games():
    """Get NCAAB historical games from database."""
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    team = request.args.get('team')

    games, error = NCAABService.get_games(limit, start_date, end_date, team)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'count': len(games) if games else 0,
        'filters': {
            'limit': limit,
            'start_date': start_date,
            'end_date': end_date,
            'team': team
        },
        'games': games,
        'sport': 'NCAAB'
    })


@ncaab_historical_bp.route('/api/historical/ncaab/teams/<int:team_id>/games', methods=['GET'])
def get_ncaab_team_games_by_id(team_id):
    """Get games for a specific NCAAB team by ID."""
    limit = request.args.get('limit', 50, type=int)

    games, error = NCAABService.get_team_games_by_id(team_id, limit)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAB',
        'team_id': team_id,
        'limit': limit
    })


@ncaab_historical_bp.route('/api/historical/ncaab/teams/<team_name>/games', methods=['GET'])
def get_ncaab_team_games(team_name):
    """Get games for a specific NCAAB team by name."""
    limit = request.args.get('limit', 50, type=int)
    venue = request.args.get('venue')  # 'home', 'away', or None for all games

    games, error = NCAABService.get_team_games_by_name(team_name, limit, venue)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAB',
        'team_name': team_name,
        'limit': limit
    })


@ncaab_historical_bp.route('/api/historical/ncaab/teams/<int:team_id>/vs/<int:opponent_id>', methods=['GET'])
def get_ncaab_head_to_head_by_id(team_id, opponent_id):
    """Get head-to-head games between two NCAAB teams by ID."""
    limit = request.args.get('limit', 10, type=int)

    games, error = NCAABService.get_head_to_head_games_by_id(team_id, opponent_id, limit)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAB',
        'team_id': team_id,
        'opponent_id': opponent_id,
        'limit': limit
    })


@ncaab_historical_bp.route('/api/historical/ncaab/teams/<home_team>/vs/<away_team>', methods=['GET'])
def get_ncaab_head_to_head(home_team, away_team):
    """Get head-to-head games between two NCAAB teams by name."""
    limit = request.args.get('limit', 10, type=int)
    venue = request.args.get('venue')  # 'home', 'away', or None for all games
    team_perspective = request.args.get('team_perspective')  # Which team's venue to consider

    games, error = NCAABService.get_head_to_head_games_by_name(home_team, away_team, limit, venue, team_perspective)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'NCAAB',
        'home_team': home_team,
        'away_team': away_team,
        'limit': limit
    })
