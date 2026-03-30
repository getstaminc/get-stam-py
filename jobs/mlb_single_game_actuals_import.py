#!/usr/bin/python3
"""
MLB Single Game Actuals Import

This script imports actual player and pitcher stats for a single ESPN game event.
Useful for testing, debugging, or importing specific games.

Usage:
    python3 mlb_single_game_actuals_import.py ESPN_GAME_ID
    python3 mlb_single_game_actuals_import.py 401234567
"""

import os
import sys
from datetime import datetime, date
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import functions from the reverse import module
from jobs.mlb_historical_player_actuals_import_reverse import (
    get_historical_game_boxscore,
    process_game_reverse,
    build_player_stats_lookup_mlb,
    get_team_ids_from_boxscore,
    resolve_internal_team_ids,
    find_player_in_lookup,
    normalize_player_name
)

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


def import_single_game_actuals(espn_game_id: str, target_date: date = None):
    """
    Import actual player and pitcher stats for a single ESPN game.
    
    Args:
        espn_game_id: ESPN game ID (e.g., "401234567")
        target_date: Optional date override for the game
    """
    print("=" * 60)
    print("MLB Single Game Actuals Import (Players & Pitchers)")
    print("=" * 60)
    print(f"ESPN Game ID: {espn_game_id}")
    
    # If no date provided, try to extract from current context or use today
    if not target_date:
        target_date = date.today()
        print(f"Using default date: {target_date}")
    else:
        print(f"Game Date: {target_date}")
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # First, let's see if we can get basic game info
        boxscore_data = get_historical_game_boxscore(espn_game_id, target_date)
        
        if not boxscore_data:
            print(f"❌ Could not fetch boxscore data for game {espn_game_id}")
            return 0
        
        # Extract game info if available
        game_info = boxscore_data.get('header', {})
        if game_info:
            competitions = game_info.get('competitions', [])
            if competitions:
                competition = competitions[0]
                game_date_str = competition.get('date', '')
                if game_date_str:
                    # Parse ESPN date format: "2024-06-03T22:45Z"
                    try:
                        parsed_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                        actual_game_date = parsed_date.date()
                        print(f"Detected game date: {actual_game_date}")
                        target_date = actual_game_date
                    except:
                        print(f"Could not parse game date: {game_date_str}")
                
                # Show teams
                competitors = competition.get('competitors', [])
                teams = []
                for comp in competitors:
                    team = comp.get('team', {})
                    teams.append(team.get('displayName', 'Unknown'))
                if len(teams) >= 2:
                    print(f"Matchup: {teams[0]} vs {teams[1]}")
        
        print(f"\nProcessing game actuals...")
        
        # Process player actuals
        print("Processing player actuals...")
        player_updated_count = process_game_reverse(conn, espn_game_id, target_date)
        
        # Process pitcher actuals
        print("Processing pitcher actuals...")
        pitcher_updated_count = process_pitcher_actuals(conn, espn_game_id, target_date)
        
        # Commit the changes
        conn.commit()
        
        print(f"\n✅ Successfully updated {player_updated_count} player prop records")
        print(f"✅ Successfully updated {pitcher_updated_count} pitcher prop records")
        print(f"Total records updated: {player_updated_count + pitcher_updated_count}")
        print(f"Game ID: {espn_game_id}")
        print(f"Date: {target_date}")
        
        return player_updated_count + pitcher_updated_count
        
    except Exception as e:
        print(f"❌ Error processing game {espn_game_id}: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        return 0
    finally:
        conn.close()


def process_pitcher_actuals(conn, espn_game_id: str, game_date: date):
    """
    Process pitcher actuals using the same logic as the reverse import.
    """
    print(f"Fetching boxscore data for pitcher actuals...")
    
    boxscore_data = get_historical_game_boxscore(espn_game_id, game_date)
    
    if not boxscore_data:
        print("No boxscore data available")
        return 0
    
    # Use the same team resolution logic as reverse import
    espn_team_id_1, espn_team_id_2 = get_team_ids_from_boxscore(boxscore_data)
    
    if not espn_team_id_1 or not espn_team_id_2:
        print(f"Could not extract team IDs from boxscore")
        return 0
    
    team1_id, team2_id = resolve_internal_team_ids(conn, espn_team_id_1, espn_team_id_2)
    
    if not team1_id or not team2_id:
        print(f"Could not resolve internal team IDs")
        return 0
    
    # Build pitcher lookup using the same function as reverse import
    batter_lookup, pitcher_lookup, team_info_list = build_player_stats_lookup_mlb(boxscore_data)
    
    if not pitcher_lookup:
        print("No pitcher stats found in boxscore")
        return 0
    
    print(f"Built lookup for {len(pitcher_lookup)} pitchers from ESPN")
    
    # Try multiple date ranges to catch records with slightly different dates
    date_variants = [
        game_date,
        game_date.replace(day=game_date.day - 1) if game_date.day > 1 else game_date,
        game_date.replace(day=game_date.day + 1) if game_date.day < 28 else game_date
    ]
    
    updated_count = 0
    
    # Get pitcher prop records for this game (trying multiple dates)
    for target_date in date_variants:
        pitcher_records = conn.execute(text("""
            SELECT id, player_id, normalized_name, odds_home_team_id, odds_away_team_id
            FROM mlb_pitcher_props
            WHERE game_date = :game_date
            AND (odds_home_team_id = :team1_id OR odds_away_team_id = :team1_id
                 OR odds_home_team_id = :team2_id OR odds_away_team_id = :team2_id)
            AND (actual_pitcher_strikeouts IS NULL 
                 OR actual_pitcher_earned_runs IS NULL 
                 OR actual_pitcher_hits_allowed IS NULL 
                 OR actual_pitcher_walks IS NULL)
        """), {
            'game_date': target_date,
            'team1_id': team1_id,
            'team2_id': team2_id
        }).fetchall()
        
        if pitcher_records:
            print(f"Found {len(pitcher_records)} pitcher prop records for {target_date}")
            
            for record in pitcher_records:
                props_id, player_id, normalized_name, odds_home_team_id, odds_away_team_id = record
                
                # Use the same matching logic as reverse import
                player_stats = find_player_in_lookup(normalized_name, pitcher_lookup, conn, player_id, props_id)
                
                if not player_stats:
                    print(f"    ⚠️ No match found for {normalized_name}")
                    continue
                
                # Determine player's team and opponent (same logic as reverse import)
                player_team_espn_id = player_stats.get('player_team_espn_id')
                player_team_name = player_stats.get('player_team_name', 'Unknown')
                
                player_team_id = None
                opponent_team_id = None
                opponent_team_name = 'Unknown'
                
                for team_info in team_info_list:
                    if team_info['espn_id'] == player_team_espn_id:
                        # Resolve internal team ID
                        try:
                            result = conn.execute(text("""
                                SELECT team_id FROM teams
                                WHERE espn_team_id = :espn_team_id AND sport = 'MLB'
                            """), {'espn_team_id': team_info['espn_id']}).fetchone()
                            player_team_id = result[0] if result else None
                        except Exception as e:
                            print(f"Error resolving team {team_info['name']}: {e}")
                        break
                
                for team_info in team_info_list:
                    if team_info['espn_id'] != player_team_espn_id:
                        opponent_team_name = team_info['name']
                        try:
                            result = conn.execute(text("""
                                SELECT team_id FROM teams
                                WHERE espn_team_id = :espn_team_id AND sport = 'MLB'
                            """), {'espn_team_id': team_info['espn_id']}).fetchone()
                            opponent_team_id = result[0] if result else None
                        except Exception as e:
                            print(f"Error resolving opponent team {team_info['name']}: {e}")
                        break
                
                is_dnp = player_stats.get('did_not_play', False)
                
                if is_dnp:
                    conn.execute(text("""
                        UPDATE mlb_pitcher_props
                        SET player_team_name = :team_name,
                            player_team_id = :team_id,
                            opponent_team_name = :opponent_team_name,
                            opponent_team_id = :opponent_team_id,
                            espn_event_id = :espn_event_id,
                            did_not_play = true,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :record_id
                    """), {
                        'team_name': player_team_name,
                        'team_id': player_team_id,
                        'opponent_team_name': opponent_team_name,
                        'opponent_team_id': opponent_team_id,
                        'espn_event_id': espn_game_id,
                        'record_id': props_id
                    })
                    print(f"      🚫 DNP: {normalized_name} ({player_team_name} vs {opponent_team_name})")
                else:
                    conn.execute(text("""
                        UPDATE mlb_pitcher_props
                        SET actual_pitcher_strikeouts = :strikeouts,
                            actual_pitcher_earned_runs = :earned_runs,
                            actual_pitcher_hits_allowed = :hits_allowed,
                            actual_pitcher_walks = :walks,
                            actual_pitcher_innings_pitched = :innings_pitched,
                            player_team_name = :team_name,
                            player_team_id = :team_id,
                            opponent_team_name = :opponent_team_name,
                            opponent_team_id = :opponent_team_id,
                            espn_event_id = :espn_event_id,
                            did_not_play = false,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :record_id
                    """), {
                        'strikeouts': player_stats['actual_pitcher_strikeouts'],
                        'earned_runs': player_stats['actual_pitcher_earned_runs'],
                        'hits_allowed': player_stats['actual_pitcher_hits_allowed'],
                        'walks': player_stats['actual_pitcher_walks'],
                        'innings_pitched': player_stats['actual_pitcher_innings_pitched'],
                        'team_name': player_team_name,
                        'team_id': player_team_id,
                        'opponent_team_name': opponent_team_name,
                        'opponent_team_id': opponent_team_id,
                        'espn_event_id': espn_game_id,
                        'record_id': props_id
                    })
                    print(f"      ✅ {normalized_name} ({player_team_name} vs {opponent_team_name}): {player_stats['actual_pitcher_strikeouts']}K/{player_stats['actual_pitcher_earned_runs']}ER/{player_stats['actual_pitcher_innings_pitched']}IP")
                
                updated_count += 1
            
            # If we found and processed records for this date, break out of the date loop
            if updated_count > 0:
                break
    
    return updated_count


def main():
    """Main function to parse arguments and run the import."""
    if len(sys.argv) < 2:
        print("Usage: python3 mlb_single_game_actuals_import.py ESPN_GAME_ID [YYYY-MM-DD]")
        print("Example: python3 mlb_single_game_actuals_import.py 401234567")
        print("Example: python3 mlb_single_game_actuals_import.py 401234567 2024-06-03")
        print("Note: Imports both player and pitcher actuals")
        sys.exit(1)
    
    espn_game_id = sys.argv[1]
    
    # Optional date parameter
    target_date = None
    if len(sys.argv) >= 3:
        try:
            target_date = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    
    try:
        updated_count = import_single_game_actuals(espn_game_id, target_date)
        
        if updated_count > 0:
            print(f"\n🎉 Import completed successfully!")
        else:
            print(f"\n⚠️ No records were updated")
            
    except KeyboardInterrupt:
        print("\n⚠️ Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
