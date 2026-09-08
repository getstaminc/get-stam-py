import os
import logging
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from cachetools import TTLCache, cached

from ..external_requests.nfl_player_props_api import get_nfl_player_props, combine_nfl_player_props
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
        "application_name": "nfl_player_props_service"
    }
)

_nfl_props_cache = TTLCache(maxsize=1000, ttl=21600)  # 6 hours

# Odds API market key -> the nfl_player_props odds column exposed to the frontend.
# (The table itself is queried column-by-column below; this map is only used to
# decide which players carry a prop we care about.)
NFL_PLAYER_MARKETS = {
    "player_pass_yds", "player_pass_tds", "player_rush_yds",
    "player_reception_yds", "player_receptions", "player_anytime_td",
}


def execute_with_retry(sql, params, max_retries=3):
    for attempt in range(max_retries):
        conn = None
        try:
            conn = engine.connect()
            result = conn.execute(text(sql), params)
            return result.fetchall()
        except Exception as e:
            logging.error(f"NFL props DB error attempt {attempt + 1}: {str(e)}")
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


def resolve_nfl_player(player_name):
    """Return (team_name, player_id) for an NFL player name, checking aliases first.

    nfl_players.team_id is not populated, so the player's team is taken from their
    most recent nfl_player_props row (player_team_name, an Odds API full team name).
    """
    normalized = normalize_name(player_name)
    try:
        rows = execute_with_retry(
            "SELECT player_id FROM nfl_player_aliases WHERE normalized_name = :name",
            {"name": normalized}
        )
        if rows:
            player_id = rows[0][0]
        else:
            rows = execute_with_retry(
                "SELECT id FROM nfl_players WHERE normalized_name = :name",
                {"name": normalized}
            )
            if not rows:
                return None, None
            player_id = rows[0][0]

        team_rows = execute_with_retry(
            """
            SELECT player_team_name FROM nfl_player_props
            WHERE player_id = :player_id AND player_team_name IS NOT NULL
            ORDER BY game_date DESC
            LIMIT 1
            """,
            {"player_id": player_id}
        )
        team_name = team_rows[0][0] if team_rows else None
        return team_name, player_id
    except Exception as e:
        logging.error(f"Error resolving NFL player '{player_name}': {str(e)}")
        return None, None


@cached(cache=_nfl_props_cache)
def get_last_n_nfl_props(player_id, n=5):
    sql = """
        SELECT
            game_date,
            MAX(odds_player_pass_yds)          AS odds_player_pass_yds,
            MAX(odds_player_pass_tds)          AS odds_player_pass_tds,
            MAX(odds_player_rush_yds)          AS odds_player_rush_yds,
            MAX(odds_player_reception_yds)     AS odds_player_reception_yds,
            MAX(odds_player_receptions)        AS odds_player_receptions,
            MAX(odds_player_anytime_td)        AS odds_player_anytime_td,
            MAX(actual_player_pass_yds)        AS actual_player_pass_yds,
            MAX(actual_player_pass_tds)        AS actual_player_pass_tds,
            MAX(actual_player_rush_yds)        AS actual_player_rush_yds,
            MAX(actual_player_reception_yds)   AS actual_player_reception_yds,
            MAX(actual_player_receptions)      AS actual_player_receptions,
            MAX(actual_player_anytime_td::int) AS actual_player_anytime_td,
            MAX(opponent_team_name)            AS opponent_team_name,
            MAX(player_team_name)              AS player_team_name
        FROM nfl_player_props
        WHERE player_id = :player_id AND did_not_play IS NOT TRUE
        GROUP BY game_date, odds_event_id
        ORDER BY game_date DESC
        LIMIT :n
    """
    try:
        result_rows = execute_with_retry(sql, {"player_id": player_id, "n": n})
        rows = []
        for row in result_rows:
            record = dict(row._mapping)
            rows.append(_format_date(record))
        return rows
    except Exception as e:
        logging.error(f"Error in get_last_n_nfl_props for player {player_id}: {str(e)}")
        return []


def get_structured_nfl_player_props(event_id, limit=5):
    try:
        event_data = get_nfl_player_props(event_id)
        if isinstance(event_data, dict) and event_data.get("error"):
            return None, event_data["error"]
        if not event_data:
            return None, "No player props found for this event."

        result = combine_nfl_player_props(event_data)
        home_team_name = result.get("home_team")
        away_team_name = result.get("away_team")

        home_players = {}
        away_players = {}

        for bookmaker in result.get("bookmakers", []):
            for player_name, player_markets in bookmaker.get("players", {}).items():
                if not any(k in NFL_PLAYER_MARKETS for k in player_markets):
                    continue

                try:
                    team_name, player_id = resolve_nfl_player(player_name)
                except Exception as e:
                    logging.error(f"Error resolving NFL player '{player_name}': {str(e)}")
                    continue

                if not player_id:
                    # Unresolved name (covers team D/ST that slipped through) — skip.
                    continue

                player_data = dict(player_markets)
                player_data["player_id"] = player_id
                try:
                    player_data["historical"] = get_last_n_nfl_props(player_id, n=limit)
                except Exception as e:
                    logging.error(f"Error getting historical data for player {player_id}: {str(e)}")
                    player_data["historical"] = []

                if team_name == home_team_name:
                    home_players[player_name] = player_data
                elif team_name == away_team_name:
                    away_players[player_name] = player_data
                # else: player's last known team isn't in this matchup — skip
                # (traded player with stale history, or a name collision).

        if not home_players and not away_players:
            return None, "No player props found for this event."

        response = {
            "commence_time": result.get("commence_time"),
            "home_team": {
                "name": home_team_name,
                "players": home_players,
            },
            "away_team": {
                "name": away_team_name,
                "players": away_players,
            },
        }
        return response, None
    except Exception as e:
        logging.error(f"Error in get_structured_nfl_player_props: {str(e)}")
        return None, f"Internal error in NFL player props service: {str(e)}"
