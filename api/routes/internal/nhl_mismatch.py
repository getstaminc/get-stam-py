"""Internal tool for resolving NHL player name mismatches. Mirrors
api/routes/internal/nfl_mismatch.py exactly -- same schema shape
(nhl_player_props/nhl_players/nhl_player_aliases/nhl_player_name_mismatch),
same boxscore-fetch-by-ESPN-event-id approach. NHL has no team D/ST
equivalent, so there's nothing to split out of the candidate-scoring path.
"""
import os
import sys
from collections import defaultdict
import requests
from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from jobs.nhl_historical_player_actuals_import_reverse import (
    get_game_boxscore,
    build_player_stats_lookup_nhl,
    normalize_player_name,
    process_game_reverse,
)

load_dotenv()

INTERNAL_PASSWORD = os.getenv("INTERNAL_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")

nhl_mismatch_bp = Blueprint("nhl_mismatch", __name__)


@nhl_mismatch_bp.before_request
def check_internal_password():
    if request.method == "OPTIONS":
        return
    pwd = request.headers.get("X-Internal-Password")
    if not INTERNAL_PASSWORD or pwd != INTERNAL_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401


def _get_engine():
    return create_engine(DATABASE_URL)


_SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}


def _scoring_tokens(name: str) -> set:
    return {t for t in name.split() if t not in _SUFFIX_TOKENS}


def score_candidate(odds_name: str, espn_name: str) -> float:
    odds_tokens = _scoring_tokens(odds_name)
    espn_tokens = _scoring_tokens(espn_name)
    overlap = len(odds_tokens & espn_tokens)
    return overlap / max(len(odds_tokens), len(espn_tokens), 1)


def _date_str(game_date) -> str:
    return game_date.isoformat() if hasattr(game_date, "isoformat") else str(game_date)


def search_espn_player_api(name: str) -> list:
    try:
        resp = requests.get("https://site.api.espn.com/apis/search/v2", params={"query": name, "limit": 10}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    candidates = []
    for result_type in data.get("results", []):
        if result_type.get("type") != "player":
            continue
        for item in result_type.get("contents", []):
            uid_parts = dict(p.split(":", 1) for p in item.get("uid", "").split("~") if ":" in p)
            if uid_parts.get("l") != "90":  # NHL league id
                continue
            espn_id = uid_parts.get("a")
            display_name = item.get("displayName", "")
            if not espn_id or not display_name:
                continue
            candidates.append({"espn_player_id": espn_id, "espn_display_name": display_name, "source": "espn_search"})
    return candidates


def _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id):
    row = conn.execute(text("""
        SELECT espn_event_id FROM nhl_player_props
        WHERE game_date = :game_date AND odds_home_team_id = :home_id AND odds_away_team_id = :away_id
          AND espn_event_id IS NOT NULL AND player_id != :player_id
        LIMIT 1
    """), {"game_date": game_date, "home_id": home_team_id, "away_id": away_team_id, "player_id": player_id}).fetchone()
    return row[0] if row else None


