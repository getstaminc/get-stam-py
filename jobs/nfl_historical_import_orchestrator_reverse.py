#!/usr/bin/python3
"""
NFL Historical Data Import Orchestrator (Reverse Approach)

This script coordinates the import of both historical odds and actual stats for a date range.
It runs the odds import first, then the actuals import using the reverse/optimized approach.

No-args invocation defaults to importing yesterday's games, which is also what this file
is intended to be run as (e.g. via Heroku Scheduler) for ongoing daily ingestion.

Usage:
    # Default: import yesterday's games (used by Heroku Scheduler)
    python3 nfl_historical_import_orchestrator_reverse.py

    # Import a specific date
    python3 nfl_historical_import_orchestrator_reverse.py 2025-10-05

    # Import a date range
    python3 nfl_historical_import_orchestrator_reverse.py 2025-10-01 2025-10-31

    # Import with different format
    python3 nfl_historical_import_orchestrator_reverse.py 20251005
"""

import sys
import os
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the historical import functions
from jobs.nfl_historical_player_odds_import import import_historical_odds_date_range
from jobs.nfl_historical_player_actuals_import_reverse import import_historical_actuals_date_range_reverse
from jobs.nfl_historical_defense_actuals_import_reverse import import_historical_defense_actuals_date_range_reverse

# Load environment variables
load_dotenv()


def parse_date(date_str: str) -> date:
    """
    Parse date string in various formats.

    Supports:
        - YYYY-MM-DD (e.g., 2025-10-05)
        - YYYYMMDD (e.g., 20251005)
        - MM/DD/YYYY (e.g., 10/05/2025)

    Args:
        date_str: Date string to parse

    Returns:
        date object

    Raises:
        ValueError: If date format is not recognized
    """
    formats = [
        '%Y-%m-%d',
        '%Y%m%d',
        '%m/%d/%Y',
        '%m-%d-%Y',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Could not parse date '{date_str}'. Supported formats: YYYY-MM-DD, YYYYMMDD, MM/DD/YYYY")


def main():
    """
    Main orchestrator function.
    Parses command line arguments and runs both historical imports using reverse approach.
    """
    print("=" * 80)
    print("NFL Historical Data Import Orchestrator (Reverse/Optimized Approach)")
    print("=" * 80)

    try:
        if len(sys.argv) < 2:
            start_date = date.today() - timedelta(days=1)
            end_date = start_date
            print(f"\nNo date provided — defaulting to yesterday: {start_date}")
        else:
            start_date = parse_date(sys.argv[1])
            end_date = parse_date(sys.argv[2]) if len(sys.argv) >= 3 else start_date

        if start_date > end_date:
            print(f"\n❌ Error: Start date ({start_date}) is after end date ({end_date})")
            sys.exit(1)

        if start_date == end_date:
            print(f"\nImporting data for: {start_date}")
        else:
            days = (end_date - start_date).days + 1
            print(f"\nImporting data for: {start_date} to {end_date} ({days} days)")

        print("\nThis will:")
        print("  1. Import historical odds from Odds API (DraftKings)")
        print("  2. Import actual game stats from ESPN (using optimized reverse approach)")
        print("  3. Match players and update records in nfl_player_props")
        print("  4. Import team D/ST actual stats from ESPN and update nfl_defense_props")

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
        print("STEP 3: Importing Historical Defense (D/ST) Actuals")
        print("=" * 80)

        try:
            import_historical_defense_actuals_date_range_reverse(start_date, end_date)
            print("\n✅ Historical defense actuals import completed successfully")
        except Exception as e:
            print(f"\n❌ Error during defense actuals import: {e}")
            raise

        print("\n" + "=" * 80)
        print("🎉 Historical Data Import Complete!")
        print("=" * 80)
        print(f"\nDate range: {start_date} to {end_date}")
        print("\nYou can now query nfl_player_props for analysis.")
        print("Records include both odds and actual stats for players in games during this period.")
        print("Team D/ST anytime-TD props (with actual stats) live in nfl_defense_props.")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
