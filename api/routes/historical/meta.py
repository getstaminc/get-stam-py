"""Historical data metadata endpoint — returns the earliest year of data for a sport."""

import os
from flask import Blueprint, jsonify, request, abort
from dotenv import load_dotenv
from cache import cache
from api.services.database_service import DatabaseService

load_dotenv()
API_KEY = os.getenv("API_KEY")

historical_meta_bp = Blueprint('historical_meta', __name__)

VALID_SPORTS = {'mlb', 'nba', 'nfl', 'nhl', 'ncaaf', 'ncaab', 'soccer', 'worldcup'}

@historical_meta_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

@historical_meta_bp.route('/api/historical/<sport>/meta', methods=['GET'])
@cache.cached(timeout=86400)  # 24 hours — data barely changes
def get_sport_meta(sport):
    """Return the earliest year of data we have for a sport."""
    if sport not in VALID_SPORTS:
        return jsonify({'error': f'Unknown sport: {sport}'}), 404

    table = f"{sport}_games"
    conn = DatabaseService._get_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT EXTRACT(YEAR FROM MIN(game_date)) FROM {table}")
            row = cur.fetchone()
            year = int(row[0]) if row and row[0] else None
        return jsonify({'data_since_year': year})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
