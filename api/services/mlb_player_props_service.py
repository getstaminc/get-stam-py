import os
import logging
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from cachetools import TTLCache, cached

from ..external_requests.mlb_player_props_api import get_mlb_player_props, combine_mlb_player_props
from ..external_requests.team_lookup import get_mlb_team_id_by_odds_api_team_name
from utils.player_name_utils import normalize_name

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=1,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=900,
    pool_timeout=10,
    connect_args={
        "connect_timeout": 5,
        "application_name": "mlb_player_props_service"
    }
)

_mlb_props_cache = TTLCache(maxsize=1000, ttl=21600)  # 6 hours

BATTER_MARKETS = {
    "batter_hits", "batter_home_runs", "batter_rbis",
    "batter_runs_scored", "batter_total_bases"
}
PITCHER_MARKETS = {
    "pitcher_strikeouts", "pitcher_earned_runs",
    "pitcher_hits_allowed", "pitcher_walks"
}


def execute_with_retry(sql, params, max_retries=3):
    for attempt in range(max_retries):
        conn = None
        try:
            conn = engine.connect()
            result = conn.execute(text(sql), params)
            rows = result.fetchall()
            return rows
        except Exception as e:
            logging.error(f"MLB props DB error attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(0.5 * (attempt + 1))
        finally:
            if conn:
                conn.close()
    return []


def _format_date(record):
    if record.get("game_date"):
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(str(record["game_date"]), fmt)
                record["short_game_date"] = dt.strftime("%m/%d/%y")
                return record
            except Exception:
                continue
    record["short_game_date"] = None
    return record


def resolve_mlb_player(player_name):
    """Return (team_id, player_id) for an MLB player name, checking aliases first."""
    normalized = normalize_name(player_name)
    try:
        # Check aliases table first
        rows = execute_with_retry(
            "SELECT player_id FROM mlb_player_aliases WHERE normalized_name = :name",
            {"name": normalized}
        )
        if rows:
            player_id = rows[0][0]
        else:
            # Fallback to mlb_players
            rows = execute_with_retry(
                "SELECT id FROM mlb_players WHERE normalized_name = :name",
                {"name": normalized}
            )
            if not rows:
                return None, None
            player_id = rows[0][0]

        # Get team_id from mlb_players
        team_rows = execute_with_retry(
            "SELECT team_id FROM mlb_players WHERE id = :player_id",
            {"player_id": player_id}
        )
        team_id = team_rows[0][0] if team_rows else None
        return team_id, player_id
    except Exception as e:
        logging.error(f"Error resolving MLB player '{player_name}': {str(e)}")
        return None, None


@cached(cache=_mlb_props_cache)
def get_last_n_batter_props(player_id, n=5):
    # Each game has multiple rows (one per market), so GROUP BY game to aggregate all stats
    sql = """
        SELECT
            game_date,
            MAX(odds_batter_hits)          AS odds_batter_hits,
            MAX(odds_batter_home_runs)     AS odds_batter_home_runs,
            MAX(odds_batter_rbi)           AS odds_batter_rbi,
            MAX(actual_batter_hits)        AS actual_batter_hits,
            MAX(actual_batter_home_runs)   AS actual_batter_home_runs,
            MAX(actual_batter_rbi)         AS actual_batter_rbi,
            MAX(opponent_team_name)        AS opponent_team_name,
            MAX(player_team_name)          AS player_team_name
        FROM mlb_batter_props
        WHERE player_id = :player_id
        GROUP BY game_date, odds_event_id
        ORDER BY game_date DESC
        LIMIT :n
    """
    try:
        result_rows = execute_with_retry(sql, {"player_id": player_id, "n": n})
        rows = []
        for row in result_rows:
            record = dict(row._mapping)
            record = _format_date(record)
            rows.append(record)
        return rows
    except Exception as e:
        logging.error(f"Error in get_last_n_batter_props for player {player_id}: {str(e)}")
        return []


@cached(cache=_mlb_props_cache)
def get_last_n_pitcher_props(player_id, n=5):
    # Each game has multiple rows (one per market), so GROUP BY game to aggregate all stats
    sql = """
        SELECT
            game_date,
            MAX(odds_pitcher_strikeouts)   AS odds_pitcher_strikeouts,
            MAX(odds_pitcher_earned_runs)  AS odds_pitcher_earned_runs,
            MAX(odds_pitcher_hits_allowed) AS odds_pitcher_hits_allowed,
            MAX(actual_pitcher_strikeouts)   AS actual_pitcher_strikeouts,
            MAX(actual_pitcher_earned_runs)  AS actual_pitcher_earned_runs,
            MAX(actual_pitcher_hits_allowed) AS actual_pitcher_hits_allowed,
            MAX(opponent_team_name)        AS opponent_team_name,
            MAX(player_team_name)          AS player_team_name
        FROM mlb_pitcher_props
        WHERE player_id = :player_id
        GROUP BY game_date, odds_event_id
        ORDER BY game_date DESC
        LIMIT :n
    """
    try:
        result_rows = execute_with_retry(sql, {"player_id": player_id, "n": n})
        rows = []
        for row in result_rows:
            record = dict(row._mapping)
            record = _format_date(record)
            rows.append(record)
        return rows
    except Exception as e:
        logging.error(f"Error in get_last_n_pitcher_props for player {player_id}: {str(e)}")
        return []


def _classify_player(markets: dict) -> str:
    """Return 'batter', 'pitcher', or 'unknown' based on market keys."""
    for key in markets:
        if key in BATTER_MARKETS:
            return "batter"
        if key in PITCHER_MARKETS:
            return "pitcher"
    return "unknown"


def get_structured_mlb_player_props(event_id, limit=5):
    try:
        event_data = get_mlb_player_props(event_id)
        if isinstance(event_data, dict) and event_data.get("error"):
            return None, event_data["error"]
        if not event_data:
            return None, "No player props found for this event."

        result = combine_mlb_player_props(event_data)
        home_team_name = result.get("home_team")
        away_team_name = result.get("away_team")

        try:
            home_team_id = get_mlb_team_id_by_odds_api_team_name(home_team_name)
            away_team_id = get_mlb_team_id_by_odds_api_team_name(away_team_name)
        except Exception as e:
            logging.error(f"Error getting MLB team IDs: {str(e)}")
            return None, f"Database error while resolving team IDs: {str(e)}"

        home_batters = {}
        home_pitchers = {}
        away_batters = {}
        away_pitchers = {}

        for bookmaker in result.get("bookmakers", []):
            for player_name, player_markets in bookmaker.get("players", {}).items():
                player_type = _classify_player(player_markets)
                if player_type == "unknown":
                    continue

                try:
                    team_id, player_id = resolve_mlb_player(player_name)
                except Exception as e:
                    logging.error(f"Error resolving MLB player '{player_name}': {str(e)}")
                    continue

                player_data = dict(player_markets)
                player_data["player_id"] = player_id

                if player_id:
                    try:
                        if player_type == "batter":
                            player_data["historical"] = get_last_n_batter_props(player_id, n=limit)
                        else:
                            player_data["historical"] = get_last_n_pitcher_props(player_id, n=limit)
                    except Exception as e:
                        logging.error(f"Error getting historical data for player {player_id}: {str(e)}")
                        player_data["historical"] = []
                else:
                    player_data["historical"] = []

                if team_id == home_team_id:
                    if player_type == "batter":
                        home_batters[player_name] = player_data
                    else:
                        home_pitchers[player_name] = player_data
                elif team_id == away_team_id:
                    if player_type == "batter":
                        away_batters[player_name] = player_data
                    else:
                        away_pitchers[player_name] = player_data

        if not home_batters and not home_pitchers and not away_batters and not away_pitchers:
            return None, "No player props found for this event."

        response = {
            "commence_time": result.get("commence_time"),
            "home_team": {
                "name": home_team_name,
                "team_id": home_team_id,
                "batters": home_batters,
                "pitchers": home_pitchers
            },
            "away_team": {
                "name": away_team_name,
                "team_id": away_team_id,
                "batters": away_batters,
                "pitchers": away_pitchers
            }
        }
        return response, None
    except Exception as e:
        logging.error(f"Error in get_structured_mlb_player_props: {str(e)}")
        return None, f"Internal error in MLB player props service: {str(e)}"
