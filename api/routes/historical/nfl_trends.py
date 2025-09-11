"""NFL Trends API routes - Generate game trends from historical NFL data."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ...services.historical.nfl_trends_service import NFLTrendsService

load_dotenv()
API_KEY = os.getenv("API_KEY")

nfl_trends_bp = Blueprint('nfl_trends', __name__)

@nfl_trends_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

# =============================================================================
# NFL TRENDS ENDPOINTS
# =============================================================================

@nfl_trends_bp.route('/api/historical/trends/nfl', methods=['POST'])
def analyze_nfl_games_trends():
    """
    Analyze trends for multiple NFL games based on historical data.
    
    Expected request body:
    {
        "games": [...],  # Array of game objects
        "minTrendLength": 3,  # Minimum streak length (optional, default 3)
        "limit": 5  # Number of historical games to analyze (optional, default 5)
    }
    
    Returns:
    Array of games with trend analysis including:
    - game: Original game object
    - homeTeamTrends: Array of trend objects for home team
    - awayTeamTrends: Array of trend objects for away team  
    - headToHeadTrends: Array of trend objects for head-to-head matchups
    - hasTrends: Boolean indicating if any trends were found
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
            
        games = data.get('games', [])
        min_trend_length = data.get('minTrendLength', 3)
        limit = data.get('limit', 5)
        
        if not games:
            return jsonify({'error': 'games array is required'}), 400
            
        # Analyze trends for all NFL games
        result, error = NFLTrendsService.analyze_multiple_games_trends(
            games, limit, min_trend_length
        )
        
        if error:
            return jsonify({'error': error}), 500
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@nfl_trends_bp.route('/api/historical/trends/nfl/single', methods=['POST'])
def analyze_single_nfl_game_trends():
    """
    Analyze trends for a single NFL game based on historical data.
    
    Expected request body:
    {
        "game": {...},  # Single game object
        "minTrendLength": 3,  # Minimum streak length (optional, default 3)
        "limit": 5  # Number of historical games to analyze (optional, default 5)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
            
        game = data.get('game')
        min_trend_length = data.get('minTrendLength', 3)
        limit = data.get('limit', 5)
        
        if not game:
            return jsonify({'error': 'game object is required'}), 400
            
        # Analyze trends for single NFL game
        result, error = NFLTrendsService.analyze_game_trends(
            game, limit, min_trend_length
        )
        
        if error:
            return jsonify({'error': error}), 500
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
