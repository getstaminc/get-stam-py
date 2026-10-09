#!/usr/bin/python3
"""
Player Prop Mismatch Report

One-off email listing:
  1. Players whose odds-side name never confidently matched an ESPN player
     (the unresolved mismatch queue backing /internal/mismatch-players).
  2. Same-team players whose normalized names are similar enough that a
     future ESPN-search match could plausibly confuse one for the other.
Across MLB and NFL. Sent directly to the admin inbox, never to a Brevo list.

Usage:
    python jobs/send_player_mismatch_report.py
"""

import os
import sys
import itertools
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

import requests
from sqlalchemy import create_engine, text

from api.services.email_service import EmailService
from api.routes.internal.mlb_mismatch import score_candidate

ESPN_HEALTH_CHECK_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://www.getstam.com")
REPORT_RECIPIENT = "getstaminc@gmail.com"

# Same-team pairs scoring at or above this are similar enough to flag — picked
# from a one-off check that found 0 same-team MLB/NFL collisions at 0.75 (only
# differing by a single token, e.g. first name) but plenty of noise at 0.5
# (pairs sharing only a last name, which the real matcher never confuses).
SAME_TEAM_SIMILARITY_THRESHOLD = 0.75

SPORTS = [
    {
        "key": "mlb", "display": "MLB",
        "table": "mlb_player_name_mismatch", "players_table": "mlb_players",
        "prop_tables": ["mlb_batter_props", "mlb_pitcher_props"],
    },
    {
        "key": "nfl", "display": "NFL",
        "table": "nfl_player_name_mismatch", "players_table": "nfl_players",
        "prop_tables": ["nfl_player_props"],
    },
]


def _get_engine():
    return create_engine(DATABASE_URL)


def _check_espn_reachable():
    """One lightweight ESPN ping from wherever this job actually runs (a pulse
    check on the same dependency every other check in this report relies on).
    Checks status 200 AND that the body has the expected key, not just that
    *something* came back -- a block/challenge page can still return 200."""
    try:
        resp = requests.get(
            ESPN_HEALTH_CHECK_URL,
            params={"dates": date.today().strftime("%Y%m%d"), "limit": 5},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15,
        )
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        if "events" not in resp.json():
            return False, "200 OK but missing expected 'events' key (possible block/challenge page)"
        return True, None
    except Exception as e:
        return False, str(e)


def _fetch_mismatches(engine, table):
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT player_id, normalized_name, COUNT(*) AS total,
                   MIN(game_date) AS first_game, MAX(game_date) AS last_game
            FROM {table}
            WHERE resolved = false
            GROUP BY player_id, normalized_name
            ORDER BY total DESC, normalized_name
        """)).fetchall()
    return [
        {
            "player_id": r[0],
            "odds_name": r[1],
            "total": r[2],
            "first_game": r[3].isoformat() if r[3] else None,
            "last_game": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


def _fetch_same_team_collisions(engine, players_table):
    """Same-team players whose normalized names score >= threshold against each
    other — a blind spot for the team-level consistency check, since two such
    players would both legitimately belong to the team either way."""
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT p.id, p.normalized_name, p.espn_player_id, t.team_name
            FROM {players_table} p
            JOIN teams t ON t.team_id = p.team_id
            WHERE p.team_id IS NOT NULL
        """)).fetchall()

    by_team = {}
    for player_id, name, espn_id, team_name in rows:
        by_team.setdefault(team_name, []).append((player_id, name, espn_id))

    flagged = []
    for team_name, players in by_team.items():
        for (pid1, n1, e1), (pid2, n2, e2) in itertools.combinations(players, 2):
            s = score_candidate(n1, n2)
            if s >= SAME_TEAM_SIMILARITY_THRESHOLD:
                flagged.append({
                    "team_name": team_name,
                    "player_a": n1, "espn_id_a": e1,
                    "player_b": n2, "espn_id_b": e2,
                    "score": round(s, 2),
                })

    flagged.sort(key=lambda x: -x["score"])
    return flagged


def _fetch_team_consistency_issues(engine, prop_tables):
    """Rows where ESPN's per-game team assignment (player_team_id, set from that
    game's boxscore during actuals import) doesn't match either team in the
    odds-side game (odds_home_team_id / odds_away_team_id) — a free, zero-ESPN-call
    signal that we linked the wrong game or the wrong player to this row. Needs
    all three team-id columns populated to mean anything, so rows still missing
    actuals (player_team_id IS NULL) are out of scope here, not flagged."""
    flagged = []
    with engine.connect() as conn:
        for table in prop_tables:
            rows = conn.execute(text(f"""
                SELECT id, normalized_name, game_date,
                       player_team_name, odds_home_team, odds_away_team
                FROM {table}
                WHERE player_team_id IS NOT NULL
                  AND odds_home_team_id IS NOT NULL
                  AND odds_away_team_id IS NOT NULL
                  AND player_team_id NOT IN (odds_home_team_id, odds_away_team_id)
                ORDER BY game_date DESC
            """)).fetchall()
            for row_id, name, game_date, player_team, home, away in rows:
                flagged.append({
                    "table": table,
                    "row_id": row_id,
                    "name": name,
                    "game_date": game_date.isoformat() if game_date else None,
                    "player_team": player_team,
                    "odds_home_team": home,
                    "odds_away_team": away,
                })
    return flagged


