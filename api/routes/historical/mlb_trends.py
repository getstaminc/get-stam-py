"""MLB trends API endpoints."""

from flask import Blueprint, request, jsonify
from ...services.historical.mlb_trends_service import MLBTrendsService


mlb_trends_bp = Blueprint('mlb_trends', __name__)


@mlb_trends_bp.route('/api/historical/trends/mlb', methods=['POST'])
def analyze_mlb_trends():
    """Analyze MLB trends for the given games."""
    try:
        data = request.get_json()
        if not data or 'games' not in data:
            return jsonify({'error': 'Games data is required'}), 400
        
        games = data['games']
        limit = data.get('limit', 5)
        min_trend_length = data.get('min_trend_length', 3)
        
        # Analyze trends for all games
        results, error = MLBTrendsService.analyze_multiple_games_trends(
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
        print(f"Error in analyze_mlb_trends: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
