#!/usr/bin/python3
"""
Backfill actuals_unavailable_reason for MLB Prop Rows

Finds (game_date, odds_home_team, odds_away_team) matchups where every prop
row is missing player_team_id -- the signature of a game whose boxscore never
came through -- and checks ESPN's scoreboard for that date to see why. When
the game was postponed or canceled, actuals for it can never be filled in
under this date, so this labels the rows accordingly instead of leaving them
looking like an open, unexplained gap.

Usage:
    python jobs/backfill_postponed_game_reason.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(override=True)

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

PROP_TABLES = ["mlb_batter_props", "mlb_pitcher_props"]

REASON_BY_STATUS = {
    "STATUS_POSTPONED": "postponed",
    "STATUS_CANCELED": "canceled",
}


def _get_engine():
    return create_engine(DATABASE_URL)


def _find_whole_game_gaps(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT game_date, odds_home_team, odds_away_team
            FROM mlb_batter_props
            WHERE game_date < CURRENT_DATE
              AND actuals_unavailable_reason IS NULL
            GROUP BY game_date, odds_home_team, odds_away_team
            HAVING COUNT(*) = COUNT(*) FILTER (WHERE player_team_id IS NULL)
        """)).fetchall()
    return rows


def _espn_game_status(game_date, home_team, away_team):
    """Returns ESPN's status name for this matchup on this date (e.g.
    'STATUS_POSTPONED'), or None if no matching event is found that day."""
    date_str = game_date.strftime("%Y%m%d")
    resp = requests.get(
        ESPN_SCOREBOARD_URL,
        params={"dates": date_str, "limit": 50},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        teams = {c.get("team", {}).get("displayName") for c in comp.get("competitors", [])}
        if {home_team, away_team} == teams:
            return comp.get("status", {}).get("type", {}).get("name")
    return None


def run():
    engine = _get_engine()
    gaps = _find_whole_game_gaps(engine)
    print(f"[postponed-backfill] {len(gaps)} whole-game gap(s) to check")

    labeled = 0
    unresolved = []
    for game_date, home, away in gaps:
        status = _espn_game_status(game_date, home, away)
        time.sleep(0.2)
        reason = REASON_BY_STATUS.get(status)
        if not reason:
            unresolved.append((game_date, home, away, status))
            print(f"  ? {game_date} {away} @ {home}: status={status} -- leaving unlabeled")
            continue

        with engine.connect() as conn:
            for table in PROP_TABLES:
                conn.execute(text(f"""
                    UPDATE {table}
                    SET actuals_unavailable_reason = :reason
                    WHERE game_date = :game_date
                      AND odds_home_team = :home AND odds_away_team = :away
                      AND player_team_id IS NULL
                """), {"reason": reason, "game_date": game_date, "home": home, "away": away})
            conn.commit()
        labeled += 1
        print(f"  ✅ {game_date} {away} @ {home}: {reason}")

    print(f"[postponed-backfill] Labeled {labeled} game(s). {len(unresolved)} unresolved.")
    for game_date, home, away, status in unresolved:
        print(f"  UNRESOLVED: {game_date} {away} @ {home} status={status}")


if __name__ == "__main__":
    run()