def _fetch_missing_actuals_summary(engine, prop_tables):
    """Rows where ESPN never confirmed a team (player_team_id IS NULL, i.e. no
    actuals), broken into 'explained' (actuals_unavailable_reason set — e.g. the
    game was postponed/canceled, confirmed against ESPN, never recoverable
    under this date) vs 'unexplained' (still worth investigating). Only counts
    past games — future/in-progress games are expected to be missing actuals."""
    explained = {}
    unexplained_sample = []
    unexplained_total = 0
    with engine.connect() as conn:
        for table in prop_tables:
            for reason, count in conn.execute(text(f"""
                SELECT COALESCE(actuals_unavailable_reason, '(unexplained)'), COUNT(*)
                FROM {table}
                WHERE player_team_id IS NULL AND game_date < CURRENT_DATE
                GROUP BY 1
            """)).fetchall():
                if reason == "(unexplained)":
                    unexplained_total += count
                else:
                    explained[reason] = explained.get(reason, 0) + count

            unexplained_sample.extend(conn.execute(text(f"""
                SELECT normalized_name, game_date, odds_home_team, odds_away_team
                FROM {table}
                WHERE player_team_id IS NULL AND game_date < CURRENT_DATE
                  AND actuals_unavailable_reason IS NULL
                ORDER BY game_date DESC
                LIMIT 10
            """)).fetchall())

    return {
        "explained": explained,
        "unexplained_total": unexplained_total,
        "unexplained_sample": unexplained_sample[:10],
    }


def _build_html(results_by_sport, collisions_by_sport, team_issues_by_sport, missing_actuals_by_sport, espn_ok, espn_detail):
    if espn_ok:
        espn_banner = """
            <div style="padding:12px; background:#e6f4ea; border:1px solid #34a853; margin-bottom:16px;">
                ✅ ESPN reachable from this job's environment right now.
            </div>
        """
    else:
        espn_banner = f"""
            <div style="padding:12px; background:#fce8e6; border:1px solid #d93025; margin-bottom:16px;">
                ❌ ESPN is NOT reachable from this job's environment right now ({espn_detail}).
                Every check below that depends on ESPN access may be stale or incomplete until this is fixed.
            </div>
        """

    sections = []
    total_players = 0
    for sport in SPORTS:
        rows = results_by_sport[sport["key"]]
        total_players += len(rows)
        if not rows:
            sections.append(f"<h3>{sport['display']}</h3><p>No unresolved mismatches.</p>")
            continue
        table_rows = "".join(
            f"<tr><td>{r['odds_name']}</td><td>{r['total']}</td>"
            f"<td>{r['first_game']} &ndash; {r['last_game']}</td></tr>"
            for r in rows
        )
        sections.append(f"""
            <h3>{sport['display']} ({len(rows)} players)</h3>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Odds-side name</th><th>Affected rows</th><th>Date range</th></tr>
                {table_rows}
            </table>
        """)

    collision_sections = []
    total_collisions = 0
    for sport in SPORTS:
        pairs = collisions_by_sport[sport["key"]]
        total_collisions += len(pairs)
        if not pairs:
            collision_sections.append(f"<h3>{sport['display']}</h3><p>No same-team name collisions detected.</p>")
            continue
        pair_rows = "".join(
            f"<tr><td>{p['team_name']}</td><td>{p['player_a']} (espn={p['espn_id_a']})</td>"
            f"<td>{p['player_b']} (espn={p['espn_id_b']})</td><td>{p['score']}</td></tr>"
            for p in pairs
        )
        collision_sections.append(f"""
            <h3>{sport['display']} ({len(pairs)} pair(s))</h3>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Team</th><th>Player A</th><th>Player B</th><th>Similarity</th></tr>
                {pair_rows}
            </table>
        """)

    team_issue_sections = []
    total_team_issues = 0
    for sport in SPORTS:
        issues = team_issues_by_sport[sport["key"]]
        total_team_issues += len(issues)
        if not issues:
            team_issue_sections.append(f"<h3>{sport['display']}</h3><p>No team/game inconsistencies detected.</p>")
            continue
        issue_rows = "".join(
            f"<tr><td>{i['table']}#{i['row_id']}</td><td>{i['name']}</td><td>{i['game_date']}</td>"
            f"<td>{i['player_team']}</td><td>{i['odds_home_team']} vs {i['odds_away_team']}</td></tr>"
            for i in issues
        )
        team_issue_sections.append(f"""
            <h3>{sport['display']} ({len(issues)} row(s))</h3>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Row</th><th>Player</th><th>Game date</th><th>ESPN team</th><th>Odds-side matchup</th></tr>
                {issue_rows}
            </table>
        """)

    missing_sections = []
    total_unexplained = 0
    total_explained = 0
    for sport in SPORTS:
        summary = missing_actuals_by_sport[sport["key"]]
        total_unexplained += summary["unexplained_total"]
        total_explained += sum(summary["explained"].values())
        explained_str = ", ".join(f"{reason}: {count}" for reason, count in summary["explained"].items()) or "none"
        sample_rows = "".join(
            f"<tr><td>{name}</td><td>{gd}</td><td>{home} vs {away}</td></tr>"
            for name, gd, home, away in summary["unexplained_sample"]
        )
        sample_table = (
            f"""<table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Player</th><th>Game date</th><th>Odds-side matchup</th></tr>
                {sample_rows}
            </table>"""
            if sample_rows else "<p>None.</p>"
        )
        missing_sections.append(f"""
            <h3>{sport['display']}</h3>
            <p>Explained (game postponed/canceled — permanent, not actionable): {explained_str}</p>
            <p>Unexplained ({summary['unexplained_total']} total; showing up to 10 most recent):</p>
            {sample_table}
        """)

    body = "".join(sections)
    collision_body = "".join(collision_sections)
    team_issue_body = "".join(team_issue_sections)
    missing_body = "".join(missing_sections)
    link = f"{SITE_BASE_URL}/internal/mismatch-players"
    return f"""
        <div style="font-family: sans-serif;">
            {espn_banner}
            <h2>Player Prop Mismatch Report</h2>
            <p>{total_players} player(s) across MLB/NFL have an odds-side name that never
            confidently matched an ESPN player.</p>
            {body}
            <p>Review and resolve: <a href="{link}">{link}</a></p>

            <h2>Same-Team Similar-Name Check</h2>
            <p>{total_collisions} same-team pair(s) across MLB/NFL have normalized names
            similar enough that a future match could confuse one player for the other.</p>
            {collision_body}

            <h2>Team/Game Consistency Check</h2>
            <p>{total_team_issues} prop row(s) across MLB/NFL have an ESPN-confirmed player team
            that doesn't match either team in that row's odds-side game — a sign the wrong ESPN
            game or player was linked.</p>
            {team_issue_body}

            <h2>Missing Actuals</h2>
            <p>{total_explained} row(s) are explained (postponed/canceled games — permanent gaps),
            {total_unexplained} row(s) are still unexplained and worth investigating.</p>
            {missing_body}
        </div>
    """


