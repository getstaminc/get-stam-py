"""NCAAB trends API endpoints."""

from flask import Blueprint, request, jsonify
from cache import cache
from ...services.historical.ncaab_trends_service import NCAABTrendsService


ncaab_trends_bp = Blueprint('ncaab_trends', __name__)


def make_ncaab_trends_cache_key(*args, **kwargs):
    """Create a custom cache key based on game IDs only."""
    data = request.get_json() or {}
    games = data.get('games', [])
    
    # Extract and sort game IDs for consistent cache key
    game_ids = [game.get('game_id') for game in games if game.get('game_id')]
    game_ids.sort()
    
    import hashlib
    game_ids_str = '|'.join(game_ids)
    game_ids_hash = hashlib.md5(game_ids_str.encode()).hexdigest()[:8]
    return f"ncaab_trends:{game_ids_hash}"


@ncaab_trends_bp.route('/api/historical/trends/ncaab', methods=['POST'])
@cache.cached(timeout=3600, make_cache_key=make_ncaab_trends_cache_key)
def analyze_ncaab_trends():
    """Analyze NCAAB trends for the given games."""
    try:
        data = request.get_json()
        if not data or 'games' not in data:
            return jsonify({'error': 'Games data is required'}), 400
        
        games = data['games']
        limit = data.get('limit', 5)
        min_trend_length = data.get('min_trend_length', 3)
        
        results, error = NCAABTrendsService.analyze_multiple_games_trends(
            games, limit, min_trend_length
        )
        
        if error:
            return jsonify({'error': error}), 500
        
        return jsonify({
            'success': True,
            'data': results,
            'meta': {
                'games_analyzed': len(games),
                'limit': limit,
                'min_trend_length': min_trend_length
            }
        })
        
    except Exception as e:
        print(f"Error in analyze_ncaab_trends: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
