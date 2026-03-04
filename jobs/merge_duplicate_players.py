#!/usr/bin/python3
"""
NBA Player Merger Tool

This script merges duplicate NBA player records by moving all data from 
a "bad" player record to a "good" player record, then cleaning up duplicates.

Usage:
    python3 jobs/merge_duplicate_players.py <good_player_id> <bad_player_id>
    
Example:
    python3 jobs/merge_duplicate_players.py 436 559
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

def merge_players(good_player_id: int, bad_player_id: int):
    """
    Merge duplicate player records.
    
    Args:
        good_player_id: The correct player ID to keep
        bad_player_id: The duplicate player ID to remove
    """
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            print(f"🔄 Merging player records: {bad_player_id} → {good_player_id}")
            
            # Step 1: Get player info for confirmation
            good_player = conn.execute(text("""
                SELECT player_name, normalized_name FROM nba_players WHERE id = :id
            """), {'id': good_player_id}).fetchone()
            
            bad_player = conn.execute(text("""
                SELECT player_name, normalized_name FROM nba_players WHERE id = :id
            """), {'id': bad_player_id}).fetchone()
            
            if not good_player:
                print(f"❌ Error: Good player ID {good_player_id} not found!")
                return False
                
            if not bad_player:
                print(f"❌ Error: Bad player ID {bad_player_id} not found!")
                return False
                
            print(f"  Good player: {good_player[0]} (normalized: {good_player[1]})")
            print(f"  Bad player:  {bad_player[0]} (normalized: {bad_player[1]})")
            
            # Step 2: Update all nba_player_props records
            props_updated = conn.execute(text("""
                UPDATE nba_player_props 
                SET player_id = :good_id,
                    normalized_name = :good_normalized,
                    updated_at = NOW()
                WHERE player_id = :bad_id
            """), {
                'good_id': good_player_id,
                'good_normalized': good_player[1],
                'bad_id': bad_player_id
            })
            
            print(f"  ✅ Updated {props_updated.rowcount} player props records")
            
            # Step 3: Delete any existing aliases for the bad player FIRST
            aliases_deleted = conn.execute(text("""
                DELETE FROM nba_player_aliases WHERE player_id = :bad_id
            """), {'bad_id': bad_player_id})
            
            print(f"  ✅ Deleted {aliases_deleted.rowcount} aliases for bad player")
            
            # Step 4: Add aliases for the bad player's names to map to good player
            conn.execute(text("""
                INSERT INTO nba_player_aliases (player_id, source, source_name, normalized_name, created_at)
                VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
                ON CONFLICT (source, normalized_name) DO NOTHING
            """), {
                'player_id': good_player_id,
                'source_name': bad_player[0].lower(),
                'normalized_name': bad_player[1]
            })
            
            conn.execute(text("""
                INSERT INTO nba_player_aliases (player_id, source, source_name, normalized_name, created_at)
                VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
                ON CONFLICT (source, normalized_name) DO NOTHING
            """), {
                'player_id': good_player_id,
                'source_name': bad_player[0],
                'normalized_name': bad_player[1]
            })
            
            print(f"  ✅ Added aliases for '{bad_player[0]}' → player_id {good_player_id}")
            
            # Step 5: Mark any related mismatch records as resolved AND update player_id
            mismatches_updated = conn.execute(text("""
                UPDATE nba_player_name_mismatch 
                SET resolved = true,
                    player_id = :good_id
                WHERE player_id = :bad_id
            """), {'bad_id': bad_player_id, 'good_id': good_player_id})
            
            print(f"  ✅ Updated {mismatches_updated.rowcount} mismatch records to point to good player")
            
            # Step 6: Delete any remaining mismatch records that still reference bad player (just in case)
            remaining_mismatches = conn.execute(text("""
                DELETE FROM nba_player_name_mismatch 
                WHERE player_id = :bad_id
            """), {'bad_id': bad_player_id})
            
            if remaining_mismatches.rowcount > 0:
                print(f"  ✅ Deleted {remaining_mismatches.rowcount} remaining mismatch records")
            
            # Step 7: Delete the duplicate player record
            conn.execute(text("""
                DELETE FROM nba_players WHERE id = :bad_id
            """), {'bad_id': bad_player_id})
            
            print(f"  ✅ Deleted duplicate player record (ID: {bad_player_id})")
            
            # Commit all changes
            trans.commit()
            print(f"🎉 Successfully merged players! All data consolidated under player_id {good_player_id}")
            return True
            
    except Exception as e:
        print(f"❌ Error during merge: {e}")
        try:
            trans.rollback()
        except:
            pass  # Transaction might already be rolled back
        return False

def main():
    """Main function to handle command line arguments."""
    
    if len(sys.argv) != 3:
        print("❌ Usage: python3 jobs/merge_duplicate_players.py <good_player_id> <bad_player_id>")
        print("\nExample:")
        print("  python3 jobs/merge_duplicate_players.py 436 559")
        print("  (This merges player 559 into player 436)")
        sys.exit(1)
    
    try:
        good_player_id = int(sys.argv[1])
        bad_player_id = int(sys.argv[2])
    except ValueError:
        print("❌ Error: Player IDs must be integers")
        sys.exit(1)
    
    if good_player_id == bad_player_id:
        print("❌ Error: Good and bad player IDs cannot be the same")
        sys.exit(1)
    
    print("=" * 60)
    print("NBA Player Merger Tool")
    print("=" * 60)
    
    success = merge_players(good_player_id, bad_player_id)
    
    if success:
        print(f"\n✅ Merge completed successfully!")
        print(f"Player {bad_player_id} has been merged into player {good_player_id}")
    else:
        print(f"\n❌ Merge failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
