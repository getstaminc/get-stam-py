"""Soccer Historical Games API routes - Database data only."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ...services.historical.soccer_service import SoccerService

load_dotenv()
API_KEY = os.getenv("API_KEY")

soccer_historical_bp = Blueprint('soccer_historical', __name__)

@soccer_historical_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

# =============================================================================
# SOCCER HISTORICAL GAMES ENDPOINTS (Database Data)
# =============================================================================

@soccer_historical_bp.route('/api/historical/soccer/games', methods=['GET'])
def get_soccer_games():
    """Get soccer historical games from database."""
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    team = request.args.get('team')
    league = request.args.get('league')
    
    games, error = SoccerService.get_games(limit, start_date, end_date, team, league)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'sport': 'Soccer',
        'filters': {
            'limit': limit,
            'start_date': start_date,
            'end_date': end_date,
            'team': team,
            'league': league
        }
    })


@soccer_historical_bp.route('/api/historical/soccer/epl/games', methods=['GET'])
def get_epl_games():
    """Get EPL games specifically."""
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    team = request.args.get('team')
    
    games, error = SoccerService.get_games(limit, start_date, end_date, team, "EPL")
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'league': 'EPL',
        'sport': 'Soccer'
    })


@soccer_historical_bp.route('/api/historical/soccer/games/<int:game_id>', methods=['GET'])
def get_soccer_game_by_id(game_id):
    """Get a specific soccer game by ID."""
    game, error = SoccerService.get_game_by_id(game_id)
    
    if error:
        if "not found" in error.lower():
            return jsonify({'error': error}), 404
        return jsonify({'error': error}), 500
    
    return jsonify({'game': game, 'sport': 'Soccer'})


@soccer_historical_bp.route('/api/historical/soccer/teams/<team_name>/games', methods=['GET'])
def get_soccer_team_games(team_name):
    """Get games for a specific soccer team."""
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    league = request.args.get('league')
    
    games, error = SoccerService.get_team_games(team_name, limit, start_date, end_date, league)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'team': team_name,
        'sport': 'Soccer'
    })


@soccer_historical_bp.route('/api/historical/soccer/teams/<team1>/vs/<team2>', methods=['GET'])
def get_soccer_head_to_head(team1, team2):
    """Get head-to-head games between two soccer teams."""
    limit = request.args.get('limit', 10, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    league = request.args.get('league')
    
    games, error = SoccerService.get_head_to_head_games(team1, team2, limit, start_date, end_date, league)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'games': games,
        'count': len(games) if games else 0,
        'team1': team1,
        'team2': team2,
        'sport': 'Soccer'
    })


@soccer_historical_bp.route('/api/historical/soccer/leagues', methods=['GET'])
def get_soccer_leagues():
    """Get available soccer leagues."""
    leagues, error = SoccerService.get_leagues()
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'leagues': leagues,
        'count': len(leagues) if leagues else 0,
        'sport': 'Soccer'
    })
