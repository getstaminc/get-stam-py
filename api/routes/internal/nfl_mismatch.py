"""Internal tool for resolving NFL player name mismatches.

Mirrors api/routes/internal/mlb_mismatch.py, adapted to NFL's schema: a single
nfl_player_props table (no separate batter/pitcher tables) and boxscore fetches
keyed directly by ESPN event id (no historical-date lookup needed).
"""

import os
import sys
from collections import defaultdict
from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# Add project root to sys.path so jobs module can be imported
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from jobs.nfl_historical_player_actuals_import_reverse import (
    get_game_boxscore,
    build_player_stats_lookup_nfl,
    normalize_player_name,
    process_game_reverse,
)

load_dotenv()

INTERNAL_PASSWORD = os.getenv("INTERNAL_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")

nfl_mismatch_bp = Blueprint("nfl_mismatch", __name__)


@nfl_mismatch_bp.before_request
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


def _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id):
    """Find an espn_event_id from a sibling prop record for the same game."""
    row = conn.execute(text("""
        SELECT espn_event_id FROM nfl_player_props
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
# GET /api/internal/nfl/mismatches
# ---------------------------------------------------------------------------

@nfl_mismatch_bp.route("/api/internal/nfl/mismatches", methods=["GET"])
def get_mismatches():
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, player_id, normalized_name, game_date,
                   odds_home_team, odds_away_team, nfl_player_props_id
            FROM nfl_player_name_mismatch
            WHERE resolved = false
            ORDER BY player_id, game_date
        """)).fetchall()

    groups = defaultdict(lambda: {"player_id": None, "odds_name": None, "mismatch_ids": [], "records": []})

    for row in rows:
        id_, player_id, normalized_name, game_date, odds_home_team, odds_away_team, props_id = row
        g = groups[player_id]
        g["player_id"] = player_id
        g["odds_name"] = normalized_name
        g["mismatch_ids"].append(id_)
        g["records"].append({
            "id": id_,
            "game_date": _date_str(game_date),
            "odds_home_team": odds_home_team,
            "odds_away_team": odds_away_team,
            "nfl_player_props_id": props_id,
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
# GET /api/internal/nfl/mismatches/<player_id>/candidates
# ---------------------------------------------------------------------------

def _compute_mismatch_candidates(engine, player_id):
    """Core candidate-lookup logic for a mismatched player. Returns (data, error)
    where error is (message, status_code) or None."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, normalized_name, game_date, odds_home_team_id, odds_away_team_id
            FROM nfl_player_name_mismatch
            WHERE resolved = false AND player_id = :player_id
            ORDER BY game_date
        """), {"player_id": player_id}).fetchall()

        if not rows:
            return None, ("No unresolved mismatches found for this player", 404)

        odds_name = rows[0][1]
        espn_event_id = None

        for row in rows:
            _, normalized_name, game_date, home_team_id, away_team_id = row
            eid = _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id)
            if eid:
                espn_event_id = eid
                break

    if not espn_event_id:
        return None, ("Could not find a sibling prop with espn_event_id for any mismatch date", 404)

    boxscore_data = get_game_boxscore(espn_event_id)
    if not boxscore_data:
        return None, (f"Could not fetch ESPN boxscore for event {espn_event_id}", 500)

    player_lookup, _ = build_player_stats_lookup_nfl(boxscore_data)

    normalized_odds = normalize_player_name(odds_name)

    candidates = []
    for espn_name, stats in player_lookup.items():
        espn_pid = stats.get("espn_player_id")
        display_name = stats.get("player_name", "")
        if not espn_pid:
            continue
        score = score_candidate(normalized_odds, espn_name)
        candidates.append({
            "espn_player_id": espn_pid,
            "espn_display_name": display_name,
            "similarity_score": round(score, 3),
            "espn_event_id": espn_event_id,
            "source": "boxscore",
        })

    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    candidates = candidates[:8]

    # If boxscore gave us nothing useful, fall back to searching nfl_players by name tokens
    if not candidates or all(c["similarity_score"] == 0.0 for c in candidates):
        tokens = [t for t in normalized_odds.split() if len(t) > 2]
        if tokens:
            conditions = " OR ".join([f"normalized_name LIKE :tok{i}" for i in range(len(tokens))])
            params = {f"tok{i}": f"%{tok}%" for i, tok in enumerate(tokens)}
            with engine.connect() as conn:
                rows = conn.execute(text(f"""
                    SELECT espn_player_id, player_name, normalized_name
                    FROM nfl_players
                    WHERE espn_player_id IS NOT NULL
                      AND ({conditions})
                    ORDER BY normalized_name
                    LIMIT 20
                """), params).fetchall()

            db_candidates = []
            for row in rows:
                espn_pid, display_name, norm_name = row
                score = score_candidate(normalized_odds, norm_name)
                db_candidates.append({
                    "espn_player_id": espn_pid,
                    "espn_display_name": display_name,
                    "similarity_score": round(score, 3),
                    "espn_event_id": espn_event_id,
                    "source": "db_search",
                })
            db_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
            candidates = db_candidates[:8]

    return {
        "player_id": player_id,
        "odds_name": odds_name,
        "espn_event_id": espn_event_id,
        "candidates": candidates,
    }, None


