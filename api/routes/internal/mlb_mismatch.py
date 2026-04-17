"""Internal tool for resolving MLB player name mismatches."""

import os
import sys
from collections import defaultdict
from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add project root to sys.path so jobs module can be imported
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from jobs.mlb_historical_player_actuals_import_reverse import (
    get_historical_game_boxscore,
    build_player_stats_lookup_mlb,
    normalize_player_name,
    process_game_reverse,
)

load_dotenv()

INTERNAL_PASSWORD = os.getenv("INTERNAL_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")

mlb_mismatch_bp = Blueprint("mlb_mismatch", __name__)


@mlb_mismatch_bp.before_request
def check_internal_password():
    if request.method == "OPTIONS":
        return
    pwd = request.headers.get("X-Internal-Password")
    if not INTERNAL_PASSWORD or pwd != INTERNAL_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401


def _get_engine():
    return create_engine(DATABASE_URL)


def score_candidate(odds_name: str, espn_name: str) -> float:
    """Token overlap score between normalized odds name and ESPN name."""
    odds_tokens = set(odds_name.split())
    espn_tokens = set(espn_name.split())
    overlap = len(odds_tokens & espn_tokens)
    return overlap / max(len(odds_tokens), len(espn_tokens), 1)


def _date_str(game_date) -> str:
    return game_date.isoformat() if hasattr(game_date, "isoformat") else str(game_date)


def _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id, player_type):
    """Find an espn_event_id from a sibling prop record for the same game."""
    table = "mlb_batter_props" if player_type == "batter" else "mlb_pitcher_props"
    row = conn.execute(text(f"""
        SELECT espn_event_id FROM {table}
        WHERE game_date = :game_date
          AND odds_home_team_id = :home_id
          AND odds_away_team_id = :away_id
          AND espn_event_id IS NOT NULL
          AND player_id != :player_id
        LIMIT 1
    """), {
        "game_date": game_date,
        "home_id": home_team_id,
        "away_id": away_team_id,
        "player_id": player_id,
    }).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# GET /api/internal/mlb/mismatches
# ---------------------------------------------------------------------------

@mlb_mismatch_bp.route("/api/internal/mlb/mismatches", methods=["GET"])
def get_mismatches():
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, player_id, normalized_name, game_date,
                   odds_home_team, odds_away_team,
                   batter_props_id, pitcher_props_id
            FROM mlb_player_name_mismatch
            WHERE resolved = false
            ORDER BY player_id, game_date
        """)).fetchall()

    groups = defaultdict(lambda: {"player_id": None, "odds_name": None, "mismatch_ids": [], "records": []})

    for row in rows:
        id_, player_id, normalized_name, game_date, odds_home_team, odds_away_team, batter_props_id, pitcher_props_id = row
        g = groups[player_id]
        g["player_id"] = player_id
        g["odds_name"] = normalized_name
        g["mismatch_ids"].append(id_)
        g["records"].append({
            "id": id_,
            "game_date": _date_str(game_date),
            "odds_home_team": odds_home_team,
            "odds_away_team": odds_away_team,
            "player_type": "batter" if batter_props_id else "pitcher",
            "batter_props_id": batter_props_id,
            "pitcher_props_id": pitcher_props_id,
        })

    result = [
        {
            "player_id": g["player_id"],
            "odds_name": g["odds_name"],
            "total_mismatches": len(g["mismatch_ids"]),
            "mismatch_ids": g["mismatch_ids"],
            "records": g["records"],
        }
        for g in groups.values()
    ]
    return jsonify(result)


# ---------------------------------------------------------------------------
# GET /api/internal/mlb/mismatches/<player_id>/candidates
# ---------------------------------------------------------------------------

@mlb_mismatch_bp.route("/api/internal/mlb/mismatches/<int:player_id>/candidates", methods=["GET"])
def get_candidates(player_id):
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, normalized_name, game_date,
                   batter_props_id, pitcher_props_id,
                   odds_home_team_id, odds_away_team_id
            FROM mlb_player_name_mismatch
            WHERE resolved = false AND player_id = :player_id
            ORDER BY game_date
        """), {"player_id": player_id}).fetchall()

        if not rows:
            return jsonify({"error": "No unresolved mismatches found for this player"}), 404

        odds_name = rows[0][1]
        espn_event_id = None
        game_date_used = None

        for row in rows:
            _, normalized_name, game_date, batter_props_id, pitcher_props_id, home_team_id, away_team_id = row
            player_type = "batter" if batter_props_id else "pitcher"
            eid = _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id, player_type)
            if eid:
                espn_event_id = eid
                game_date_used = game_date
                break

    if not espn_event_id:
        return jsonify({"error": "Could not find a sibling prop with espn_event_id for any mismatch date"}), 404

    boxscore_data = get_historical_game_boxscore(espn_event_id, game_date_used)
    if not boxscore_data:
        return jsonify({"error": f"Could not fetch ESPN boxscore for event {espn_event_id}"}), 500

    batter_lookup, pitcher_lookup, _ = build_player_stats_lookup_mlb(boxscore_data)

    # Collect unique ESPN players from both lookups
    all_espn_players: dict[str, str] = {}  # espn_player_id -> display_name
    for stats in list(batter_lookup.values()) + list(pitcher_lookup.values()):
        eid = stats.get("espn_player_id")
        display_name = stats.get("player_name", "")
        if eid and eid not in all_espn_players:
            all_espn_players[eid] = display_name

    normalized_odds = normalize_player_name(odds_name)

    candidates = []
    for espn_pid, display_name in all_espn_players.items():
        norm_espn = normalize_player_name(display_name)
        score = score_candidate(normalized_odds, norm_espn)
        candidates.append({
            "espn_player_id": espn_pid,
            "espn_display_name": display_name,
            "similarity_score": round(score, 3),
            "espn_event_id": espn_event_id,
        })

    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    candidates = candidates[:8]

    return jsonify({
        "player_id": player_id,
        "odds_name": odds_name,
        "espn_event_id": espn_event_id,
        "candidates": candidates,
    })


