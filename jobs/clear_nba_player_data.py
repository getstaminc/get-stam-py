#!/usr/bin/env python3
"""
Clear all NBA player data and reset sequences.

WARNING: This will permanently delete all records from:
- nba_player_name_mismatch
- nba_player_props
- nba_player_aliases
- nba_players

And reset all ID sequences to 1.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")


def clear_nba_player_data():
    """Clear all NBA player data and reset sequences."""
    print("=" * 60)
    print("WARNING: About to delete ALL NBA player data")
    print("=" * 60)
    print("\nThis will delete records from:")
    print("  - nba_player_name_mismatch")
    print("  - nba_player_props")
    print("  - nba_player_aliases")
    print("  - nba_players")
    print("\nAnd reset all ID sequences to 1.")
    print()
    
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    print("\nConnecting to database...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Delete child records first (foreign key constraints)
        print("\n1. Deleting nba_player_name_mismatch records...")
        result = conn.execute(text("DELETE FROM nba_player_name_mismatch"))
        conn.commit()
        print(f"   ✓ Deleted {result.rowcount} mismatch records")
        
        print("\n2. Deleting nba_player_props records...")
        result = conn.execute(text("DELETE FROM nba_player_props"))
        conn.commit()
        print(f"   ✓ Deleted {result.rowcount} player props records")
        
        print("\n3. Deleting nba_player_aliases records...")
        result = conn.execute(text("DELETE FROM nba_player_aliases"))
        conn.commit()
        print(f"   ✓ Deleted {result.rowcount} player alias records")
        
        # Delete parent records
        print("\n4. Deleting nba_players records...")
        result = conn.execute(text("DELETE FROM nba_players"))
        conn.commit()
        print(f"   ✓ Deleted {result.rowcount} player records")
        
        # Reset sequences
        print("\n5. Resetting sequences...")
        conn.execute(text("ALTER SEQUENCE nba_player_name_mismatch_id_seq RESTART WITH 1"))
        conn.execute(text("ALTER SEQUENCE nba_player_props_id_seq RESTART WITH 1"))
        conn.execute(text("ALTER SEQUENCE nba_player_aliases_id_seq RESTART WITH 1"))
        conn.execute(text("ALTER SEQUENCE nba_players_id_seq RESTART WITH 1"))
        conn.commit()
        print("   ✓ All sequences reset to 1")
        
        print("\n" + "=" * 60)
        print("✅ Successfully cleared all NBA player data")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    clear_nba_player_data()