@nhl_mismatch_bp.route("/api/internal/nhl/mismatches", methods=["GET"])
def get_mismatches():
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, player_id, normalized_name, game_date, odds_home_team, odds_away_team, nhl_player_props_id
            FROM nhl_player_name_mismatch WHERE resolved = false ORDER BY player_id, game_date
        """)).fetchall()

    groups = defaultdict(lambda: {"player_id": None, "odds_name": None, "mismatch_ids": [], "records": []})
    for id_, player_id, normalized_name, game_date, odds_home_team, odds_away_team, props_id in rows:
        g = groups[player_id]
        g["player_id"] = player_id
        g["odds_name"] = normalized_name
        g["mismatch_ids"].append(id_)
        g["records"].append({
            "id": id_, "game_date": _date_str(game_date), "odds_home_team": odds_home_team,
            "odds_away_team": odds_away_team, "nhl_player_props_id": props_id,
        })

    result = [
        {"player_id": g["player_id"], "odds_name": g["odds_name"], "total_mismatches": len(g["mismatch_ids"]),
         "mismatch_ids": g["mismatch_ids"], "records": g["records"]}
        for g in groups.values()
    ]
    result.sort(key=lambda g: g["total_mismatches"], reverse=True)
    return jsonify(result)


def _compute_mismatch_candidates(engine, player_id):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, normalized_name, game_date, odds_home_team_id, odds_away_team_id
            FROM nhl_player_name_mismatch WHERE resolved = false AND player_id = :player_id ORDER BY game_date
        """), {"player_id": player_id}).fetchall()
        if not rows:
            return None, ("No unresolved mismatches found for this player", 404)

        odds_name = rows[0][1]
        espn_event_id = None
        for row in rows:
            eid = _find_sibling_espn_event(conn, row[2], row[3], row[4], player_id)
            if eid:
                espn_event_id = eid
                break

    if not espn_event_id:
        return None, ("Could not find a sibling prop with espn_event_id for any mismatch date", 404)

    boxscore_data = get_game_boxscore(espn_event_id)
    if not boxscore_data:
        return None, (f"Could not fetch ESPN boxscore for event {espn_event_id}", 500)

    player_lookup, _ = build_player_stats_lookup_nhl(boxscore_data)
    normalized_odds = normalize_player_name(odds_name)

    candidates = []
    for espn_name, stats in player_lookup.items():
        espn_pid = stats.get("espn_player_id")
        if not espn_pid:
            continue
        candidates.append({
            "espn_player_id": espn_pid, "espn_display_name": stats.get("player_name", ""),
            "similarity_score": round(score_candidate(normalized_odds, espn_name), 3),
            "espn_event_id": espn_event_id, "source": "boxscore",
        })
    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    candidates = candidates[:8]

    if not candidates or all(c["similarity_score"] == 0.0 for c in candidates):
        tokens = [t for t in normalized_odds.split() if len(t) > 2]
        if tokens:
            conditions = " OR ".join([f"normalized_name LIKE :tok{i}" for i in range(len(tokens))])
            params = {f"tok{i}": f"%{tok}%" for i, tok in enumerate(tokens)}
            with engine.connect() as conn:
                rows = conn.execute(text(f"""
                    SELECT espn_player_id, player_name, normalized_name FROM nhl_players
                    WHERE espn_player_id IS NOT NULL AND ({conditions}) ORDER BY normalized_name LIMIT 20
                """), params).fetchall()
            db_candidates = [
                {"espn_player_id": r[0], "espn_display_name": r[1],
                 "similarity_score": round(score_candidate(normalized_odds, r[2]), 3),
                 "espn_event_id": espn_event_id, "source": "db_search"}
                for r in rows
            ]
            db_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
            candidates = db_candidates[:8]

    if not candidates or candidates[0]["similarity_score"] < 1.0:
        merged = {c["espn_player_id"]: c for c in candidates}
        for cand in search_espn_player_api(odds_name):
            score = score_candidate(normalized_odds, normalize_player_name(cand["espn_display_name"]))
            cand = {**cand, "similarity_score": round(score, 3), "espn_event_id": espn_event_id}
            existing = merged.get(cand["espn_player_id"])
            if not existing or cand["similarity_score"] > existing["similarity_score"]:
                merged[cand["espn_player_id"]] = cand
        candidates = sorted(merged.values(), key=lambda x: x["similarity_score"], reverse=True)[:8]

    return {"player_id": player_id, "odds_name": odds_name, "espn_event_id": espn_event_id, "candidates": candidates}, None


@nhl_mismatch_bp.route("/api/internal/nhl/mismatches/<int:player_id>/candidates", methods=["GET"])
def get_candidates(player_id):
    data, error = _compute_mismatch_candidates(_get_engine(), player_id)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(data)


