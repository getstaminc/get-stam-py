#!/usr/bin/env python3
"""One-off backfill: correct nba_games_1.total for 2020-07-01 onward by
re-fetching the real pregame total from Odds API's historical odds, snapshot
~1 hour before each game's own commence_time (never a blanket per-day
snapshot -- proven to return drifted in-game numbers for games that already
tipped off). Odds API only, no ESPN. Safe to re-run; only ever UPDATEs a row
when a real matched total was found, never nulls anything out.

Usage:
    python3 jobs/backfill_nba_totals.py
    python3 jobs/backfill_nba_totals.py --start-date 2021-12-15 --end-date 2021-12-17
"""
import os
import sys
import time
import argparse
import requests
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text
import shared_utils

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

DEFAULT_START = "2020-07-01"


def get_day_schedule(date_str: str, retries=3, delay=2):
    """Historical events for date_str via a fixed daily anchor snapshot
    (18:00:00Z -- schedule data doesn't drift like odds do, so the anchor
    time only needs to be a stable point where the day's games are already
    on the schedule, not precisely timed). Returns list of
    {'id', 'commence_time', 'home_team', 'away_team'}."""
    url = "https://api.the-odds-api.com/v4/historical/sports/basketball_nba/events"
    params = {"apiKey": ODDS_API_KEY, "date": f"{date_str}T18:00:00Z"}
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json().get("data", [])
            return [
                {"id": e["id"], "commence_time": e["commence_time"],
                 "home_team": e["home_team"], "away_team": e["away_team"]}
                for e in data
            ]
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching schedule for {date_str} (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def get_odds_snapshot_for_commence_time(commence_time_iso: str, retries=3, delay=2):
    """Historical odds list at commence_time - 1 hour. Returns the raw list
    of game-odds dicts from the API (each with 'id', 'home_team',
    'away_team', 'bookmakers')."""
    commence_dt = datetime.fromisoformat(commence_time_iso.replace("Z", "+00:00"))
    snapshot_dt = commence_dt - timedelta(hours=1)
    snapshot_str = snapshot_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = "https://api.the-odds-api.com/v4/historical/sports/basketball_nba/odds"
    params = {
        "apiKey": ODDS_API_KEY, "regions": "us", "markets": "totals",
        "oddsFormat": "american", "date": snapshot_str,
    }
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching odds snapshot at {snapshot_str} (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def _market_from_preferred_bookmaker(bookmakers, market_key, preferred="draftkings"):
    preferred_bm = next((bm for bm in bookmakers if bm["key"] == preferred), None)
    if preferred_bm:
        market = next((m for m in preferred_bm.get("markets", []) if m["key"] == market_key), None)
        if market:
            return market
    for bm in bookmakers:
        market = next((m for m in bm.get("markets", []) if m["key"] == market_key), None)
        if market:
            return market
    return None


def parse_total(odds_game: dict):
    """Extract the totals market's point value, DraftKings-preferred with
    fallback. Returns None if no bookmaker has a totals market."""
    bookmakers = odds_game.get("bookmakers", [])
    if not bookmakers:
        return None
    totals = _market_from_preferred_bookmaker(bookmakers, "totals")
    if not totals:
        return None
    over = next((o for o in totals["outcomes"] if o["name"] == "Over"), None)
    return over.get("point") if over else None


def backfill_date_range(start_date: str, end_date: str):
    print(f"Starting NBA totals backfill: {start_date} to {end_date}")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    processed_days = 0
    updated = 0
    skipped_no_db_match = 0
    skipped_no_odds = 0

    current = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    try:
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            events = get_day_schedule(date_str)
            if events:
                # Group events by unique commence_time to share odds snapshots.
                by_commence_time = {}
                for e in events:
                    by_commence_time.setdefault(e["commence_time"], []).append(e)

                odds_by_event_id = {}
                for commence_time, group in by_commence_time.items():
                    snapshot_games = get_odds_snapshot_for_commence_time(commence_time)
                    for g in snapshot_games:
                        # The historical odds endpoint returns every game that's
                        # still active at the snapshot timestamp, not just games
                        # commencing at this group's own commence_time. Only keep
                        # entries for games whose own commence_time matches this
                        # group -- otherwise a later-processed group covering a
                        # different (often earlier) snapshot moment can clobber
                        # a game's correct ~1hr-before-its-own-tip line with a
                        # stale one, since dict iteration order follows the
                        # events list, not chronological snapshot order.
                        if g.get("commence_time") != commence_time:
                            continue
                        odds_by_event_id[g["id"]] = g
                    time.sleep(0.3)

                for e in events:
                    odds_game = odds_by_event_id.get(e["id"])
                    if not odds_game:
                        skipped_no_odds += 1
                        continue
                    new_total = parse_total(odds_game)
                    if new_total is None:
                        skipped_no_odds += 1
                        continue

                    db_home = shared_utils.convert_team_name(e["home_team"])
                    db_away = shared_utils.convert_team_name(e["away_team"])
                    row = conn.execute(text("""
                        SELECT game_id FROM nba_games_1
                        WHERE game_date = :game_date AND home_team_name = :home AND away_team_name = :away
                    """), {"game_date": date_str, "home": db_home, "away": db_away}).fetchone()

                    if not row:
                        skipped_no_db_match += 1
                        continue

                    conn.execute(text("""
                        UPDATE nba_games_1 SET total = :new_total WHERE game_id = :game_id
                    """), {"new_total": new_total, "game_id": row[0]})
                    updated += 1
                    print(f"  {date_str}: {db_away} @ {db_home} -> total={new_total}")

            conn.commit()
            processed_days += 1
            current += timedelta(days=1)
            time.sleep(0.3)

        print(f"\nDone. Days processed: {processed_days}")
        print(f"Rows updated: {updated}")
        print(f"Skipped (no DB match): {skipped_no_db_match}")
        print(f"Skipped (no odds found): {skipped_no_odds}")
    except Exception as e:
        print(f"Error during backfill: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(description="Backfill nba_games_1.total precision from Odds API")
    parser.add_argument("--start-date", default=DEFAULT_START, help="YYYY-MM-DD (default: 2020-07-01)")
    parser.add_argument("--end-date", default=yesterday, help="YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    backfill_date_range(args.start_date, args.end_date)
