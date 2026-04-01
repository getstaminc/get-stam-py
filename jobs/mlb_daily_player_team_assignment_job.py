#!/usr/bin/python3
"""
MLB Player Team Assignment Job

This script populates the team_id field in the mlb_players table by fetching MLB rosters from ESPN and matching espn_player_id to your database records.
If espn_player_id is missing, it attempts to match by normalized player names.
If ESPN rosters don't have the player, it uses their most recent prop record to assign team_id.
Designed to be scheduled daily (e.g., via Heroku Scheduler) to keep player-team assignments up to date.
"""

import os
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from unidecode import unidecode

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

engine = create_engine(DATABASE_URL)

ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/{team_id}/roster"

def normalize_player_name(name: str) -> str:
    """Normalize player name for matching (same logic as actuals import)"""
    if not name:
        return ''
    
    # Remove accents/diacritics
    name = unidecode(name)
    
    normalized = name.lower()
    normalized = normalized.replace("'", "").replace("-", "").replace(".", "")
    normalized = ' '.join(normalized.split())
    return normalized

def assign_teams_from_recent_props(conn):
    """Assign teams to players based on their most recent prop records."""
    print("=== Assigning teams from recent prop records ===")
    
    try:
        # Find players with NULL team_id who have recent prop records
        unassigned_players = conn.execute(text("""
            WITH recent_batter_props AS (
                SELECT 
                    player_id,
                    odds_home_team_id,
                    odds_away_team_id,
                    player_team_id,
                    game_date,
                    'batter' as prop_type,
                    ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY game_date DESC, created_at DESC) as rn
                FROM mlb_batter_props 
                WHERE player_team_id IS NOT NULL
            ),
            recent_pitcher_props AS (
                SELECT 
                    player_id,
                    odds_home_team_id,
                    odds_away_team_id,
                    player_team_id,
                    game_date,
                    'pitcher' as prop_type,
                    ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY game_date DESC, created_at DESC) as rn
                FROM mlb_pitcher_props 
                WHERE player_team_id IS NOT NULL
            ),
            combined_props AS (
                SELECT * FROM recent_batter_props WHERE rn = 1
                UNION ALL
                SELECT * FROM recent_pitcher_props WHERE rn = 1
            ),
            most_recent_prop AS (
                SELECT 
                    player_id,
                    player_team_id,
                    game_date,
                    prop_type,
                    ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY game_date DESC) as rn
                FROM combined_props
            )
            SELECT 
                p.id,
                p.player_name,
                mrp.player_team_id,
                mrp.game_date,
                mrp.prop_type,
                t.team_name
            FROM mlb_players p
            JOIN most_recent_prop mrp ON p.id = mrp.player_id
            JOIN teams t ON mrp.player_team_id = t.team_id
            WHERE p.team_id IS NULL 
            AND mrp.rn = 1
            ORDER BY mrp.game_date DESC
        """)).fetchall()
        
        if not unassigned_players:
            print("  No unassigned players with recent prop records found")
            return 0
        
        print(f"  Found {len(unassigned_players)} unassigned players with recent prop records")
        
        updated_count = 0
        
        for player in unassigned_players:
            player_id, player_name, team_id, game_date, prop_type, team_name = player
            
            try:
                # Update the player's team assignment
                conn.execute(text("""
                    UPDATE mlb_players 
                    SET team_id = :team_id 
                    WHERE id = :player_id
                """), {
                    "team_id": team_id,
                    "player_id": player_id
                })
                
                print(f"    📍 Assigned {player_name} → {team_name} (from {prop_type} prop on {game_date})")
                updated_count += 1
                
            except Exception as e:
                print(f"    ❌ Error updating {player_name}: {e}")
                continue
        
        return updated_count
        
    except Exception as e:
        print(f"Error in props-based team assignment: {e}")
        return 0