def _do_resolve_mismatch(engine, player_id, espn_player_id, espn_name):
    espn_player_id = str(espn_player_id)
    dates_processed, dates_skipped, merged_into = [], [], None

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, game_date, odds_home_team_id, odds_away_team_id
            FROM nhl_player_name_mismatch WHERE resolved = false AND player_id = :player_id ORDER BY game_date
        """), {"player_id": player_id}).fetchall()
        mismatch_data = [tuple(row) for row in rows]
    mismatch_ids = [row[0] for row in mismatch_data]

    with engine.connect() as conn:
        try:
            conn.execute(text("UPDATE nhl_players SET espn_player_id = :id WHERE id = :pid"),
                         {"id": espn_player_id, "pid": player_id})
            conn.commit()
        except IntegrityError:
            conn.rollback()
            row = conn.execute(text("SELECT id FROM nhl_players WHERE espn_player_id = :id"), {"id": espn_player_id}).fetchone()
            if not row:
                return None, ("Duplicate ESPN ID but existing player not found", 500)
            merged_into = row[0]

            src_player = conn.execute(text("SELECT player_name, normalized_name FROM nhl_players WHERE id = :pid"),
                                       {"pid": player_id}).fetchone()

            conn.execute(text("""
                UPDATE nhl_player_props SET player_id = :target_id
                WHERE player_id = :src_id AND odds_event_id NOT IN (
                    SELECT odds_event_id FROM nhl_player_props WHERE player_id = :target_id
                )
            """), {"target_id": merged_into, "src_id": player_id})
            conn.execute(text("DELETE FROM nhl_player_name_mismatch WHERE player_id = :src_id"), {"src_id": player_id})
            conn.execute(text("DELETE FROM nhl_player_props WHERE player_id = :src_id"), {"src_id": player_id})
            conn.execute(text("DELETE FROM nhl_players WHERE id = :pid"), {"pid": player_id})

            if src_player and src_player[1] is not None:
                conn.execute(text("""
                    INSERT INTO nhl_player_aliases (player_id, source, source_name, normalized_name, created_at)
                    VALUES (:pid, 'odds_api', :name, :norm, NOW()) ON CONFLICT (source, normalized_name) DO NOTHING
                """), {"pid": merged_into, "name": src_player[0], "norm": src_player[1]})
            conn.commit()

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

    if merged_into is None and mismatch_ids:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM nhl_player_name_mismatch WHERE id = ANY(:ids)"), {"ids": mismatch_ids})
            conn.commit()

    return {"espn_player_id_set": True, "espn_name": espn_name, "merged_into_player_id": merged_into,
            "dates_processed": dates_processed, "dates_skipped": dates_skipped}, None


@nhl_mismatch_bp.route("/api/internal/nhl/mismatches/<int:player_id>/resolve", methods=["POST"])
def resolve_mismatch(player_id):
    body = request.get_json()
    if not body or "espn_player_id" not in body:
        return jsonify({"error": "Missing espn_player_id in request body"}), 400
    result, error = _do_resolve_mismatch(_get_engine(), player_id, body["espn_player_id"], body.get("espn_name", ""))
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(result)


@nhl_mismatch_bp.route("/api/internal/nhl/placeholders", methods=["GET"])
def get_placeholder_players():
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.id, p.normalized_name, COUNT(pp.id), MIN(pp.game_date), MAX(pp.game_date)
            FROM nhl_players p JOIN nhl_player_props pp ON pp.player_id = p.id
            WHERE p.espn_player_id IS NULL
            GROUP BY p.id, p.normalized_name HAVING COUNT(pp.id) > 0
            ORDER BY COUNT(pp.id) DESC, p.normalized_name
        """)).fetchall()
    return jsonify([
        {"player_id": r[0], "normalized_name": r[1], "total_props": r[2],
         "first_game": _date_str(r[3]) if r[3] else None, "last_game": _date_str(r[4]) if r[4] else None}
        for r in rows
    ])


def _compute_placeholder_candidates(engine, player_id):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT normalized_name FROM nhl_players WHERE id = :pid AND espn_player_id IS NULL
        """), {"pid": player_id}).fetchone()
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
            SELECT espn_player_id, player_name, normalized_name FROM nhl_players
            WHERE espn_player_id IS NOT NULL AND id != :player_id AND ({conditions})
            ORDER BY normalized_name LIMIT 20
        """), params).fetchall()

    candidates = [
        {"espn_player_id": r[0], "espn_display_name": r[1],
         "similarity_score": round(score_candidate(normalized_odds, r[2]), 3), "source": "db_search"}
        for r in rows
    ]
    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    candidates = candidates[:8]

    if not candidates or candidates[0]["similarity_score"] < 1.0:
        merged = {c["espn_player_id"]: c for c in candidates}
        for cand in search_espn_player_api(normalized_odds):
            score = score_candidate(normalized_odds, normalize_player_name(cand["espn_display_name"]))
            cand = {**cand, "similarity_score": round(score, 3)}
            existing = merged.get(cand["espn_player_id"])
            if not existing or cand["similarity_score"] > existing["similarity_score"]:
                merged[cand["espn_player_id"]] = cand
        candidates = sorted(merged.values(), key=lambda x: x["similarity_score"], reverse=True)[:8]

    return {"player_id": player_id, "odds_name": normalized_odds, "candidates": candidates}, None


@nhl_mismatch_bp.route("/api/internal/nhl/placeholders/<int:player_id>/candidates", methods=["GET"])
def get_placeholder_candidates(player_id):
    data, error = _compute_placeholder_candidates(_get_engine(), player_id)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(data)