@nfl_mismatch_bp.route("/api/internal/nfl/mismatches/<int:player_id>/candidates", methods=["GET"])
def get_candidates(player_id):
    engine = _get_engine()
    data, error = _compute_mismatch_candidates(engine, player_id)
    if error:
        message, status = error
        return jsonify({"error": message}), status
    return jsonify(data)


# ---------------------------------------------------------------------------
# POST /api/internal/nfl/mismatches/<player_id>/resolve
# ---------------------------------------------------------------------------

def _do_resolve_mismatch(engine, player_id, espn_player_id, espn_name):
    """Core resolve/merge logic for a mismatched player. Returns (result, error)
    where error is (message, status_code) or None."""
    espn_player_id = str(espn_player_id)
    dates_processed = []
    dates_skipped = []
    merged_into = None

    # Step 1: load this player's unresolved mismatches (game dates drive the backfill below).
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, game_date, odds_home_team_id, odds_away_team_id
            FROM nfl_player_name_mismatch
            WHERE resolved = false AND player_id = :player_id
            ORDER BY game_date
        """), {"player_id": player_id}).fetchall()
        mismatch_data = [tuple(row) for row in rows]
    mismatch_ids = [row[0] for row in mismatch_data]

    # Step 2: point this player at the ESPN id. If another nfl_players row already owns
    # that id (the odds and ESPN spellings each spawned their own row — e.g.
    # "Lamar Jackson (BAL)" vs "Lamar Jackson"), merge this one into that row instead
    # of hitting the UNIQUE(espn_player_id) constraint.
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                UPDATE nfl_players SET espn_player_id = :espn_player_id WHERE id = :player_id
            """), {"espn_player_id": espn_player_id, "player_id": player_id})
            conn.commit()
        except IntegrityError:
            conn.rollback()
            row = conn.execute(text("""
                SELECT id FROM nfl_players WHERE espn_player_id = :espn_player_id
            """), {"espn_player_id": espn_player_id}).fetchone()
            if not row:
                return None, ("Duplicate ESPN ID but existing player not found", 500)
            merged_into = row[0]

            # Move this player's props onto the existing player (skip games it already has),
            # clear its mismatch rows, then drop the now-empty duplicate row
            # (nfl_player_aliases cascades on delete).
            conn.execute(text("""
                UPDATE nfl_player_props SET player_id = :target_id
                WHERE player_id = :src_id
                  AND odds_event_id NOT IN (
                      SELECT odds_event_id FROM nfl_player_props WHERE player_id = :target_id
                  )
            """), {"target_id": merged_into, "src_id": player_id})
            conn.execute(text("DELETE FROM nfl_player_props WHERE player_id = :src_id"), {"src_id": player_id})
            conn.execute(text("DELETE FROM nfl_player_name_mismatch WHERE player_id = :src_id"), {"src_id": player_id})
            conn.execute(text("DELETE FROM nfl_players WHERE id = :player_id"), {"player_id": player_id})
            conn.commit()

    # Step 3: backfill actuals for each mismatch game via its sibling ESPN event.
    for mismatch_id, game_date, home_team_id, away_team_id in mismatch_data:
        date_str = _date_str(game_date)

        with engine.connect() as conn:
            eid = _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id)

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

    # Step 4: delete the resolved mismatch records (the merge path already cleared them).
    if merged_into is None and mismatch_ids:
        with engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM nfl_player_name_mismatch WHERE id = ANY(:ids)
            """), {"ids": mismatch_ids})
            conn.commit()

    return {
        "espn_player_id_set": True,
        "espn_name": espn_name,
        "merged_into_player_id": merged_into,
        "dates_processed": dates_processed,
        "dates_skipped": dates_skipped,
    }, None


@nfl_mismatch_bp.route("/api/internal/nfl/mismatches/<int:player_id>/resolve", methods=["POST"])
def resolve_mismatch(player_id):
    body = request.get_json()
    if not body or "espn_player_id" not in body:
        return jsonify({"error": "Missing espn_player_id in request body"}), 400

    engine = _get_engine()
    result, error = _do_resolve_mismatch(engine, player_id, body["espn_player_id"], body.get("espn_name", ""))
    if error:
        message, status = error
        return jsonify({"error": message}), status
    return jsonify(result)


# ---------------------------------------------------------------------------
# Placeholder players — nfl_players with espn_player_id IS NULL
# ---------------------------------------------------------------------------

@nfl_mismatch_bp.route("/api/internal/nfl/placeholders", methods=["GET"])
def get_placeholder_players():
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.id, p.normalized_name,
                   COUNT(pp.id) AS props_count,
                   MIN(pp.game_date) AS first_game,
                   MAX(pp.game_date) AS last_game
            FROM nfl_players p
            JOIN nfl_player_props pp ON pp.player_id = p.id
            WHERE p.espn_player_id IS NULL
            GROUP BY p.id, p.normalized_name
            HAVING COUNT(pp.id) > 0
            ORDER BY p.normalized_name
        """)).fetchall()

    result = []
    for row in rows:
        player_id, normalized_name, props_count, first_game, last_game = row
        result.append({
            "player_id": player_id,
            "normalized_name": normalized_name,
            "total_props": props_count,
            "first_game": _date_str(first_game) if first_game else None,
            "last_game": _date_str(last_game) if last_game else None,
        })

    return jsonify(result)


