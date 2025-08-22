import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..external_requests.espn import get_nfl_rankings, get_ncaaf_rankings
from cache import cache

load_dotenv()
API_KEY = os.getenv("API_KEY")

rankings_bp = Blueprint('rankings', __name__)

@rankings_bp.before_request
def check_api_key():
    # Allow preflight OPTIONS requests for CORS
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)

# =============================================================================
# NFL RANKINGS ENDPOINT
# =============================================================================

@rankings_bp.route('/api/rankings/nfl', methods=['GET'])
@cache.cached(timeout=14400)  # Cache for 4 hours (14400 seconds)
def get_nfl_rankings_endpoint():
    """Get NFL team rankings for offense and defense"""
    return get_nfl_rankings()

# =============================================================================
# NCAAF RANKINGS ENDPOINT
# =============================================================================

@rankings_bp.route('/api/rankings/ncaaf', methods=['GET'])
@cache.cached(timeout=14400)  # Cache for 4 hours (14400 seconds)
def get_ncaaf_rankings_endpoint():
    """Get NCAAF team rankings for offense and defense"""
    return get_ncaaf_rankings()
