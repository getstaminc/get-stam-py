"""MLB trends API endpoints."""

import hashlib
from flask import Blueprint, request, jsonify
from cache import cache
from ...services.historical.mlb_trends_service import MLBTrendsService
from ...services.historical.trend_enrichment import enrich_game_trends


mlb_trends_bp = Blueprint('mlb_trends', __name__)


def make_mlb_trends_cache_key(*args, **kwargs):
    """Create a custom cache key based on game IDs, enrich flag, and min trend length."""
    data = request.get_json() or {}
    games = data.get('games', [])

    game_ids = sorted([game.get('game_id') for game in games if game.get('game_id')])
    game_ids_hash = hashlib.md5('|'.join(game_ids).encode()).hexdigest()[:8]
    enrich_flag = 'e1' if data.get('enrich') else 'e0'
    min_len = data.get('minTrendLength', data.get('min_trend_length', 3))

    return f"mlb_trends:{game_ids_hash}:{enrich_flag}:m{min_len}"


@mlb_trends_bp.route('/api/historical/trends/mlb', methods=['POST'])
@cache.cached(timeout=3600, make_cache_key=make_mlb_trends_cache_key)
def analyze_mlb_trends():
    """Analyze MLB trends for the given games."""
    try:
        data = request.get_json()
        if not data or 'games' not in data:
            return jsonify({'error': 'Games data is required'}), 400

        games = data['games']
        limit = data.get('limit', 5)
        min_trend_length = data.get('minTrendLength', data.get('min_trend_length', 3))
        enrich = data.get('enrich', False)

        results, error = MLBTrendsService.analyze_multiple_games_trends(
            games, limit, min_trend_length
        )

        if error:
            return jsonify({'error': error}), 500

        if enrich and results:
            enrich_game_trends(results, 'mlb')

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
        print(f"Error in analyze_mlb_trends: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
