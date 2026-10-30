#!/usr/bin/python3
"""
Daily Data Integrity Report
Compares yesterday's final games (ESPN) against our DB row counts, and
flags player-prop completeness gaps for NBA/NFL/MLB/NHL.
Runs every morning via Heroku Scheduler, after the nightly seed jobs:
  python jobs/send_data_integrity_report.py
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

import requests
from sqlalchemy import create_engine, text

from api.services.email_service import EmailService

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
REPORT_RECIPIENT = "getstaminc@gmail.com"
ESPN_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Each entry: espn_slug + espn_final_statuses identify how to ask ESPN "what
# finished yesterday"; table/date_col/league_filter identify how to count
# our own rows for the same day. prop_tables is added in Task 2 — sports
# without a props pipeline simply never get that key.
SPORTS_CONFIG = [
    {"key": "nba", "display": "NBA", "espn_slug": "basketball/nba",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "nba_games_1", "date_col": "game_date", "league_filter": None,
     "prop_check": {"mode": "team_id_join", "games_table": "nba_games_1",
                    "prop_tables": ["nba_player_props"]}},
    {"key": "nfl", "display": "NFL", "espn_slug": "football/nfl",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "nfl_games", "date_col": "game_date", "league_filter": None,
     "prop_check": {"mode": "team_id_join", "games_table": "nfl_games",
                    "prop_tables": ["nfl_player_props"]}},
    {"key": "mlb", "display": "MLB", "espn_slug": "baseball/mlb",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "mlb_games", "date_col": "game_date", "league_filter": None,
     "prop_check": {"mode": "event_id_join", "games_table": "mlb_games",
                    "prop_tables": ["mlb_batter_props", "mlb_pitcher_props"]}},
    {"key": "nhl", "display": "NHL", "espn_slug": "hockey/nhl",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "nhl_games", "date_col": "game_date", "league_filter": None,
     "prop_check": {"mode": "event_id_join", "games_table": "nhl_games",
                    "prop_tables": ["nhl_player_props"]}},
    {"key": "ncaaf", "display": "NCAAF", "espn_slug": "football/college-football",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "ncaaf_games", "date_col": "game_date", "league_filter": None},
    {"key": "ncaab", "display": "NCAAB", "espn_slug": "basketball/mens-college-basketball",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {"groups": 50},
     "table": "ncaab_games", "date_col": "game_date", "league_filter": None},
    {"key": "epl", "display": "EPL", "espn_slug": "soccer/eng.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "EPL"},
    {"key": "laliga", "display": "La Liga", "espn_slug": "soccer/esp.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "LA LIGA"},
    {"key": "bundesliga", "display": "Bundesliga", "espn_slug": "soccer/ger.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "BUNDESLIGA"},
    {"key": "ligue1", "display": "Ligue 1", "espn_slug": "soccer/fra.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "LIGUE 1"},
    {"key": "seriea", "display": "Serie A", "espn_slug": "soccer/ita.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "SERIE A"},
    {"key": "ucl", "display": "UCL", "espn_slug": "soccer/uefa.champions",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "UCL"},
]


def _get_engine():
    return create_engine(DATABASE_URL)


def _fetch_espn_final_games(slug, date_str, final_statuses, extra_params=None):
    """Return list of {'espn_id','home','away','status'} for events ESPN
    reports as finished on date_str (YYYYMMDD) for the given sport slug."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard"
    params = {"dates": date_str, "limit": 100}
    if extra_params:
        params.update(extra_params)
    resp = requests.get(url, headers=ESPN_HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    events = resp.json().get("events", [])

    finals = []
    for event in events:
        status = event.get("status", {}).get("type", {}).get("name", "")
        if status not in final_statuses:
            continue
        competitors = event.get("competitions", [{}])[0].get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        finals.append({
            "espn_id": event.get("id"),
            "home": home.get("team", {}).get("displayName", "?"),
            "away": away.get("team", {}).get("displayName", "?"),
            "status": status,
        })
    return finals


def _get_db_game_count(engine, table, date_col, date_obj, league_filter=None):
    sql = f"SELECT COUNT(*) FROM {table} WHERE {date_col} = :d"
    params = {"d": date_obj}
    if league_filter is not None:
        sql += " AND league = :league"
        params["league"] = league_filter
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def _check_games_count(engine, cfg, target_date, date_str):
    espn_games = _fetch_espn_final_games(
        cfg["espn_slug"], date_str, cfg["espn_final_statuses"], cfg["espn_extra_params"]
    )
    db_count = _get_db_game_count(engine, cfg["table"], cfg["date_col"], target_date, cfg["league_filter"])
    return {
        "sport": cfg["display"],
        "espn_count": len(espn_games),
        "db_count": db_count,
        "mismatch": len(espn_games) != db_count,
        "espn_games": espn_games,
    }


def _check_prop_completeness(engine, cfg, target_date):
    """For each DB game on target_date, check whether ANY row exists in
    every configured prop table for that game. Returns games with zero
    prop rows in at least one required table."""
    prop_cfg = cfg.get("prop_check")
    if not prop_cfg:
        return {"sport": cfg["display"], "applicable": False, "missing_games": []}

    missing_games = []
    with engine.connect() as conn:
        if prop_cfg["mode"] == "event_id_join":
            rows = conn.execute(text(f"""
                SELECT odds_event_id, home_team_name, away_team_name
                FROM {prop_cfg['games_table']}
                WHERE game_date = :d AND odds_event_id IS NOT NULL
            """), {"d": target_date}).fetchall()
            for event_id, home, away in rows:
                for prop_table in prop_cfg["prop_tables"]:
                    count = conn.execute(text(
                        f"SELECT COUNT(*) FROM {prop_table} WHERE odds_event_id = :eid"
                    ), {"eid": event_id}).scalar()
                    if count == 0:
                        missing_games.append({
                            "home": home, "away": away, "missing_table": prop_table,
                        })

        elif prop_cfg["mode"] == "team_id_join":
            rows = conn.execute(text(f"""
                SELECT home_team_id, away_team_id, home_team_name, away_team_name
                FROM {prop_cfg['games_table']}
                WHERE game_date = :d
            """), {"d": target_date}).fetchall()
            for home_id, away_id, home_name, away_name in rows:
                for prop_table in prop_cfg["prop_tables"]:
                    count = conn.execute(text(f"""
                        SELECT COUNT(*) FROM {prop_table}
                        WHERE game_date = :d AND odds_home_team_id = :hid AND odds_away_team_id = :aid
                    """), {"d": target_date, "hid": home_id, "aid": away_id}).scalar()
                    if count == 0:
                        missing_games.append({
                            "home": home_name, "away": away_name, "missing_table": prop_table,
                        })

    return {"sport": cfg["display"], "applicable": True, "missing_games": missing_games}


def _build_html(games_results, prop_results, target_date):
    games_rows = "".join(
        f"<tr><td>{r['sport']}</td>"
        f"<td>{r['espn_count'] if r['espn_count'] is not None else 'ERROR'}</td>"
        f"<td>{r['db_count'] if r['db_count'] is not None else 'ERROR'}</td>"
        f"<td style=\"color:{'#d93025' if r['mismatch'] else '#188038'}\">"
        f"{'MISMATCH' if r['mismatch'] else 'ok'}</td></tr>"
        for r in games_results
    )

    mismatch_detail_sections = []
    for r in games_results:
        if not r["mismatch"] or not r.get("espn_games"):
            continue
        game_rows = "".join(
            f"<li>{g['away']} @ {g['home']} (ESPN id {g['espn_id']}, status {g['status']})</li>"
            for g in r["espn_games"]
        )
        mismatch_detail_sections.append(f"""
            <h4>{r['sport']} — ESPN's finished games for {target_date}</h4>
            <ul>{game_rows}</ul>
        """)

    prop_sections = []
    total_missing = 0
    for r in prop_results:
        if not r["applicable"]:
            continue
        if r.get("error"):
            prop_sections.append(f"<h4>{r['sport']}</h4><p style=\"color:#d93025\">⚠️ Check failed: {r['error']}</p>")
            continue
        missing = r["missing_games"]
        total_missing += len(missing)
        if not missing:
            prop_sections.append(f"<h4>{r['sport']}</h4><p>All games have prop rows in every required table.</p>")
            continue
        rows = "".join(
            f"<tr><td>{m['away']} @ {m['home']}</td><td>{m['missing_table']}</td></tr>"
            for m in missing
        )
        prop_sections.append(f"""
            <h4>{r['sport']} ({len(missing)} gap(s))</h4>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Game</th><th>Missing from</th></tr>
                {rows}
            </table>
        """)

    return f"""
        <div style="font-family: sans-serif;">
            <h2>Data Integrity Report — {target_date}</h2>

            <h3>Games Count (ESPN vs. DB)</h3>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Sport</th><th>ESPN finished</th><th>In our DB</th><th>Status</th></tr>
                {games_rows}
            </table>
            {''.join(mismatch_detail_sections)}

            <h3>Player Props Completeness ({total_missing} gap(s) across NBA/NFL/MLB/NHL)</h3>
            {''.join(prop_sections)}
        </div>
    """


def run():
    target_date = date.today() - timedelta(days=1)
    date_str = target_date.strftime("%Y%m%d")
    print(f"[integrity-report] Checking games for {target_date}")

    engine = _get_engine()
    games_results = []
    for cfg in SPORTS_CONFIG:
        try:
            result = _check_games_count(engine, cfg, target_date, date_str)
            games_results.append(result)
            print(f"[integrity-report] {cfg['display']}: ESPN={result['espn_count']} DB={result['db_count']} "
                  f"{'MISMATCH' if result['mismatch'] else 'ok'}")
        except Exception as e:
            print(f"[integrity-report] {cfg['display']} error (non-fatal): {e}")
            games_results.append({
                "sport": cfg["display"], "espn_count": None, "db_count": None,
                "mismatch": True, "espn_games": [], "error": str(e),
            })

    total_mismatches = sum(1 for r in games_results if r["mismatch"])
    print(f"[integrity-report] {total_mismatches} sport(s) with a games-count mismatch")

    prop_results = []
    for cfg in SPORTS_CONFIG:
        try:
            result = _check_prop_completeness(engine, cfg, target_date)
            prop_results.append(result)
            if result["applicable"]:
                print(f"[integrity-report] {cfg['display']} props: {len(result['missing_games'])} gap(s)")
        except Exception as e:
            print(f"[integrity-report] {cfg['display']} prop-check error (non-fatal): {e}")
            prop_results.append({"sport": cfg["display"], "applicable": True, "missing_games": [],
                                  "error": str(e)})

    total_prop_gaps = sum(len(r["missing_games"]) for r in prop_results if r["applicable"])
    total_prop_errors = sum(1 for r in prop_results if r.get("error"))
    subject_prefix = "🚨 " if (total_mismatches or total_prop_gaps or total_prop_errors) else ""
    subject = (f"{subject_prefix}Data Integrity Report {target_date} — "
               f"{total_mismatches} games mismatch(es), {total_prop_gaps} prop gap(s)")
    html = _build_html(games_results, prop_results, target_date)

    ok, err = EmailService.send_digest_to_one(REPORT_RECIPIENT, subject, html)
    if ok:
        print(f"[integrity-report] Sent to {REPORT_RECIPIENT}")
    else:
        print(f"[integrity-report] Failed to send: {err}")


if __name__ == "__main__":
    run()