def _do_resolve_placeholder(engine, player_id, espn_player_id, espn_name):
    espn_player_id = str(espn_player_id)
    merged_from = None
    target_player_id = player_id

    with engine.connect() as conn:
        try:
            conn.execute(text("""
                UPDATE nhl_players SET espn_player_id = :id WHERE id = :pid AND espn_player_id IS NULL
            """), {"id": espn_player_id, "pid": player_id})
            conn.commit()
        except IntegrityError:
            conn.rollback()
            row = conn.execute(text("SELECT id, normalized_name FROM nhl_players WHERE espn_player_id = :id"),
                                {"id": espn_player_id}).fetchone()
            if not row:
                return None, ("Duplicate ESPN ID but existing player not found", 500)
            target_player_id = row[0]
            merged_from = player_id

            src_player = conn.execute(text("SELECT player_name, normalized_name FROM nhl_players WHERE id = :pid"),
                                       {"pid": player_id}).fetchone()

            conn.execute(text("""
                UPDATE nhl_player_props SET player_id = :target_id
                WHERE player_id = :src_id AND odds_event_id NOT IN (
                    SELECT odds_event_id FROM nhl_player_props WHERE player_id = :target_id
                )
            """), {"target_id": target_player_id, "src_id": player_id})
            conn.execute(text("DELETE FROM nhl_player_aliases WHERE player_id = :pid"), {"pid": player_id})
            conn.execute(text("DELETE FROM nhl_player_name_mismatch WHERE player_id = :pid"), {"pid": player_id})
            conn.execute(text("DELETE FROM nhl_player_props WHERE player_id = :src_id"), {"src_id": player_id})
            conn.execute(text("DELETE FROM nhl_players WHERE id = :pid"), {"pid": player_id})

            if src_player and src_player[1] is not None:
                conn.execute(text("""
                    INSERT INTO nhl_player_aliases (player_id, source, source_name, normalized_name, created_at)
                    VALUES (:pid, 'odds_api', :name, :norm, NOW()) ON CONFLICT (source, normalized_name) DO NOTHING
                """), {"pid": target_player_id, "name": src_player[0], "norm": src_player[1]})
            conn.commit()

    with engine.connect() as conn:
        event_rows = conn.execute(text("""
            SELECT DISTINCT espn_event_id, game_date FROM nhl_player_props
            WHERE player_id = :pid AND espn_event_id IS NOT NULL ORDER BY game_date
        """), {"pid": target_player_id}).fetchall()
        event_data = [tuple(r) for r in event_rows]

    dates_processed, dates_skipped = [], []
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

    return {"espn_player_id_set": True, "espn_name": espn_name, "merged_placeholder_id": merged_from,
            "dates_processed": dates_processed, "dates_skipped": dates_skipped}, None


@nhl_mismatch_bp.route("/api/internal/nhl/placeholders/<int:player_id>/resolve", methods=["POST"])
def resolve_placeholder(player_id):
    body = request.get_json()
    if not body or "espn_player_id" not in body:
        return jsonify({"error": "Missing espn_player_id in request body"}), 400
    result, error = _do_resolve_placeholder(_get_engine(), player_id, body["espn_player_id"], body.get("espn_name", ""))
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(result)


def run_auto_resolve_exact_matches(engine):
    """Auto-confirms any mismatch/placeholder player with exactly one
    candidate at a 1.00 similarity score (no tied runner-up)."""
    resolved, skipped = [], []

    with engine.connect() as conn:
        mismatch_player_ids = [r[0] for r in conn.execute(text(
            "SELECT DISTINCT player_id FROM nhl_player_name_mismatch WHERE resolved = false"
        )).fetchall()]
        placeholder_player_ids = [r[0] for r in conn.execute(text("""
            SELECT p.id FROM nhl_players p JOIN nhl_player_props pp ON pp.player_id = p.id
            WHERE p.espn_player_id IS NULL GROUP BY p.id HAVING COUNT(pp.id) > 0
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
                top_score = candidates[0]["similarity_score"] if candidates else 0
                runner_up_score = candidates[1]["similarity_score"] if len(candidates) > 1 else 0
                if top_score != 1.0 or runner_up_score == 1.0:
                    skipped.append({"player_id": player_id, "queue": queue_name, "odds_name": data.get("odds_name"),
                                     "reason": f"{len(candidates)} candidate(s)" if candidates else "no candidates"})
                    continue
                cand = candidates[0]
                result, error = do_resolve(engine, player_id, cand["espn_player_id"], cand["espn_display_name"])
                if error:
                    skipped.append({"player_id": player_id, "queue": queue_name, "reason": error[0]})
                    continue
                resolved.append({
                    "player_id": player_id, "queue": queue_name, "odds_name": data.get("odds_name"),
                    "espn_player_id": cand["espn_player_id"], "espn_name": cand["espn_display_name"],
                    "merged_into_player_id": result.get("merged_into_player_id") or result.get("merged_placeholder_id"),
                })
            except Exception as e:
                skipped.append({"player_id": player_id, "queue": queue_name, "reason": str(e)})

    return {"auto_resolved_count": len(resolved), "auto_resolved": resolved,
            "skipped_count": len(skipped), "skipped": skipped}


@nhl_mismatch_bp.route("/api/internal/nhl/auto-resolve-exact-matches", methods=["POST"])
def auto_resolve_exact_matches():
    return jsonify(run_auto_resolve_exact_matches(_get_engine()))
