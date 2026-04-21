import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv
from cache import cache
from ..services.mlb_player_props_service import get_structured_mlb_player_props

mlb_props_bp = Blueprint('mlb_player_props', __name__)

load_dotenv()
API_KEY = os.getenv("API_KEY")


@mlb_props_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)


@mlb_props_bp.route('/api/odds/mlb/player-props/<event_id>', methods=['GET'])
@cache.cached(timeout=900, query_string=True)
def get_mlb_player_props_for_event(event_id):
    try:
        limit = request.args.get('limit', 5, type=int)
        response, error = get_structured_mlb_player_props(event_id, limit)
        if error:
            if 'not found' in error.lower() or 'no player props' in error.lower():
                return jsonify({'error': error}), 404
            return jsonify({'error': error}), 500
        return jsonify(response)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
