#!/usr/bin/python3
"""NHL Historical Data Import Orchestrator. Runs odds import then actuals
import for a date range. No-args invocation defaults to yesterday, which is
also what this file is intended to run as via Heroku Scheduler for ongoing
daily ingestion. No defense-props step -- NHL has no team D/ST market.

Usage:
    python3 jobs/nhl_historical_import_orchestrator_reverse.py
    python3 jobs/nhl_historical_import_orchestrator_reverse.py 2023-10-10
    python3 jobs/nhl_historical_import_orchestrator_reverse.py 2023-10-10 2026-10-20
"""
import sys
import os
from datetime import date, datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobs.nhl_historical_player_odds_import import import_historical_odds_date_range
from jobs.nhl_historical_player_actuals_import_reverse import import_historical_actuals_date_range_reverse


def parse_date(date_str: str) -> date:
    for fmt in ('%Y-%m-%d', '%Y%m%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date '{date_str}'")


def main():
    print("=" * 80)
    print("NHL Historical Data Import Orchestrator")
    print("=" * 80)

    if len(sys.argv) < 2:
        start_date = end_date = date.today() - timedelta(days=1)
        print(f"\nNo date provided - defaulting to yesterday: {start_date}")
    else:
        start_date = parse_date(sys.argv[1])
        end_date = parse_date(sys.argv[2]) if len(sys.argv) >= 3 else start_date

    if start_date > end_date:
        print(f"Error: start date ({start_date}) is after end date ({end_date})")
        sys.exit(1)

    print(f"\nImporting NHL player props for {start_date} to {end_date}")

    print("\n" + "=" * 80)
    print("STEP 1: Importing Historical Odds")
    print("=" * 80)
    try:
        import_historical_odds_date_range(start_date, end_date)
    except Exception as e:
        print(f"Error during odds import: {e}")
        print("Continuing with actuals import...")

    print("\n" + "=" * 80)
    print("STEP 2: Importing Historical Actuals")
    print("=" * 80)
    import_historical_actuals_date_range_reverse(start_date, end_date)

    print("\n" + "=" * 80)
    print("Historical Data Import Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
