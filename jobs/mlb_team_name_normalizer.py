#!/usr/bin/python3
"""
MLB Team Name Normalizer

This script normalizes team names from Odds API to match our internal team records.
Handles cases like "Athletics" vs "Oakland Athletics" and other team name variations.

Usage:
    python3 mlb_team_name_normalizer.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


def get_team_name_mapping():
    """
    Define mapping from Odds API team names to our database team names.
    Add new mappings here as needed.
    """
    return {
        # Athletics variations
        'Athletics': 'Oakland Athletics',
        'Oakland Athletics': 'Oakland Athletics',
        'A\'s': 'Oakland Athletics',
        
        # Add other common variations here
        'Guardians': 'Cleveland Guardians',
        'Cleveland Guardians': 'Cleveland Guardians',
        
        'D-backs': 'Arizona Diamondbacks', 
        'Diamondbacks': 'Arizona Diamondbacks',
        'Arizona Diamondbacks': 'Arizona Diamondbacks',
        
        'Red Sox': 'Boston Red Sox',
        'Boston Red Sox': 'Boston Red Sox',
        
        'Blue Jays': 'Toronto Blue Jays',
        'Toronto Blue Jays': 'Toronto Blue Jays',
        
        'White Sox': 'Chicago White Sox',
        'Chicago White Sox': 'Chicago White Sox',
    }


def normalize_team_name(odds_api_name: str) -> str:
    """
    Normalize an Odds API team name to our database format.
    
    Args:
        odds_api_name: Team name from Odds API
        
    Returns:
        Normalized team name that should match our database
    """
    name_mapping = get_team_name_mapping()
    return name_mapping.get(odds_api_name, odds_api_name)


def find_team_by_name(conn, team_name: str) -> tuple:
    """
    Find team record by name with fallback search strategies.
    
    Returns:
        (team_id, canonical_team_name) or (None, None) if not found
    """
    # Strategy 1: Exact match
    result = conn.execute(text("""
        SELECT team_id, team_name FROM teams 
        WHERE team_name = :team_name AND sport = 'MLB'
    """), {'team_name': team_name}).fetchone()
    
    if result:
        return result[0], result[1]
    
    # Strategy 2: Try normalized version
    normalized_name = normalize_team_name(team_name)
    if normalized_name != team_name:
        result = conn.execute(text("""
            SELECT team_id, team_name FROM teams 
            WHERE team_name = :team_name AND sport = 'MLB'
        """), {'team_name': normalized_name}).fetchone()
        
        if result:
            print(f"    🔧 Found via normalization: '{team_name}' → '{normalized_name}'")
            return result[0], result[1]
    
    # Strategy 3: Partial match (contains search)
    like_pattern = f"%{team_name.split()[-1]}%"  # Use last word for matching
    result = conn.execute(text("""
        SELECT team_id, team_name FROM teams 
        WHERE team_name ILIKE :pattern AND sport = 'MLB'
        LIMIT 1
    """), {'pattern': like_pattern}).fetchone()
    
    if result:
        print(f"    🔍 Found via partial match: '{team_name}' → '{result[1]}'")
        return result[0], result[1]
    
    return None, None


def update_prop_records_with_normalized_teams():
    """
    Update batter and pitcher prop records with properly resolved team names and IDs.
    """
    print("=" * 80)
    print("MLB Team Name Normalizer")
    print("=" * 80)
    
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Get all unique team name combinations that need resolution
        print("\n=== Analyzing team name issues ===")
        
        unresolved_teams = conn.execute(text("""
            WITH unresolved_batter_teams AS (
                SELECT DISTINCT odds_home_team, odds_away_team
                FROM mlb_batter_props
                WHERE odds_home_team_id IS NULL OR odds_away_team_id IS NULL
            ),
            unresolved_pitcher_teams AS (
                SELECT DISTINCT odds_home_team, odds_away_team  
                FROM mlb_pitcher_props
                WHERE odds_home_team_id IS NULL OR odds_away_team_id IS NULL
            )
            SELECT DISTINCT unnest(ARRAY[odds_home_team, odds_away_team]) as team_name
            FROM (
                SELECT * FROM unresolved_batter_teams
                UNION
                SELECT * FROM unresolved_pitcher_teams
            ) combined
            WHERE unnest(ARRAY[odds_home_team, odds_away_team]) IS NOT NULL
            ORDER BY team_name
        """)).fetchall()
        
        if not unresolved_teams:
            print("✅ No unresolved team names found!")
            return
        
        print(f"Found {len(unresolved_teams)} unique team names needing resolution:")
        
        team_resolution_map = {}
        
        for team_row in unresolved_teams:
            team_name = team_row[0]
            print(f"\n🔍 Resolving: '{team_name}'")
            
            team_id, canonical_name = find_team_by_name(conn, team_name)
            
            if team_id:
                team_resolution_map[team_name] = {'id': team_id, 'name': canonical_name}
                print(f"    ✅ Resolved to: {canonical_name} (ID: {team_id})")
            else:
                print(f"    ❌ Could not resolve: '{team_name}'")
                # Log for manual review
                team_resolution_map[team_name] = None
        
        # Update batter props
        print(f"\n=== Updating batter prop records ===")
        batter_updates = 0
        
        for odds_team_name, resolution in team_resolution_map.items():
            if resolution is None:
                continue
                
            team_id = resolution['id']
            canonical_name = resolution['name']
            
            # Update home team references
            result = conn.execute(text("""
                UPDATE mlb_batter_props
                SET odds_home_team_id = :team_id,
                    odds_home_team = :canonical_name
                WHERE odds_home_team = :odds_team_name
                AND odds_home_team_id IS NULL
            """), {
                'team_id': team_id,
                'canonical_name': canonical_name,
                'odds_team_name': odds_team_name
            })
            batter_updates += result.rowcount
            
            # Update away team references  
            result = conn.execute(text("""
                UPDATE mlb_batter_props
                SET odds_away_team_id = :team_id,
                    odds_away_team = :canonical_name
                WHERE odds_away_team = :odds_team_name
                AND odds_away_team_id IS NULL
            """), {
                'team_id': team_id,
                'canonical_name': canonical_name,
                'odds_team_name': odds_team_name
            })
            batter_updates += result.rowcount
        
        # Update pitcher props
        print(f"\n=== Updating pitcher prop records ===")
        pitcher_updates = 0
        
        for odds_team_name, resolution in team_resolution_map.items():
            if resolution is None:
                continue
                
            team_id = resolution['id']
            canonical_name = resolution['name']
            
            # Update home team references
            result = conn.execute(text("""
                UPDATE mlb_pitcher_props
                SET odds_home_team_id = :team_id,
                    odds_home_team = :canonical_name
                WHERE odds_home_team = :odds_team_name
                AND odds_home_team_id IS NULL
            """), {
                'team_id': team_id,
                'canonical_name': canonical_name,
                'odds_team_name': odds_team_name
            })
            pitcher_updates += result.rowcount
            
            # Update away team references
            result = conn.execute(text("""
                UPDATE mlb_pitcher_props
                SET odds_away_team_id = :team_id,
                    odds_away_team = :canonical_name
                WHERE odds_away_team = :odds_team_name
                AND odds_away_team_id IS NULL
            """), {
                'team_id': team_id,
                'canonical_name': canonical_name,
                'odds_team_name': odds_team_name
            })
            pitcher_updates += result.rowcount
        
        # Commit changes
        conn.commit()
        
        print(f"\n✅ Team name normalization complete!")
        print(f"Updated {batter_updates} batter prop records")
        print(f"Updated {pitcher_updates} pitcher prop records")
        print(f"Total updates: {batter_updates + pitcher_updates}")
        
        # Show any unresolved teams for manual review
        unresolved = [name for name, resolution in team_resolution_map.items() if resolution is None]
        if unresolved:
            print(f"\n⚠️ Unresolved team names (need manual review):")
            for name in unresolved:
                print(f"  - '{name}'")
            print(f"\nAdd these to the name mapping in get_team_name_mapping() function")
        
    except Exception as e:
        print(f"❌ Error during team name normalization: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def test_team_name_normalization():
    """Test the team name normalization logic."""
    print("=" * 60)
    print("Testing Team Name Normalization")
    print("=" * 60)
    
    test_cases = [
        'Athletics',
        'Oakland Athletics', 
        'A\'s',
        'Guardians',
        'Cleveland Guardians',
        'Red Sox',
        'Boston Red Sox',
        'NonExistent Team'
    ]
    
    for test_name in test_cases:
        normalized = normalize_team_name(test_name)
        status = "✅" if normalized != test_name else "➡️"
        print(f"{status} '{test_name}' → '{normalized}'")


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_team_name_normalization()
    else:
        update_prop_records_with_normalized_teams()


if __name__ == "__main__":
    main()