def main():
    print("=" * 80)
    print("MLB Player Team Assignment Job")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Step 1: Handle assignments from recent prop data (for players not in current rosters)
        print("\n=== Step 1: Team assignment from recent prop records ===")
        props_updates = assign_teams_from_recent_props(conn)
        print(f"Assigned teams to {props_updates} players from recent props")
        
        # Step 2: Handle ESPN roster assignments
        print("\n=== Step 2: ESPN roster assignment ===")
        
        # Get all MLB teams with espn_team_id
        teams = conn.execute(text("SELECT team_id, team_name, espn_team_id FROM teams WHERE sport = 'MLB' AND espn_team_id IS NOT NULL")).fetchall()
        print(f"Found {len(teams)} MLB teams with ESPN IDs.")
        
        total_updates = 0
        total_espn_id_updates = 0
        
        for team in teams:
            team_id, team_name, espn_team_id = team
            url = ESPN_ROSTER_URL.format(team_id=espn_team_id)
            print(f"Fetching roster for {team_name} (team_id={team_id}, espn_team_id={espn_team_id})...")
            
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                data = resp.json()
                
                # MLB response structure: position groups with items arrays
                position_groups = data.get("athletes", [])
                all_athletes = []
                
                # Extract athletes from all position groups
                for position_group in position_groups:
                    items = position_group.get("items", [])
                    all_athletes.extend(items)
                
                print(f"  Found {len(all_athletes)} athletes across all positions.")
                
                for athlete in all_athletes:
                    athlete_id = athlete.get("id")
                    athlete_name = athlete.get("displayName", "")
                    
                    if not athlete_id or not athlete_name:
                        continue
                    
                    # Try direct ESPN ID match first
                    result = conn.execute(
                        text("UPDATE mlb_players SET team_id = :team_id WHERE espn_player_id = :athlete_id"),
                        {"team_id": team_id, "athlete_id": str(athlete_id)}
                    )
                    
                    if result.rowcount:
                        total_updates += result.rowcount
                        print(f"    ✅ Updated by ESPN ID: {athlete_name} (espn_id={athlete_id})")
                        continue
                    
                    # If no ESPN ID match, try name matching for players with NULL espn_player_id
                    normalized_espn_name = normalize_player_name(athlete_name)
                    
                    # Find matching player by normalized name who doesn't have an ESPN ID yet
                    player_match = conn.execute(text("""
                        SELECT id, player_name FROM mlb_players 
                        WHERE normalized_name = :normalized_name 
                        AND espn_player_id IS NULL
                        LIMIT 1
                    """), {"normalized_name": normalized_espn_name}).fetchone()
                    
                    if player_match:
                        player_id, player_name = player_match
                        
                        # Check if this ESPN ID is already used by another player
                        existing_player = conn.execute(text("""
                            SELECT id, player_name FROM mlb_players WHERE espn_player_id = :athlete_id
                        """), {"athlete_id": str(athlete_id)}).fetchone()
                        
                        if existing_player:
                            print(f"    ⚠️ ESPN ID {athlete_id} already used by player {existing_player[1]}")
                            continue
                        
                        # Update both espn_player_id and team_id
                        conn.execute(text("""
                            UPDATE mlb_players 
                            SET espn_player_id = :athlete_id, team_id = :team_id 
                            WHERE id = :player_id
                        """), {
                            "athlete_id": str(athlete_id),
                            "team_id": team_id,
                            "player_id": player_id
                        })
                        
                        total_updates += 1
                        total_espn_id_updates += 1
                        print(f"    🔗 Matched by name: {player_name} → {athlete_name} (espn_id={athlete_id})")
                    else:
                        print(f"    ⚠️ No match found for {athlete_name} (normalized: {normalized_espn_name})")
                            
            except Exception as e:
                print(f"  ❌ Error fetching or updating for team {team_name}: {e}")
        
        conn.commit()
        print(f"\n✅ Step 1 - Props-based assignments: {props_updates}")
        print(f"✅ Step 2 - ESPN roster assignments: {total_updates}")
        print(f"✅ Step 2 - ESPN IDs populated: {total_espn_id_updates}")
        print(f"✅ Total player records updated: {props_updates + total_updates}")
    
    print("\nDone.")

if __name__ == "__main__":
    main()
