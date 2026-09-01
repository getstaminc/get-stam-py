"""NCAAF trends API endpoints."""

from flask import Blueprint, request, jsonify
from cache import cache
from ...services.historical.ncaaf_trends_service import NCAAFTrendsService
from ...services.historical.trend_enrichment import enrich_game_trends


ncaaf_trends_bp = Blueprint('ncaaf_trends', __name__)


def make_ncaaf_trends_cache_key(*args, **kwargs):
    """Create a custom cache key based on game IDs, enrich flag, and min trend length."""
    data = request.get_json() or {}
    games = data.get('games', [])

    # Extract and sort game IDs for consistent cache key
    game_ids = [game.get('game_id') for game in games if game.get('game_id')]
    game_ids.sort()  # Sort to ensure consistent key regardless of game order

    # Create a shorter hash of the game IDs to keep cache key manageable
    import hashlib
    game_ids_str = '|'.join(game_ids)
    game_ids_hash = hashlib.md5(game_ids_str.encode()).hexdigest()[:8]  # First 8 chars
    enrich_flag = 'e1' if data.get('enrich') else 'e0'
    min_len = data.get('minTrendLength', data.get('min_trend_length', 3))

    return f"ncaaf_trends:{game_ids_hash}:{enrich_flag}:m{min_len}"


@ncaaf_trends_bp.route('/api/historical/trends/ncaaf', methods=['POST'])
@cache.cached(timeout=3600, make_cache_key=make_ncaaf_trends_cache_key)
def analyze_ncaaf_trends():
    """Analyze NCAAF trends for the given games with Flask-Caching decorator."""
    try:
        data = request.get_json()
        if not data or 'games' not in data:
            return jsonify({'error': 'Games data is required'}), 400
        
        games = data['games']
        limit = data.get('limit', 5)
        min_trend_length = data.get('minTrendLength', data.get('min_trend_length', 3))
        enrich = data.get('enrich', False)

        # Analyze trends for all games
        results, error = NCAAFTrendsService.analyze_multiple_games_trends(
            games, limit, min_trend_length
        )

        if error:
            return jsonify({'error': error}), 500

        if enrich and results:
            enrich_game_trends(results, 'ncaaf')

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
        print(f"Error in analyze_ncaaf_trends: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
