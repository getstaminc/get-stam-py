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
     "table": "nba_games_1", "date_col": "game_date", "league_filter": None},
    {"key": "nfl", "display": "NFL", "espn_slug": "football/nfl",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "nfl_games", "date_col": "game_date", "league_filter": None},
    {"key": "mlb", "display": "MLB", "espn_slug": "baseball/mlb",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "mlb_games", "date_col": "game_date", "league_filter": None},
    {"key": "nhl", "display": "NHL", "espn_slug": "hockey/nhl",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "nhl_games", "date_col": "game_date", "league_filter": None},
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


if __name__ == "__main__":
    run()