def _compute_placeholder_candidates(engine, player_id):
    """Core candidate-lookup logic for a placeholder player. Returns (data, error)
    where error is (message, status_code) or None."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT normalized_name FROM nfl_players
            WHERE id = :player_id AND espn_player_id IS NULL
        """), {"player_id": player_id}).fetchone()

    if not row:
        return None, ("Placeholder player not found", 404)

    normalized_odds = row[0]
    tokens = [t for t in normalized_odds.split() if len(t) > 2]

    if not tokens:
        return {"player_id": player_id, "odds_name": normalized_odds, "candidates": []}, None

    conditions = " OR ".join([f"normalized_name LIKE :tok{i}" for i in range(len(tokens))])
    params = {f"tok{i}": f"%{tok}%" for i, tok in enumerate(tokens)}
    params["player_id"] = player_id

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT espn_player_id, player_name, normalized_name
            FROM nfl_players
            WHERE espn_player_id IS NOT NULL
              AND id != :player_id
              AND ({conditions})
            ORDER BY normalized_name
            LIMIT 20
        """), params).fetchall()

    candidates = []
    for r in rows:
        espn_pid, display_name, norm_name = r
        score = score_candidate(normalized_odds, norm_name)
        candidates.append({
            "espn_player_id": espn_pid,
            "espn_display_name": display_name,
            "similarity_score": round(score, 3),
            "source": "db_search",
        })
    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {
        "player_id": player_id,
        "odds_name": normalized_odds,
        "candidates": candidates[:8],
    }, None


@nfl_mismatch_bp.route("/api/internal/nfl/placeholders/<int:player_id>/candidates", methods=["GET"])
def get_placeholder_candidates(player_id):
    engine = _get_engine()
    data, error = _compute_placeholder_candidates(engine, player_id)
    if error:
        message, status = error
        return jsonify({"error": message}), status
    return jsonify(data)


def _do_resolve_placeholder(engine, player_id, espn_player_id, espn_name):
    """Core resolve/merge logic for a placeholder player. Returns (result, error)
    where error is (message, status_code) or None."""
    espn_player_id = str(espn_player_id)

    # Step 1: set espn_player_id on the placeholder.
    # If another player already has this ESPN ID, merge the placeholder into that player.
    merged_from = None
    target_player_id = player_id
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                UPDATE nfl_players SET espn_player_id = :espn_player_id
                WHERE id = :player_id AND espn_player_id IS NULL
            """), {"espn_player_id": espn_player_id, "player_id": player_id})
            conn.commit()
        except IntegrityError:
            conn.rollback()
            # Find the existing player that owns this ESPN ID
            row = conn.execute(text("""
                SELECT id, normalized_name FROM nfl_players WHERE espn_player_id = :espn_player_id
            """), {"espn_player_id": espn_player_id}).fetchone()
            if not row:
                return None, ("Duplicate ESPN ID but existing player not found", 500)
            target_player_id, target_name = row[0], row[1]
            merged_from = player_id

            # Move props from placeholder → existing player (skip any that conflict)
            conn.execute(text("""
                UPDATE nfl_player_props SET player_id = :target_id
                WHERE player_id = :src_id
                  AND odds_event_id NOT IN (
                      SELECT odds_event_id FROM nfl_player_props WHERE player_id = :target_id
                  )
            """), {"target_id": target_player_id, "src_id": player_id})
            conn.execute(text("DELETE FROM nfl_player_props WHERE player_id = :src_id"), {"src_id": player_id})

            # Remove the duplicate placeholder (mismatch rows have a non-cascading FK,
            # so they must be cleared explicitly before the player row can be deleted).
            conn.execute(text("DELETE FROM nfl_player_aliases WHERE player_id = :player_id"), {"player_id": player_id})
            conn.execute(text("DELETE FROM nfl_player_name_mismatch WHERE player_id = :player_id"), {"player_id": player_id})
            conn.execute(text("DELETE FROM nfl_players WHERE id = :player_id"), {"player_id": player_id})
            conn.commit()

    # Step 2: find all espn_event_ids already linked to the target player's prop records
    with engine.connect() as conn:
        event_rows = conn.execute(text("""
            SELECT DISTINCT espn_event_id, game_date FROM nfl_player_props
            WHERE player_id = :player_id AND espn_event_id IS NOT NULL
            ORDER BY game_date
        """), {"player_id": target_player_id}).fetchall()
        event_data = [tuple(r) for r in event_rows]

    # Step 3: backfill actuals for each linked game
    dates_processed = []
    dates_skipped = []

    for eid, game_date in event_data:
        date_str = _date_str(game_date)
        with engine.connect() as conn:
            try:
                process_game_reverse(conn, eid, game_date)
                conn.commit()
                dates_processed.append(date_str)
            except Exception as e:
                conn.rollback()
                print(f"Error processing game {eid} for date {date_str}: {e}")
                dates_skipped.append(date_str)

    return {
        "espn_player_id_set": True,
        "espn_name": espn_name,
        "merged_placeholder_id": merged_from,
        "dates_processed": dates_processed,
        "dates_skipped": dates_skipped,
    }, None


