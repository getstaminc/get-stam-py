#!/usr/bin/python3
"""
Backfill BetMGM batter_home_runs odds into existing mlb_batter_props records.

UPDATE-only: if no record exists for a player+event, it is skipped. No new rows
are inserted. Run for any date range where home_runs columns are NULL.

Usage:
    python jobs/mlb_betmgm_home_runs_backfill.py
    (adjust start_date / end_date at the bottom of the file)
"""

import os
import sys
import time
from datetime import date, datetime, timedelta

import pytz
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Allow importing from the project root when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobs.mlb_historical_player_odds_import import (
    get_historical_mlb_events,
    get_betmgm_home_run_odds,
    parse_historical_player_props,
    update_batter_home_runs_in_db,
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


def backfill_home_runs_for_date(target_date: date, conn) -> int:
    """
    Fetch BetMGM home run odds for every MLB event on target_date (ET) and
    update existing mlb_batter_props records. Returns number of rows updated.
    """
    print(f"\n=== Backfilling BetMGM home run odds for {target_date} ===")

    events = get_historical_mlb_events(target_date)
    if not events:
        print(f"  No events found for {target_date}")
        return 0

    eastern = pytz.timezone('US/Eastern')
    filtered_events = []
    for event in events:
        commence_time = event.get('commence_time')
        if commence_time:
            game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            game_start_et = game_start.astimezone(eastern)
            if game_start_et.date() == target_date:
                filtered_events.append(event)

    print(f"  Filtered to {len(filtered_events)} events on {target_date} ET (from {len(events)} total)")

    if not filtered_events:
        print(f"  No events match {target_date} after timezone conversion")
        return 0

    total_updated = 0

    for i, event in enumerate(filtered_events, 1):
        event_id = event.get('id')
        commence_time = event.get('commence_time')

        if not event_id or not commence_time:
            continue

        print(f"\n  Event {i}/{len(filtered_events)}: {event_id}")

        betmgm_data = get_betmgm_home_run_odds(event_id, target_date)
        if not betmgm_data:
            continue

        all_props = parse_historical_player_props(betmgm_data, commence_time, bookmaker_key='betmgm')
        hr_props = [p for p in all_props if p['market_key'] == 'batter_home_runs']

        if not hr_props:
            print(f"    No home run props found for event {event_id}")
            continue

        updated, errors = update_batter_home_runs_in_db(conn, hr_props)
        total_updated += updated
        print(f"    Updated {updated} home run records")

        if errors:
            for name, err in errors:
                print(f"    • {name}: {err}")

        if i < len(filtered_events):
            time.sleep(3)

    return total_updated


def backfill_home_runs_date_range(start_date: date, end_date: date):
    """
    Backfill BetMGM home run odds for all dates in [start_date, end_date].
    Commits after each date so partial progress is preserved.
    """
    print(f"=== BetMGM Home Runs Backfill ===")
    print(f"Date range: {start_date} to {end_date}")

    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    try:
        current_date = start_date
        grand_total = 0

        while current_date <= end_date:
            try:
                daily_updated = backfill_home_runs_for_date(current_date, conn)
                grand_total += daily_updated
                conn.commit()
                print(f"✅ Committed home run updates for {current_date} ({daily_updated} rows)")
            except Exception as e:
                print(f"❌ Error processing {current_date}: {e}")
                conn.rollback()

            current_date += timedelta(days=1)

            if current_date <= end_date:
                time.sleep(5)

        print(f"\n🎉 Backfill complete! Total rows updated: {grand_total}")
        print(f"Date range: {start_date} to {end_date}")

    except Exception as e:
        print(f"❌ Fatal error during backfill: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        start_date = date.fromisoformat(sys.argv[1])
        end_date = date.fromisoformat(sys.argv[2])
    elif len(sys.argv) == 2:
        start_date = end_date = date.fromisoformat(sys.argv[1])
    else:
        start_date = date(2026, 5, 1)
        end_date = date(2026, 5, 2)

    backfill_home_runs_date_range(start_date, end_date)
