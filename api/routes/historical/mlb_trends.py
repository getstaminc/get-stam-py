"""MLB trends API endpoints."""

import hashlib
from flask import Blueprint, request, jsonify
from cache import cache
from ...services.historical.mlb_trends_service import MLBTrendsService
from ...services.historical.trend_enrichment import enrich_game_trends
from ...services.auth_service import AuthService
from ...utils.auth_helpers import get_current_user_optional


mlb_trends_bp = Blueprint('mlb_trends', __name__)

FREE_MAX_MIN_TREND_LENGTH = 5
PRO_MAX_MIN_TREND_LENGTH = 10


def _effective_max_min_trend_length():
    """Max min-trend-length the requesting user is allowed, based on their plan."""
    user = get_current_user_optional()
    if AuthService.effective_plan(user) == 'pro':
        return PRO_MAX_MIN_TREND_LENGTH
    return FREE_MAX_MIN_TREND_LENGTH


def make_mlb_trends_cache_key(*args, **kwargs):
    """Create a custom cache key based on game IDs, enrich flag, and the CLAMPED min trend length.

    Must key on the clamped value, not the raw requested one — otherwise a free-tier
    request for minTrendLength=10 would populate the shared cache under key "...:m10"
    with clamped (limit-5) results, which would then be served to the next caller
    requesting m10, including a legitimate Pro user.
    """
    data = request.get_json() or {}
    games = data.get('games', [])

    game_ids = sorted([game.get('game_id') for game in games if game.get('game_id')])
    game_ids_hash = hashlib.md5('|'.join(game_ids).encode()).hexdigest()[:8]
    enrich_flag = 'e1' if data.get('enrich') else 'e0'
    requested_min_len = data.get('minTrendLength', data.get('min_trend_length', 3))
    effective_min_len = min(requested_min_len, _effective_max_min_trend_length())

    return f"mlb_trends:{game_ids_hash}:{enrich_flag}:m{effective_min_len}"


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
        min_trend_length = min(min_trend_length, _effective_max_min_trend_length())
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
