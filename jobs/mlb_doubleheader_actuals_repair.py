#!/usr/bin/python3
"""
MLB Doubleheader Actuals Repair

Finds all doubleheader records (same player, date, and teams appearing more than once),
nulls out their actuals, and re-imports ESPN actuals for each affected date.

Usage:
    python3 mlb_doubleheader_actuals_repair.py           # dry run (shows affected dates)
    python3 mlb_doubleheader_actuals_repair.py --fix     # null out + re-import actuals
"""

import os
import sys
import time
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobs.mlb_historical_player_actuals_import_reverse import import_historical_actuals_for_date_reverse

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


def find_doubleheader_dates(conn) -> list[date]:
    """Return sorted list of distinct dates that have doubleheader batter or pitcher records."""
    batter_dates = conn.execute(text("""
        SELECT DISTINCT game_date
        FROM mlb_batter_props
        WHERE (game_date, normalized_name, odds_home_team_id, odds_away_team_id) IN (
            SELECT game_date, normalized_name, odds_home_team_id, odds_away_team_id
            FROM mlb_batter_props
            GROUP BY game_date, normalized_name, odds_home_team_id, odds_away_team_id
            HAVING COUNT(*) > 1
        )
    """)).fetchall()

    pitcher_dates = conn.execute(text("""
        SELECT DISTINCT game_date
        FROM mlb_pitcher_props
        WHERE (game_date, normalized_name, odds_home_team_id, odds_away_team_id) IN (
            SELECT game_date, normalized_name, odds_home_team_id, odds_away_team_id
            FROM mlb_pitcher_props
            GROUP BY game_date, normalized_name, odds_home_team_id, odds_away_team_id
            HAVING COUNT(*) > 1
        )
    """)).fetchall()

    all_dates = set(row[0] for row in batter_dates) | set(row[0] for row in pitcher_dates)
    return sorted(all_dates)


def null_doubleheader_actuals(conn):
    """Null out actuals for all doubleheader batter and pitcher records."""
    batter_result = conn.execute(text("""
        UPDATE mlb_batter_props
        SET actual_batter_hits = NULL,
            actual_batter_home_runs = NULL,
            actual_batter_rbi = NULL,
            actual_batter_runs_scored = NULL,
            actual_batter_at_bats = NULL,
            actual_batter_walks = NULL,
            actual_batter_strikeouts = NULL,
            espn_event_id = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE (game_date, normalized_name, odds_home_team_id, odds_away_team_id) IN (
            SELECT game_date, normalized_name, odds_home_team_id, odds_away_team_id
            FROM mlb_batter_props
            GROUP BY game_date, normalized_name, odds_home_team_id, odds_away_team_id
            HAVING COUNT(*) > 1
        )
    """))

    pitcher_result = conn.execute(text("""
        UPDATE mlb_pitcher_props
        SET actual_pitcher_strikeouts = NULL,
            actual_pitcher_earned_runs = NULL,
            actual_pitcher_hits_allowed = NULL,
            actual_pitcher_walks = NULL,
            actual_pitcher_innings_pitched = NULL,
            espn_event_id = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE (game_date, normalized_name, odds_home_team_id, odds_away_team_id) IN (
            SELECT game_date, normalized_name, odds_home_team_id, odds_away_team_id
            FROM mlb_pitcher_props
            GROUP BY game_date, normalized_name, odds_home_team_id, odds_away_team_id
            HAVING COUNT(*) > 1
        )
    """))

    conn.commit()
    print(f"  Nulled {batter_result.rowcount} batter records and {pitcher_result.rowcount} pitcher records")


def main():
    dry_run = '--fix' not in sys.argv

    print("=" * 80)
    print("MLB Doubleheader Actuals Repair")
    print("=" * 80)

    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    try:
        print("\nFinding doubleheader dates...")
        dates = find_doubleheader_dates(conn)

        if not dates:
            print("✅ No doubleheader records found — nothing to repair.")
            return

        print(f"\nFound {len(dates)} date(s) with doubleheader records:")
        for d in dates:
            print(f"  {d}")

        if dry_run:
            print("\n⚠️  Dry run — pass --fix to null actuals and re-import.")
            return

        print("\n--- Step 1: Nulling out doubleheader actuals ---")
        null_doubleheader_actuals(conn)

        print("\n--- Step 2: Re-importing actuals for each date ---")
        total_updated = 0

        for i, target_date in enumerate(dates, 1):
            print(f"\n[{i}/{len(dates)}] Processing {target_date}")
            try:
                updated = import_historical_actuals_for_date_reverse(target_date, conn)
                total_updated += updated
                conn.commit()
                print(f"  ✅ Committed {updated} records for {target_date}")
            except Exception as e:
                print(f"  ❌ Error on {target_date}: {e}")
                conn.rollback()

            if i < len(dates):
                time.sleep(3)

        print("\n" + "=" * 80)
        print(f"🎉 Repair complete — {total_updated} total records updated across {len(dates)} date(s)")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
