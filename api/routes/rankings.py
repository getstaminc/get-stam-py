import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..external_requests.espn import get_nfl_rankings

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
def get_nfl_rankings_endpoint():
    """Get NFL team rankings for offense and defense"""
    return get_nfl_rankings()
