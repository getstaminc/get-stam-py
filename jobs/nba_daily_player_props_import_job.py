#!/usr/bin/python3
"""
NBA Daily Data Import Job (For Heroku Scheduler)

This script runs the NBA historical odds and actuals import jobs for yesterday's date (or a date range).
It is designed to be scheduled (e.g., via Heroku Scheduler) to run daily at 4am ET, but can also be run manually for a date or date range.

Usage:
    python3 nba_daily_player_props_import_job.py           # Imports yesterday (ET)
    python3 nba_daily_player_props_import_job.py 2026-01-27
    python3 nba_daily_player_props_import_job.py 2026-01-20 2026-01-27
"""

import sys
import os
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import pytz

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the historical import functions
from jobs.nba_historical_player_odds_import import import_historical_odds_date_range
from jobs.nba_historical_player_actuals_import_reverse import import_historical_actuals_date_range_reverse

# Load environment variables
load_dotenv()

def parse_date(date_str: str) -> date:
    """
    Parse date string in various formats.
    """
    formats = [
        '%Y-%m-%d',      # 2023-06-12
        '%Y%m%d',        # 20230612
        '%m/%d/%Y',      # 06/12/2023
        '%m-%d-%Y',      # 06-12-2023
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date '{date_str}'. Supported formats: YYYY-MM-DD, YYYYMMDD, MM/DD/YYYY")

def get_yesterdays_date_et():
    eastern = pytz.timezone('US/Eastern')
    now_et = datetime.now(eastern)
    yesterday_et = now_et - timedelta(days=1)
    return yesterday_et.date()

def main():
    print("=" * 80)
    print("NBA Daily Data Import Job (Reverse/Optimized Approach)")
    print("=" * 80)

    # Parse command line arguments for date or date range
    if len(sys.argv) == 1:
        # Default: yesterday in ET
        start_date = end_date = get_yesterdays_date_et()
    elif len(sys.argv) == 2:
        start_date = end_date = parse_date(sys.argv[1])
    elif len(sys.argv) >= 3:
        start_date = parse_date(sys.argv[1])
        end_date = parse_date(sys.argv[2])
    else:
        print("Usage: python3 nba_daily_player_props_import_job.py [start_date] [end_date]")
        sys.exit(1)

    if start_date > end_date:
        print(f"\n❌ Error: Start date ({start_date}) is after end date ({end_date})")
        sys.exit(1)

    # Display import plan
    if start_date == end_date:
        print(f"\nImporting data for: {start_date}")
    else:
        days = (end_date - start_date).days + 1
        print(f"\nImporting data for: {start_date} to {end_date} ({days} days)")

    print("\nThis will:")
    print("  1. Import historical odds from Odds API (DraftKings)")
    print("  2. Import actual game stats from ESPN (using optimized reverse approach)")
    print("  3. Match players and update records in nba_player_props table")
    print("\n⚡ Performance Improvement:")
    print("  - Reverse approach queries database once per game instead of per player")
    print("  - Uses in-memory dictionary lookups for faster matching")

    # Confirm before proceeding (skip for Heroku, but keep for manual runs)
    if os.environ.get('HEROKU_SKIP_CONFIRM', '0') != '1':
        try:
            response = input("\nProceed with import? (y/n): ")
            if response.lower() not in ['y', 'yes']:
                print("Import cancelled.")
                sys.exit(0)
        except EOFError:
            # If running non-interactively, just continue
            pass

    print("\n" + "=" * 80)
    print("STEP 1: Importing Historical Odds")
    print("=" * 80)
    try:
        import_historical_odds_date_range(start_date, end_date)
        print("\n✅ Historical odds import completed successfully")
    except Exception as e:
        print(f"\n❌ Error during odds import: {e}")
        print("Continuing with actuals import...")

    print("\n" + "=" * 80)
    print("STEP 2: Importing Historical Actuals (Reverse Approach)")
    print("=" * 80)
    try:
        import_historical_actuals_date_range_reverse(start_date, end_date)
        print("\n✅ Historical actuals import completed successfully")
    except Exception as e:
        print(f"\n❌ Error during actuals import: {e}")
        raise

    print("\n" + "=" * 80)
    print("🎉 Daily Data Import Complete!")
    print("=" * 80)
    print(f"\nDate range: {start_date} to {end_date}")
    print("\nYou can now query the nba_player_props table for analysis.")
    print("Records include both odds and actual stats for players in games during this period.")

if __name__ == "__main__":
    main()
