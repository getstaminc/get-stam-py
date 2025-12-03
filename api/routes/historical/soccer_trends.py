"""Soccer trends API endpoints."""

from flask import Blueprint, request, jsonify
from cache import cache
from ...services.historical.soccer_trends_service import SoccerTrendsService
from ...services.historical.soccer_service import SoccerService


soccer_trends_bp = Blueprint('soccer_trends', __name__)


def make_soccer_trends_cache_key(*args, **kwargs):
    """Create a custom cache key based on game IDs only."""
    data = request.get_json() or {}
    games = data.get('games', [])
    
    # Extract and sort game IDs for consistent cache key
    game_ids = [game.get('game_id') for game in games if game.get('game_id')]
    game_ids.sort()  # Sort to ensure consistent key regardless of game order
    
    # Create a shorter hash of the game IDs to keep cache key manageable
    import hashlib
    game_ids_str = '|'.join(game_ids)
    game_ids_hash = hashlib.md5(game_ids_str.encode()).hexdigest()[:8]  # First 8 chars
    
    return f"soccer_trends:{game_ids_hash}"


@soccer_trends_bp.route('/api/historical/trends/soccer', methods=['POST'])
@cache.cached(timeout=3600, make_cache_key=make_soccer_trends_cache_key)
def analyze_soccer_trends():
    """Analyze soccer trends for the given games."""
    try:
        data = request.get_json()
        if not data or 'games' not in data:
            return jsonify({'error': 'Games data is required'}), 400
        
        games = data['games']
        limit = data.get('limit', 5)
        # Support both min_trend_length and minTrendLength keys
        min_trend_length = data.get('min_trend_length', data.get('minTrendLength', 3))
        sport_key = data.get('sportKey')

        # Analyze trends for all games
        results, error = SoccerTrendsService.analyze_multiple_games_trends(
            games, limit, min_trend_length, sport_key
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
        print(f"Error in analyze_soccer_trends: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@soccer_trends_bp.route('/api/historical/soccer/<league_slug>/trends', methods=['GET'])
@soccer_trends_bp.route('/<league_slug>/trends', methods=['GET'])
def league_trends(league_slug: str):
    """GET endpoint to return trends for a league on a specific date.

    Example: /ligue1/trends?date=20251205 or /api/historical/soccer/ligue1/trends?date=2025-12-05
    """
    try:
        date_param = request.args.get('date')
        if not date_param:
            return jsonify({'error': 'date query parameter is required (YYYYMMDD or YYYY-MM-DD)'}), 400

        # parse date formats YYYYMMDD or YYYY-MM-DD
        if len(date_param) == 8 and date_param.isdigit():
            game_date = f"{date_param[0:4]}-{date_param[4:6]}-{date_param[6:8]}"
        else:
            # assume already YYYY-MM-DD
            game_date = date_param

        # league slug -> canonical league string used in DB
        slug_map = {
            'epl': 'EPL',
            'laliga': 'LA LIGA',
            'bundesliga': 'BUNDESLIGA',
            'ligue1': 'LIGUE 1',
            'seriea': 'SERIE A',
        }
        league = slug_map.get(league_slug.lower())
        if not league:
            return jsonify({'error': f'Unsupported league: {league_slug}'}), 400

        limit = int(request.args.get('limit', 50))
        min_trend_length = int(request.args.get('min_trend_length', request.args.get('minTrendLength', 3)))

        games, error = SoccerService.get_games(limit=limit, start_date=game_date, end_date=game_date, league=league)
        if error:
            return jsonify({'error': error}), 500

        # SoccerTrendsService expects a list of game dicts (it accepts home_team_name / away_team_name)
        results, svc_error = SoccerTrendsService.analyze_multiple_games_trends(games or [], limit=5, min_trend_length=min_trend_length, sport_key=None)
        if svc_error:
            return jsonify({'error': svc_error}), 500

        return jsonify({'success': True, 'data': results, 'meta': {'league': league, 'date': game_date, 'games_analyzed': len(games or [])}})

    except Exception as e:
        print(f"Error in league_trends: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@soccer_trends_bp.route('/api/historical/trends/soccer/<league_slug>', methods=['POST'])
def analyze_soccer_trends_by_league(league_slug: str):
    """Analyze soccer trends for a specific league.

    Accepts the same POST payload as /api/historical/trends/soccer (with 'games') OR a 'date' to fetch
    all games for that league on the given date.
    """
    try:
        data = request.get_json() or {}
        games = data.get('games')
        limit = data.get('limit', 5)
        min_trend_length = data.get('min_trend_length', data.get('minTrendLength', 3))

        # Map league slug to DB league name and optional sport_key the trends service understands
        slug_to_db_league = {
            'epl': 'EPL',
            'laliga': 'LA LIGA',
            'bundesliga': 'BUNDESLIGA',
            'ligue1': 'LIGUE 1',
            'seriea': 'SERIE A',
        }
        slug_to_sport_key = {
            'epl': 'soccer_epl',
            'laliga': 'soccer_spain_la_liga',
            'bundesliga': 'soccer_germany_bundesliga',
            'ligue1': 'soccer_france_ligue_one',
            'seriea': 'soccer_italy_serie_a',
        }

        league_db = slug_to_db_league.get(league_slug.lower())
        sport_key = slug_to_sport_key.get(league_slug.lower())
        if not league_db:
            return jsonify({'error': f'Unsupported league: {league_slug}'}), 400

        # If no games payload provided, require a date to fetch games for the league
        if not games:
            date_param = data.get('date') or request.args.get('date')
            if not date_param:
                return jsonify({'error': 'Either a games array in the POST body or a date (YYYYMMDD or YYYY-MM-DD) is required'}), 400

            if len(date_param) == 8 and date_param.isdigit():
                game_date = f"{date_param[0:4]}-{date_param[4:6]}-{date_param[6:8]}"
            else:
                game_date = date_param

            # Fetch games for that league/date
            games, err = SoccerService.get_games(limit=1000, start_date=game_date, end_date=game_date, league=league_db)
            if err:
                return jsonify({'error': err}), 500

        results, error = SoccerTrendsService.analyze_multiple_games_trends(
            games or [], limit, min_trend_length, sport_key
        )
        if error:
            return jsonify({'error': error}), 500

        return jsonify({
            'success': True,
            'data': results,
            'meta': {
                'league': league_db,
                'games_analyzed': len(games or []),
                'limit': limit,
                'min_trend_length': min_trend_length,
            }
        })

    except Exception as e:
        print(f"Error in analyze_soccer_trends_by_league: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
