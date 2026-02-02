import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
engine = create_engine(DATABASE_URL)

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
    with engine.connect() as conn:
        result = conn.execute(text(sql), {"player_id": player_id, "n": n})
        rows = [dict(row._mapping) for row in result.fetchall()]
    return rows
from ..external_requests.player_props_api import get_player_props, combine_player_props
from ..external_requests.player_team_lookup import get_team_id_for_player
from ..external_requests.team_lookup import get_team_id_by_odds_api_team_name

def get_structured_player_props(event_id):
    event_data = get_player_props(event_id)
    if not event_data:
        return None, 'Could not fetch player props'
    result = combine_player_props(event_data)

    home_team_name = result.get("home_team")
    away_team_name = result.get("away_team")
    home_team_id = get_team_id_by_odds_api_team_name(home_team_name)
    away_team_id = get_team_id_by_odds_api_team_name(away_team_name)

    home_players = {}
    away_players = {}
    for bookmaker in result.get("bookmakers", []):
        for player_name, player_markets in bookmaker.get("players", {}).items():
            team_id, player_id = get_team_id_for_player(player_name)
            player_markets["player_id"] = player_id
            # Add historical records
            if player_id:
                player_markets["historical"] = get_last_n_player_props(player_id, n=5)
            else:
                player_markets["historical"] = []
            if team_id == home_team_id:
                home_players[player_name] = player_markets
            elif team_id == away_team_id:
                away_players[player_name] = player_markets

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
