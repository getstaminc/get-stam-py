"""MLB player batter streak trends endpoint."""

import hashlib
from flask import Blueprint, request, jsonify
from cache import cache
from ...services.historical.mlb_player_trends_service import MLBPlayerTrendsService


bp = Blueprint('mlb_player_trends', __name__)


def _make_cache_key(*args, **kwargs):
    data = request.get_json() or {}
    team_names = sorted(data.get('team_names') or [])
    min_streak = data.get('min_streak', 5)
    raw = f"{'|'.join(team_names)}:{min_streak}"
    h = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"mlb_player_trends:{h}"


@bp.route('/api/historical/player-trends/mlb', methods=['POST'])
@cache.cached(timeout=3600, make_cache_key=_make_cache_key)
def mlb_player_trends():
    """Return active batter hit/HR/RBI streaks for MLB players."""
    try:
        data = request.get_json() or {}
        team_names = data.get('team_names') or None
        min_streak = int(data.get('min_streak', 5))

        service = MLBPlayerTrendsService()
        result = service.get_batter_streaks(team_names=team_names, min_streak=min_streak)

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        print(f"Error in mlb_player_trends: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
