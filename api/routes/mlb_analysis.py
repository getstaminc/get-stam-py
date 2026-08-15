"""MLB game analysis API route — AI-written GET STAM analysis for a single matchup."""

import os
import hashlib
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..services.mlb_analysis_service import MLBAnalysisService
from cache import cache

load_dotenv()
API_KEY = os.getenv("API_KEY")

mlb_analysis_bp = Blueprint("mlb_analysis", __name__)


@mlb_analysis_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)


def make_mlb_analysis_cache_key(*args, **kwargs):
    """Cache key derived from the matchup and date, so repeat requests skip the Claude call."""
    data = request.get_json() or {}
    home_team = (data.get('home_team') or '').strip().lower()
    away_team = (data.get('away_team') or '').strip().lower()
    game_date = data.get('game_date') or ''
    key_str = f"{home_team}|{away_team}|{game_date}"
    key_hash = hashlib.md5(key_str.encode()).hexdigest()[:8]
    return f"mlb_analysis:{key_hash}"


@mlb_analysis_bp.route("/api/mlb/analysis", methods=["POST"])
@cache.cached(timeout=3600, make_cache_key=make_mlb_analysis_cache_key)
def get_mlb_analysis():
    data = request.get_json() or {}
    home_team = data.get('home_team')
    away_team = data.get('away_team')
    game_date = data.get('game_date')

    if not home_team or not away_team:
        return jsonify({'error': 'home_team and away_team are required'}), 400

    print(f"🚨 CACHE MISS: Generating MLB analysis for {away_team} @ {home_team}")

    result, error = MLBAnalysisService.generate_analysis(home_team, away_team, game_date)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({'success': True, 'data': result})
