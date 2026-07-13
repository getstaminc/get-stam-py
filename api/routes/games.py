import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from cache import cache
from ..services.database_service import DatabaseService
from ..services.game_service import GameService
from ..utils.team_slugs import resolve_team_slug
from ..external_requests.odds_api import convert_sport_url_to_api_key

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

@games_bp.route('/api/games/resolve/<sport>/<away_slug>/<home_slug>/<date>', methods=['GET'])
@cache.cached(timeout=120, query_string=True)
def resolve_matchup(sport, away_slug, home_slug, date):
    """Resolve a matchup-page slug (sport + away/home team slugs + ET date, optional
    ?n=<occurrence> for doubleheaders) to a game identity, for the crawlable
    /game-details/<sport>/<slug> route. Tries live odds data first, falls back to the
    sport's historical DB table for aged-out games."""
    occurrence = request.args.get('n', 1, type=int)

    away_name = resolve_team_slug(sport, away_slug)
    home_name = resolve_team_slug(sport, home_slug)
    if not away_name or not home_name:
        return jsonify({'error': 'Unknown team slug for this sport'}), 404

    sport_key = convert_sport_url_to_api_key(sport)
    result, error = GameService.resolve_matchup(sport_key, away_name, home_name, date, occurrence)
    if error or not result:
        return jsonify({'error': error or 'Game not found'}), 404

    return jsonify(result)

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
