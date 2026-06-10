"""World Cup Historical Games API routes."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ...services.historical.worldcup_service import WorldcupService

load_dotenv()
API_KEY = os.getenv("API_KEY")

worldcup_historical_bp = Blueprint('worldcup_historical', __name__)


@worldcup_historical_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    if request.headers.get("X-API-KEY") != API_KEY:
        abort(401)


@worldcup_historical_bp.route('/api/historical/worldcup/teams/<team_name>/games', methods=['GET'])
def get_worldcup_team_games(team_name):
    """Get games for a specific World Cup team."""
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    venue = request.args.get('venue')

    games, error = WorldcupService.get_team_games(team_name, limit, start_date, end_date, venue)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'team': team_name,
        'sport': 'World Cup'
    })


@worldcup_historical_bp.route('/api/historical/worldcup/teams/<team1>/vs/<team2>', methods=['GET'])
def get_worldcup_head_to_head(team1, team2):
    """Get head-to-head games between two World Cup teams."""
    limit = request.args.get('limit', 10, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    venue = request.args.get('venue')
    team_perspective = request.args.get('team_perspective')

    games, error = WorldcupService.get_head_to_head_games(
        team1, team2, limit, start_date, end_date, venue, team_perspective
    )

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'team1': team1,
        'team2': team2,
        'sport': 'World Cup'
    })
