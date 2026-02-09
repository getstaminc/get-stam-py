import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pytz
from datetime import datetime
# Add cache import
from cachetools import TTLCache, cached

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
engine = create_engine(DATABASE_URL)

# Use cachetools for Python function caching (not Flask route caching)
_player_props_cache = TTLCache(maxsize=1000, ttl=21600)  # 6 hours

@cached(cache=_player_props_cache)
def get_last_n_player_props(player_id, n=5):
    # Fields to include (all except odds_event_id, espn_event_id, odds_source, bookmaker)
    fields = [
        "id", "player_id", "normalized_name", "game_date",
        "odds_player_points", "odds_player_points_over_price", "odds_player_points_under_price",
        "odds_player_rebounds", "odds_player_rebounds_over_price", "odds_player_rebounds_under_price",
        "odds_player_assists", "odds_player_assists_over_price", "odds_player_assists_under_price",
        "odds_player_threes", "odds_player_threes_over_price", "odds_player_threes_under_price",
        "actual_player_points", "actual_player_rebounds", "actual_player_assists", "actual_player_threes",
        "actual_player_minutes", "actual_player_fg", "actual_player_ft", "actual_plus_minus",
        "player_team_name", "player_team_id", "opponent_team_name", "opponent_team_id",
        "created_at", "updated_at", "odds_home_team", "odds_away_team", "odds_home_team_id", "odds_away_team_id", "did_not_play"
    ]
    sql = f"""
        SELECT {', '.join(fields)}
        FROM nba_player_props
        WHERE player_id = :player_id
        ORDER BY game_date DESC, id DESC
        LIMIT :n
    """
    eastern = pytz.timezone('US/Eastern')
    with engine.connect() as conn:
        result = conn.execute(text(sql), {"player_id": player_id, "n": n})
        rows = []
        for row in result.fetchall():
            record = dict(row._mapping)
            # Convert game_date to Eastern Time and add short_game_date
            dt = None
            if record.get("game_date"):
                try:
                    # Try parsing as ISO or datetime string
                    dt = datetime.strptime(str(record["game_date"]), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    try:
                        dt = datetime.strptime(str(record["game_date"]), "%Y-%m-%d")
                    except Exception:
                        dt = None
                if dt:
                    dt_eastern = dt.replace(tzinfo=pytz.utc).astimezone(eastern)
                    record["short_game_date"] = dt_eastern.strftime("%m/%d/%y")
                else:
                    record["short_game_date"] = None
            else:
                record["short_game_date"] = None
            rows.append(record)
    return rows
from ..external_requests.player_props_api import get_player_props, combine_player_props
from ..external_requests.player_team_lookup import get_team_id_for_player
from ..external_requests.team_lookup import get_team_id_by_odds_api_team_name

def get_structured_player_props(event_id):
    try:
        event_data = get_player_props(event_id)
        # If the odds API returns a user-friendly error, pass it through
        if isinstance(event_data, dict) and event_data.get("error"):
            return None, event_data["error"]
        if not event_data:
            return None, 'No player props found for this event.'
        result = combine_player_props(event_data)

        home_team_name = result.get("home_team")
        away_team_name = result.get("away_team")
        home_team_id = get_team_id_by_odds_api_team_name(home_team_name)
        away_team_id = get_team_id_by_odds_api_team_name(away_team_name)

        home_players = {}
        away_players = {}
        for bookmaker in result.get("bookmakers", []):
            for player_name, player_markets in bookmaker.get("players", {}).items():
                try:
                    team_id, player_id = get_team_id_for_player(player_name)
                except Exception as e:
                    return None, f'Database error while resolving player/team: {str(e)}'
                player_markets["player_id"] = player_id
                # Add historical records
                if player_id:
                    try:
                        player_markets["historical"] = get_last_n_player_props(player_id, n=5)
                    except Exception as e:
                        player_markets["historical"] = []
                else:
                    player_markets["historical"] = []
                if team_id == home_team_id:
                    home_players[player_name] = player_markets
                elif team_id == away_team_id:
                    away_players[player_name] = player_markets

        # If no players found for both teams, return a not found error
        if not home_players and not away_players:
            return None, 'No player props found for this event.'

        response = {
            "commence_time": result.get("commence_time"),
            "home_team": {
                "name": home_team_name,
                "team_id": home_team_id,
                "players": home_players
            },
            "away_team": {
                "name": away_team_name,
                "team_id": away_team_id,
                "players": away_players
            },
            "bookmakers": result.get("bookmakers", [])
        }
        return response, None
    except Exception as e:
        return None, f'Internal error in player props service: {str(e)}'