@nfl_mismatch_bp.route("/api/internal/nfl/placeholders/<int:player_id>/resolve", methods=["POST"])
def resolve_placeholder(player_id):
    body = request.get_json()
    if not body or "espn_player_id" not in body:
        return jsonify({"error": "Missing espn_player_id in request body"}), 400

    engine = _get_engine()
    result, error = _do_resolve_placeholder(engine, player_id, body["espn_player_id"], body.get("espn_name", ""))
    if error:
        message, status = error
        return jsonify({"error": message}), status
    return jsonify(result)


# ---------------------------------------------------------------------------
# POST /api/internal/nfl/auto-resolve-exact-matches
#
# Sweeps both queues (mismatches + placeholders) and auto-confirms only the
# unambiguous case: exactly one candidate whose similarity score is 1.00. A
# single candidate at a perfect token-overlap score means the odds-API name
# and an already-ESPN-linked player's name are identical strings, which is
# the same standard a human reviewer applies when clicking "Confirm Match"
# on a 1.00 entry. Everything else (0, 2+ candidates, or a top score < 1.00)
# is left for manual review.
# ---------------------------------------------------------------------------

@nfl_mismatch_bp.route("/api/internal/nfl/auto-resolve-exact-matches", methods=["POST"])
def auto_resolve_exact_matches():
    engine = _get_engine()
    resolved = []
    skipped = []

    with engine.connect() as conn:
        mismatch_player_ids = [r[0] for r in conn.execute(text("""
            SELECT DISTINCT player_id FROM nfl_player_name_mismatch WHERE resolved = false
        """)).fetchall()]

        placeholder_player_ids = [r[0] for r in conn.execute(text("""
            SELECT p.id
            FROM nfl_players p
            JOIN nfl_player_props pp ON pp.player_id = p.id
            WHERE p.espn_player_id IS NULL
            GROUP BY p.id
            HAVING COUNT(pp.id) > 0
        """)).fetchall()]

    queues = [
        ("mismatch", mismatch_player_ids, _compute_mismatch_candidates, _do_resolve_mismatch),
        ("placeholder", placeholder_player_ids, _compute_placeholder_candidates, _do_resolve_placeholder),
    ]

    for queue_name, player_ids, compute_candidates, do_resolve in queues:
        for player_id in player_ids:
            try:
                data, error = compute_candidates(engine, player_id)
                if error or not data:
                    skipped.append({"player_id": player_id, "queue": queue_name, "reason": error[0] if error else "no data"})
                    continue

                candidates = data["candidates"]
                if len(candidates) != 1 or candidates[0]["similarity_score"] != 1.0:
                    skipped.append({
                        "player_id": player_id,
                        "queue": queue_name,
                        "odds_name": data.get("odds_name"),
                        "reason": f"{len(candidates)} candidate(s)" if candidates else "no candidates",
                    })
                    continue

                cand = candidates[0]
                result, error = do_resolve(engine, player_id, cand["espn_player_id"], cand["espn_display_name"])
                if error:
                    skipped.append({"player_id": player_id, "queue": queue_name, "reason": error[0]})
                    continue

                resolved.append({
                    "player_id": player_id,
                    "queue": queue_name,
                    "odds_name": data.get("odds_name"),
                    "espn_player_id": cand["espn_player_id"],
                    "espn_name": cand["espn_display_name"],
                    "merged_into_player_id": result.get("merged_into_player_id") or result.get("merged_placeholder_id"),
                })
            except Exception as e:
                skipped.append({"player_id": player_id, "queue": queue_name, "reason": str(e)})

    return jsonify({
        "auto_resolved_count": len(resolved),
        "auto_resolved": resolved,
        "skipped_count": len(skipped),
        "skipped": skipped,
    })
