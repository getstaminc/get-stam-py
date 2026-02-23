import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import pytz
from datetime import datetime
import time
import logging
# Add cache import
from cachetools import TTLCache, cached

# Add missing imports
from ..external_requests.player_props_api import get_player_props, combine_player_props
from ..external_requests.player_team_lookup import get_team_id_for_player
from ..external_requests.team_lookup import get_team_id_by_odds_api_team_name

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

# Create engine with connection pooling and proper settings
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    connect_args={
        "connect_timeout": 10,
        "application_name": "player_props_service"
    }
)

# Use cachetools for Python function caching (not Flask route caching)
_player_props_cache = TTLCache(maxsize=1000, ttl=21600)  # 6 hours

def execute_with_retry(sql, params, max_retries=3):
    """Execute SQL with connection retry logic"""
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), params)
                return result.fetchall()
        except Exception as e:
            logging.error(f"Database error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(0.5 * (attempt + 1))  # Exponential backoff
    return []

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
    
    try:
        result_rows = execute_with_retry(sql, {"player_id": player_id, "n": n})
        rows = []
        for row in result_rows:
            record = dict(row._mapping)
            # Convert game_date to MM/DD/YY format
            if record.get("game_date"):
                try:
                    dt = datetime.strptime(str(record["game_date"]), "%a, %d %b %Y %H:%M:%S %Z")
                    record["short_game_date"] = dt.strftime("%m/%d/%y")
                except Exception:
                    try:
                        dt = datetime.strptime(str(record["game_date"]), "%Y-%m-%d %H:%M:%S")
                        record["short_game_date"] = dt.strftime("%m/%d/%y")
                    except Exception:
                        try:
                            dt = datetime.strptime(str(record["game_date"]), "%Y-%m-%d")
                            record["short_game_date"] = dt.strftime("%m/%d/%y")
                        except Exception:
                            record["short_game_date"] = None
            else:
                record["short_game_date"] = None
            rows.append(record)
        return rows
    except Exception as e:
        logging.error(f"Error in get_last_n_player_props for player {player_id}: {str(e)}")
        return []

@cached(cache=_player_props_cache)
def get_last_n_player_props_venue(player_id, venue_type, team_name, n=5):
    """Get last N games for player at specific venue (home/away)"""
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
    
    if venue_type == 'home':
        sql = f"""
            SELECT {', '.join(fields)}
            FROM nba_player_props
            WHERE player_id = :player_id AND odds_home_team = :team_name
            ORDER BY game_date DESC, id DESC
            LIMIT :n
        """
    else:  # away
        sql = f"""
            SELECT {', '.join(fields)}
            FROM nba_player_props
            WHERE player_id = :player_id AND odds_away_team = :team_name
            ORDER BY game_date DESC, id DESC
            LIMIT :n
        """
    
    try:
        result_rows = execute_with_retry(sql, {"player_id": player_id, "team_name": team_name, "n": n})
        rows = []
        for row in result_rows:
            record = dict(row._mapping)
            # Convert game_date to MM/DD/YY format
            if record.get("game_date"):
                try:
                    dt = datetime.strptime(str(record["game_date"]), "%a, %d %b %Y %H:%M:%S %Z")
                    record["short_game_date"] = dt.strftime("%m/%d/%y")
                except Exception:
                    try:
                        dt = datetime.strptime(str(record["game_date"]), "%Y-%m-%d %H:%M:%S")
                        record["short_game_date"] = dt.strftime("%m/%d/%y")
                    except Exception:
                        try:
                            dt = datetime.strptime(str(record["game_date"]), "%Y-%m-%d")
                            record["short_game_date"] = dt.strftime("%m/%d/%y")
                        except Exception:
                            record["short_game_date"] = None
            else:
                record["short_game_date"] = None
            rows.append(record)
        return rows
    except Exception as e:
        logging.error(f"Error in get_last_n_player_props_venue for player {player_id}: {str(e)}")
        return []

@cached(cache=_player_props_cache)
def get_last_n_player_props_vs_opponent(player_id, venue_type, team_name, opponent_name, n=5):
    """Get last N games for player at venue against specific opponent"""
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
    
    if venue_type == 'home':
        sql = f"""
            SELECT {', '.join(fields)}
            FROM nba_player_props
            WHERE player_id = :player_id 
            AND odds_home_team = :team_name 
            AND odds_away_team = :opponent_name
            ORDER BY game_date DESC, id DESC
            LIMIT :n
        """
    else:  # away
        sql = f"""
            SELECT {', '.join(fields)}
            FROM nba_player_props
            WHERE player_id = :player_id 
            AND odds_away_team = :team_name 
            AND odds_home_team = :opponent_name
            ORDER BY game_date DESC, id DESC
            LIMIT :n
        """
    
    try:
        result_rows = execute_with_retry(sql, {"player_id": player_id, "team_name": team_name, "opponent_name": opponent_name, "n": n})
        rows = []
        for row in result_rows:
            record = dict(row._mapping)
            # Convert game_date to MM/DD/YY format
            if record.get("game_date"):
                try:
                    dt = datetime.strptime(str(record["game_date"]), "%a, %d %b %Y %H:%M:%S %Z")
                    record["short_game_date"] = dt.strftime("%m/%d/%y")
                except Exception:
                    try:
                        dt = datetime.strptime(str(record["game_date"]), "%Y-%m-%d %H:%M:%S")
                        record["short_game_date"] = dt.strftime("%m/%d/%y")
                    except Exception:
                        try:
                            dt = datetime.strptime(str(record["game_date"]), "%Y-%m-%d")
                            record["short_game_date"] = dt.strftime("%m/%d/%y")
                        except Exception:
                            record["short_game_date"] = None
            else:
                record["short_game_date"] = None
            rows.append(record)
        return rows
    except Exception as e:
        logging.error(f"Error in get_last_n_player_props_vs_opponent for player {player_id}: {str(e)}")
        return []

def get_structured_player_props(event_id, limit=5):
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
        
        try:
            home_team_id = get_team_id_by_odds_api_team_name(home_team_name)
            away_team_id = get_team_id_by_odds_api_team_name(away_team_name)
        except Exception as e:
            logging.error(f"Error getting team IDs: {str(e)}")
            return None, f'Database error while resolving team IDs: {str(e)}'

        home_players = {}
        away_players = {}
        for bookmaker in result.get("bookmakers", []):
            for player_name, player_markets in bookmaker.get("players", {}).items():
                try:
                    team_id, player_id = get_team_id_for_player(player_name)
                except Exception as e:
                    logging.error(f"Error getting player/team for {player_name}: {str(e)}")
                    continue  # Skip this player instead of failing entire request
                
                player_markets["player_id"] = player_id
                if player_id:
                    try:
                        player_markets["historical"] = get_last_n_player_props(player_id, n=limit)
                    except Exception as e:
                        logging.error(f"Error getting historical data for player {player_id}: {str(e)}")
                        player_markets["historical"] = []
                else:
                    player_markets["historical"] = []
                    
                if team_id == home_team_id:
                    home_players[player_name] = player_markets
                elif team_id == away_team_id:
                    away_players[player_name] = player_markets

        if not home_players and not away_players:
            return None, 'No player props found for this event.'

        response = {
            "commence_time": result.get("commence_time"),
            "home_team": {
                "name": home_team_name,
                "team_id": home_team_id,
                "odds_name": home_team_name,
                "players": home_players
            },
            "away_team": {
                "name": away_team_name,
                "team_id": away_team_id,
                "odds_name": away_team_name,
                "players": away_players
            },
            "bookmakers": result.get("bookmakers", [])
        }
        return response, None
    except Exception as e:
        logging.error(f"Error in get_structured_player_props: {str(e)}")
        return None, f'Internal error in player props service: {str(e)}'

def get_structured_player_props_venue(event_id, venue_type, limit=5):
    """Get structured player props for venue-specific games (home/away)"""
    try:
        event_data = get_player_props(event_id)
        if isinstance(event_data, dict) and event_data.get("error"):
            return None, event_data["error"]
        if not event_data:
            return None, 'No player props found for this event.'
        
        result = combine_player_props(event_data)
        home_team_name = result.get("home_team")
        away_team_name = result.get("away_team")
        home_team_id = get_team_id_by_odds_api_team_name(home_team_name)
        away_team_id = get_team_id_by_odds_api_team_name(away_team_name)

        target_players = {}
        target_team_name = home_team_name if venue_type == 'home' else away_team_name
        target_team_id = home_team_id if venue_type == 'home' else away_team_id

        for bookmaker in result.get("bookmakers", []):
            for player_name, player_markets in bookmaker.get("players", {}).items():
                try:
                    team_id, player_id = get_team_id_for_player(player_name)
                except Exception as e:
                    return None, f'Database error while resolving player/team: {str(e)}'
                
                if team_id == target_team_id:
                    player_markets["player_id"] = player_id
                    if player_id:
                        try:
                            player_markets["historical"] = get_last_n_player_props_venue(
                                player_id, venue_type, target_team_name, n=limit
                            )
                        except Exception as e:
                            player_markets["historical"] = []
                    else:
                        player_markets["historical"] = []
                    target_players[player_name] = player_markets

        if not target_players:
            return None, f'No {venue_type} player props found for this event.'

        return {"players": target_players}, None
    except Exception as e:
        return None, f'Internal error in venue player props service: {str(e)}'

def get_structured_player_props_vs_opponent(event_id, venue_type, limit=5):
    """Get structured player props for venue games against specific opponent"""
    try:
        event_data = get_player_props(event_id)
        if isinstance(event_data, dict) and event_data.get("error"):
            return None, event_data["error"]
        if not event_data:
            return None, 'No player props found for this event.'
        
        result = combine_player_props(event_data)
        home_team_name = result.get("home_team")
        away_team_name = result.get("away_team")
        home_team_id = get_team_id_by_odds_api_team_name(home_team_name)
        away_team_id = get_team_id_by_odds_api_team_name(away_team_name)

        target_players = {}
        target_team_name = home_team_name if venue_type == 'home' else away_team_name
        target_team_id = home_team_id if venue_type == 'home' else away_team_id
        opponent_team_name = away_team_name if venue_type == 'home' else home_team_name

        for bookmaker in result.get("bookmakers", []):
            for player_name, player_markets in bookmaker.get("players", {}).items():
                try:
                    team_id, player_id = get_team_id_for_player(player_name)
                except Exception as e:
                    return None, f'Database error while resolving player/team: {str(e)}'
                
                if team_id == target_team_id:
                    player_markets["player_id"] = player_id
                    if player_id:
                        try:
                            player_markets["historical"] = get_last_n_player_props_vs_opponent(
                                player_id, venue_type, target_team_name, opponent_team_name, n=limit
                            )
                        except Exception as e:
                            player_markets["historical"] = []
                    else:
                        player_markets["historical"] = []
                    target_players[player_name] = player_markets

        if not target_players:
            return None, f'No {venue_type} vs opponent player props found for this event.'

        return {"players": target_players}, None
    except Exception as e:
        return None, f'Internal error in vs opponent player props service: {str(e)}'
