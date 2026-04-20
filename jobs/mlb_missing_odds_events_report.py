#!/usr/bin/python3

import os
import sys
import pytz
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mlb_historical_player_odds_import import (
    get_historical_mlb_events,
    get_historical_player_odds,
    parse_historical_player_props,
    insert_historical_props_to_db,
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


def check_event_in_db(conn, event_id):
    """Returns (in_batter_props, in_pitcher_props) booleans."""
    batter_count = conn.execute(text(
        "SELECT COUNT(*) FROM mlb_batter_props WHERE odds_event_id = :eid"
    ), {'eid': event_id}).scalar()

    pitcher_count = conn.execute(text(
        "SELECT COUNT(*) FROM mlb_pitcher_props WHERE odds_event_id = :eid"
    ), {'eid': event_id}).scalar()

    print(f"  DB check {event_id}: batter_props={batter_count}, pitcher_props={pitcher_count}")
    return batter_count > 0, pitcher_count > 0


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 jobs/mlb_missing_odds_events_report.py START_DATE END_DATE")
        print("Example: python3 jobs/mlb_missing_odds_events_report.py 2025-07-01 2025-07-07")
        sys.exit(1)

    start_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    end_date = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
    eastern = pytz.timezone('US/Eastern')

    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    try:
        current_date = start_date
        missing_both = []
        missing_batters = []
        missing_pitchers = []

        while current_date <= end_date:
            events = get_historical_mlb_events(current_date)

            # Filter to events that actually fall on this date in ET
            filtered = []
            for event in events:
                commence_time = event.get('commence_time')
                if commence_time:
                    game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                    if game_start.astimezone(eastern).date() == current_date:
                        filtered.append(event)

            for event in filtered:
                event_id = event.get('id')
                if not event_id:
                    continue
                in_batters, in_pitchers = check_event_in_db(conn, event_id)
                info = {
                    'date': current_date,
                    'event_id': event_id,
                    'home_team': event.get('home_team'),
                    'away_team': event.get('away_team'),
                }
                if not in_batters and not in_pitchers:
                    missing_both.append(info)
                elif not in_batters:
                    missing_batters.append(info)
                elif not in_pitchers:
                    missing_pitchers.append(info)

            current_date += timedelta(days=1)

        # Report
        if not missing_both and not missing_batters and not missing_pitchers:
            print("All events found in both mlb_batter_props and mlb_pitcher_props.")
            return

        if missing_both:
            print(f"\nMissing from BOTH tables ({len(missing_both)} events):")
            for e in missing_both:
                print(f"  {e['date']} | {e['event_id']} | {e['away_team']} at {e['home_team']}")

        if missing_batters:
            print(f"\nMissing from mlb_batter_props only ({len(missing_batters)} events):")
            for e in missing_batters:
                print(f"  {e['date']} | {e['event_id']} | {e['away_team']} at {e['home_team']}")

        if missing_pitchers:
            print(f"\nMissing from mlb_pitcher_props only ({len(missing_pitchers)} events):")
            for e in missing_pitchers:
                print(f"  {e['date']} | {e['event_id']} | {e['away_team']} at {e['home_team']}")

        # Import missing events
        all_missing = missing_both + missing_batters + missing_pitchers
        if all_missing:
            print(f"\nImporting {len(all_missing)} missing event(s)...")
            for e in all_missing:
                event_id = e['event_id']
                event_date = e['date']
                print(f"\n  Fetching odds for {event_id} ({e['away_team']} at {e['home_team']})...")
                try:
                    odds_data = get_historical_player_odds(event_id, event_date)
                    if not odds_data:
                        print(f"  No odds data returned for {event_id}, skipping.")
                        continue
                    commence_time = odds_data.get('commence_time')
                    if not commence_time:
                        print(f"  No commence_time in odds data for {event_id}, skipping.")
                        continue
                    props_data = parse_historical_player_props(odds_data, commence_time)
                    if not props_data:
                        print(f"  No player props parsed for {event_id}.")
                        continue
                    inserted, errors = insert_historical_props_to_db(conn, props_data)
                    conn.commit()
                    print(f"  Inserted {inserted} props for {event_id}.")
                    if errors:
                        for name, err in errors:
                            print(f"    Skipped {name}: {err}")
                except Exception as ex:
                    print(f"  Error importing {event_id}: {ex}")
                    conn.rollback()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