def run():
    engine = _get_engine()
    results_by_sport = {}
    collisions_by_sport = {}
    team_issues_by_sport = {}
    missing_actuals_by_sport = {}

    espn_ok, espn_detail = _check_espn_reachable()
    print(f"[mismatch-report] ESPN reachable: {espn_ok}" + (f" ({espn_detail})" if espn_detail else ""))

    for sport in SPORTS:
        rows = _fetch_mismatches(engine, sport["table"])
        results_by_sport[sport["key"]] = rows
        print(f"[mismatch-report] {sport['display']}: {len(rows)} unresolved players")

        pairs = _fetch_same_team_collisions(engine, sport["players_table"])
        collisions_by_sport[sport["key"]] = pairs
        print(f"[mismatch-report] {sport['display']}: {len(pairs)} same-team name-collision pair(s)")

        issues = _fetch_team_consistency_issues(engine, sport["prop_tables"])
        team_issues_by_sport[sport["key"]] = issues
        print(f"[mismatch-report] {sport['display']}: {len(issues)} team/game consistency issue(s)")

        summary = _fetch_missing_actuals_summary(engine, sport["prop_tables"])
        missing_actuals_by_sport[sport["key"]] = summary
        print(f"[mismatch-report] {sport['display']}: {sum(summary['explained'].values())} explained, "
              f"{summary['unexplained_total']} unexplained missing-actuals row(s)")

    total = sum(len(v) for v in results_by_sport.values())
    subject_prefix = "" if espn_ok else "🚨 ESPN UNREACHABLE — "
    subject = f"{subject_prefix}Player Prop Mismatch Report — {total} player(s) need review"
    html = _build_html(results_by_sport, collisions_by_sport, team_issues_by_sport, missing_actuals_by_sport,
                        espn_ok, espn_detail)

    ok, err = EmailService.send_digest_to_one(REPORT_RECIPIENT, subject, html)
    if ok:
        print(f"[mismatch-report] Sent to {REPORT_RECIPIENT}")
    else:
        print(f"[mismatch-report] Failed to send: {err}")


if __name__ == "__main__":
    run()