# ---------------------------------------------------------------------------
# POST /api/internal/mlb/mismatches/<player_id>/resolve
# ---------------------------------------------------------------------------

@mlb_mismatch_bp.route("/api/internal/mlb/mismatches/<int:player_id>/resolve", methods=["POST"])
def resolve_mismatch(player_id):
    body = request.get_json()
    if not body or "espn_player_id" not in body:
        return jsonify({"error": "Missing espn_player_id in request body"}), 400

    espn_player_id = str(body["espn_player_id"])
    espn_name = body.get("espn_name", "")

    engine = _get_engine()
    dates_processed = []
    dates_skipped = []

    # Step 1: update espn_player_id in mlb_players
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE mlb_players SET espn_player_id = :espn_player_id WHERE id = :player_id
        """), {"espn_player_id": espn_player_id, "player_id": player_id})
        conn.commit()

    # Step 2: load mismatches and collect espn_event_ids per mismatch
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, game_date, batter_props_id, pitcher_props_id,
                   odds_home_team_id, odds_away_team_id
            FROM mlb_player_name_mismatch
            WHERE resolved = false AND player_id = :player_id
            ORDER BY game_date
        """), {"player_id": player_id}).fetchall()
        mismatch_data = [tuple(row) for row in rows]

    # Step 3: for each mismatch, run process_game_reverse in its own connection
    mismatch_ids_to_mark = []
    for row in mismatch_data:
        mismatch_id, game_date, batter_props_id, pitcher_props_id, home_team_id, away_team_id = row
        player_type = "batter" if batter_props_id else "pitcher"
        date_str = _date_str(game_date)
        mismatch_ids_to_mark.append(mismatch_id)

        with engine.connect() as conn:
            eid = _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id, player_type)

        if eid:
            with engine.connect() as conn:
                try:
                    process_game_reverse(conn, eid, game_date)
                    conn.commit()
                    dates_processed.append(date_str)
                except Exception as e:
                    conn.rollback()
                    print(f"Error processing game {eid} for date {date_str}: {e}")
                    dates_skipped.append(date_str)
        else:
            dates_skipped.append(date_str)

    # Step 4: delete resolved mismatch records
    if mismatch_ids_to_mark:
        with engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM mlb_player_name_mismatch WHERE id = ANY(:ids)
            """), {"ids": mismatch_ids_to_mark})
            conn.commit()

    return jsonify({
        "espn_player_id_set": True,
        "espn_name": espn_name,
        "dates_processed": dates_processed,
        "dates_skipped": dates_skipped,
    })
