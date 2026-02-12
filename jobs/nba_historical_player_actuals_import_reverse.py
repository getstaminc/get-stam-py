#!/usr/bin/python3

import os
import sys
import requests
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import time as _time

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


def get_nba_games_for_date(target_date: date, retries=3, delay=2) -> List[str]:
    """
    Get all NBA game IDs for a specific historical date from ESPN.
    
    Args:
        target_date: Date to fetch games for
        retries: Number of retry attempts
        delay: Delay between retries
        
    Returns:
        List of ESPN game IDs for that date
    """
    print(f"Fetching NBA games for {target_date}...")
    
    # Format date as YYYYMMDD for ESPN API
    date_str = target_date.strftime('%Y%m%d')
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    params = {
        'dates': date_str,
        'limit': 50  # Should cover all games in a day
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            # Polite spacing
            _time.sleep(0.2)
            data = response.json()
            if not data.get('events'):
                print(f"  No games found for {target_date}")
                return []
            game_ids = []
            for event in data['events']:
                game_id = event.get('id')
                if game_id:
                    game_ids.append(game_id)
            print(f"  Found {len(game_ids)} NBA games for {target_date}")
            return game_ids
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching games (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                _time.sleep(delay * (i + 1))
            else:
                print(f"  Failed to fetch games for {target_date}")
                return []
    return []


def get_historical_game_boxscore(game_id: str, target_date: date, retries=3, delay=2) -> Optional[Dict]:
    """
    Get historical boxscore data from ESPN for a specific game.
    
    Args:
        game_id: ESPN game ID
        target_date: Date of the game 
        retries: Number of retry attempts
        delay: Delay between retries
        
    Returns:
        Boxscore data or None if failed/unavailable
    """
    print(f"    Fetching boxscore for game {game_id}...")
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
    params = {
        'event': game_id,
        'enable': 'boxscore'
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            # Polite spacing
            _time.sleep(0.2)
            data = response.json()
            if not data.get('boxscore'):
                print(f"      No boxscore data available for game {game_id}")
                return None
            print(f"      ✅ Found boxscore for game {game_id}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"      Error fetching boxscore (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                _time.sleep(delay * (i + 1))
            else:
                print(f"      Failed to get boxscore for game {game_id}")
                return None
    return None


def normalize_player_name(name: str) -> str:
    """
    Normalize player name to match the format used in odds ingestion.
    """
    if not name:
        return ''
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Remove apostrophes, hyphens, and periods
    normalized = normalized.replace("'", "").replace("-", "").replace(".", "")
    
    # Collapse multiple spaces to single space and strip
    normalized = ' '.join(normalized.split())
    
    return normalized


def strip_name_suffix(normalized_name: str) -> str:
    """
    Remove common name suffixes (Jr, Sr, II, III, IV, V, 2nd, 3rd, 4th) for strict matching.
    
    Args:
        normalized_name: Normalized player name (e.g., "jimmy butler iii")
        
    Returns:
        Name without suffix (e.g., "jimmy butler")
    """
    suffixes = [' jr', ' sr', ' ii', ' iii', ' iv', ' v', ' 2nd', ' 3rd', ' 4th']
    for suffix in suffixes:
        if normalized_name.endswith(suffix):
            return normalized_name[:-len(suffix)].strip()
    return normalized_name


def parse_name_parts(normalized_name: str) -> tuple[str, str]:
    """
    Parse a normalized name into first and last name parts.
    
    Args:
        normalized_name: Normalized player name (e.g., "lebron james")
        
    Returns:
        Tuple of (first_name, last_name). For multi-part names, first_name includes all but last part.
    """
    parts = normalized_name.strip().split()
    if len(parts) == 0:
        return '', ''
    elif len(parts) == 1:
        return '', parts[0]  # Only last name
    else:
        # First name is everything except the last part
        return ' '.join(parts[:-1]), parts[-1]


def names_match_strict(odds_name: str, espn_name: str) -> bool:
    """
    Check if two normalized names match using strict first + last name comparison.
    Strips suffixes before comparing.
    
    Args:
        odds_name: Normalized name from odds data
        espn_name: Normalized name from ESPN data
        
    Returns:
        True if both first AND last names match exactly (after suffix stripping)
    """
    # Strip suffixes from both names
    odds_clean = strip_name_suffix(odds_name)
    espn_clean = strip_name_suffix(espn_name)
    
    # Parse into first and last names
    odds_first, odds_last = parse_name_parts(odds_clean)
    espn_first, espn_last = parse_name_parts(espn_clean)
    
    # Both first AND last must match
    # Handle cases where first name might be initial vs full name
    first_match = False
    if odds_first == espn_first:
        first_match = True
    elif odds_first and espn_first:
        # Check if one is initial of the other (e.g., "j" vs "john")
        if (len(odds_first) == 1 and espn_first.startswith(odds_first)):
            first_match = True
        elif (len(espn_first) == 1 and odds_first.startswith(espn_first)):
            first_match = True
    
    return first_match and odds_last == espn_last


def safe_int(value) -> Optional[int]:
    """Safely convert a value to integer, return None if not possible."""
    if value is None or value == '':
        return None
    
    try:
        # Handle cases like "2-5" for made-attempted
        if isinstance(value, str) and '-' in value:
            return int(value.split('-')[0])
        return int(float(value))
    except (ValueError, TypeError):
        return None


def build_player_stats_lookup(boxscore_data: Dict, game_id: str) -> tuple[Dict[str, Dict], List[Dict]]:
    """
    Build a lookup dictionary of player stats from ESPN boxscore.
    Keys are normalized player names, values are stat dictionaries.
    
    Args:
        boxscore_data: ESPN boxscore API response
        game_id: ESPN game ID
        
    Returns:
        Tuple of (player_lookup dict, team_info_list)
        - player_lookup: Dictionary mapping normalized_name -> player stats
        - team_info_list: List of team info dicts with 'name', 'id', 'espn_id'
    """
    player_lookup = {}
    team_info_list = []
    
    boxscore = boxscore_data.get('boxscore', {})
    teams = boxscore.get('players', [])
    
    if not teams:
        return player_lookup, team_info_list
    
    # First pass: extract team info
    for team_data in teams:
        team_info = team_data.get('team', {})
        team_info_list.append({
            'name': team_info.get('displayName', 'Unknown Team'),
            'espn_id': str(team_info.get('id', ''))
        })
    
    # Second pass: process player stats
    for team_data in teams:
        team_info = team_data.get('team', {})
        team_name = team_info.get('displayName', 'Unknown Team')
        team_espn_id = str(team_info.get('id', ''))
        
        statistics = team_data.get('statistics', [])
        if not statistics:
            continue
        
        main_stats = statistics[0] if statistics else {}
        athletes = main_stats.get('athletes', [])
        stat_names = main_stats.get('names', [])
        
        if not athletes or not stat_names:
            continue
        
        for athlete_data in athletes:
            try:
                athlete = athlete_data.get('athlete', {})
                stats = athlete_data.get('stats', [])
                did_not_play = athlete_data.get('didNotPlay', False)
                
                espn_player_id = str(athlete.get('id', ''))
                player_name = athlete.get('displayName', '')
                
                if not player_name:
                    continue
                
                normalized_name = normalize_player_name(player_name)
                
                # Handle DNP players
                if did_not_play or not stats:
                    player_lookup[normalized_name] = {
                        'espn_player_id': espn_player_id,
                        'player_name': player_name,
                        'normalized_name': normalized_name,
                        'did_not_play': True,
                        'player_team_espn_id': team_espn_id,
                        'player_team_name': team_name,
                        'actual_points': None,
                        'actual_rebounds': None,
                        'actual_assists': None,
                        'actual_threes': None,
                        'actual_minutes': None,
                        'actual_fg': None,
                        'actual_ft': None,
                        'actual_plus_minus': None,
                    }
                    continue
                
                # Map stats to dictionary
                if len(stats) != len(stat_names):
                    continue
                
                stat_dict = dict(zip(stat_names, stats))
                
                player_lookup[normalized_name] = {
                    'espn_player_id': espn_player_id,
                    'player_name': player_name,
                    'normalized_name': normalized_name,
                    'did_not_play': False,
                    'player_team_espn_id': team_espn_id,
                    'player_team_name': team_name,
                    'actual_points': safe_int(stat_dict.get('PTS')),
                    'actual_rebounds': safe_int(stat_dict.get('REB')),
                    'actual_assists': safe_int(stat_dict.get('AST')),
                    'actual_threes': safe_int(stat_dict.get('3PT', '').split('-')[0] if '3PT' in stat_dict else None),
                    'actual_minutes': stat_dict.get('MIN', ''),
                    'actual_fg': stat_dict.get('FG', ''),
                    'actual_ft': stat_dict.get('FT', ''),
                    'actual_plus_minus': safe_int(stat_dict.get('+/-')),
                }
                
            except Exception as e:
                print(f"        Error processing player in lookup: {e}")
                continue
    
    return player_lookup, team_info_list


def get_team_ids_from_boxscore(boxscore_data: Dict) -> tuple[Optional[str], Optional[str]]:
    """
    Extract the two ESPN team IDs from the boxscore data.
    
    Returns:
        Tuple of (team1_espn_id, team2_espn_id)
    """
    boxscore = boxscore_data.get('boxscore', {})
    teams = boxscore.get('players', [])
    
    team_ids = []
    for team_data in teams:
        team_info = team_data.get('team', {})
        team_id = str(team_info.get('id', ''))
        if team_id:
            team_ids.append(team_id)
    
    if len(team_ids) >= 2:
        return team_ids[0], team_ids[1]
    
    return None, None


def resolve_internal_team_ids(conn, espn_team_id_1: str, espn_team_id_2: str) -> tuple[Optional[int], Optional[int]]:
    """
    Resolve ESPN team IDs to internal team_ids from teams table.
    
    Returns:
        Tuple of (team1_id, team2_id)
    """
    team1_id = None
    team2_id = None
    
    try:
        result = conn.execute(text("""
            SELECT team_id FROM teams 
            WHERE espn_team_id = :espn_team_id AND sport = 'NBA'
        """), {'espn_team_id': espn_team_id_1}).fetchone()
        
        if result:
            team1_id = result[0]
    except Exception as e:
        print(f"    ❌ Error resolving team {espn_team_id_1}: {e}")
    
    try:
        result = conn.execute(text("""
            SELECT team_id FROM teams 
            WHERE espn_team_id = :espn_team_id AND sport = 'NBA'
        """), {'espn_team_id': espn_team_id_2}).fetchone()
        
        if result:
            team2_id = result[0]
    except Exception as e:
        print(f"    ❌ Error resolving team {espn_team_id_2}: {e}")
    
    return team1_id, team2_id


def update_game_props_with_actuals(conn, game_id: str, game_date: date, player_stats_lookup: Dict[str, Dict]) -> int:
    """
    Reverse approach: Get all prop records for this game, then search for matching players in ESPN data.
    
    Args:
        conn: Database connection
        game_id: ESPN game ID
        game_date: Date of the game
        player_stats_lookup: Dictionary of player stats from ESPN (normalized_name -> stats)
        
    Returns:
        Number of records updated
    """
    # First, get the team IDs from the game
    espn_team_id_1, espn_team_id_2 = get_team_ids_from_boxscore({'boxscore': {'players': []}})
    
    # This won't work - we need the full boxscore data
    # Let me restructure this function to be called with the full boxscore
    pass


def process_game_reverse(conn, game_id: str, game_date: date) -> int:
    """
    Process a single game using the reverse approach.
    
    Args:
        conn: Database connection
        game_id: ESPN game ID
        game_date: Date of the game
        
    Returns:
        Number of records updated
    """
    print(f"\n  Processing game: {game_id}")
    
    # Step 1: Get boxscore from ESPN
    boxscore_data = get_historical_game_boxscore(game_id, game_date)
    
    if not boxscore_data:
        return 0
    
    # Step 2: Extract team IDs from boxscore
    espn_team_id_1, espn_team_id_2 = get_team_ids_from_boxscore(boxscore_data)
    
    if not espn_team_id_1 or not espn_team_id_2:
        print(f"    ❌ Could not extract team IDs from boxscore")
        return 0
    
    print(f"    Found teams: {espn_team_id_1}, {espn_team_id_2}")
    
    # Step 3: Resolve to internal team IDs
    team1_id, team2_id = resolve_internal_team_ids(conn, espn_team_id_1, espn_team_id_2)
    
    if not team1_id or not team2_id:
        print(f"    ❌ Could not resolve internal team IDs")
        return 0
    
    print(f"    Internal team IDs: {team1_id}, {team2_id}")
    
    # Step 4: Build player stats lookup from ESPN data and get team info
    player_stats_lookup, team_info_list = build_player_stats_lookup(boxscore_data, game_id)
    
    if not player_stats_lookup:
        print(f"    No player stats found in boxscore")
        return 0
    
    # Resolve internal team IDs for team info list
    for team_info in team_info_list:
        try:
            result = conn.execute(text("""
                SELECT team_id FROM teams 
                WHERE espn_team_id = :espn_team_id AND sport = 'NBA'
            """), {'espn_team_id': team_info['espn_id']}).fetchone()
            if result:
                team_info['id'] = result[0]
            else:
                team_info['id'] = None
        except Exception as e:
            print(f"    ❌ Error resolving team {team_info['name']}: {e}")
            team_info['id'] = None
    
    print(f"    Built lookup for {len(player_stats_lookup)} players from ESPN")
    
    # Step 5: Get all prop records for this game
    prop_records = conn.execute(text("""
        SELECT id, player_id, normalized_name, odds_home_team_id, odds_away_team_id
        FROM nba_player_props
        WHERE game_date = :game_date
        AND (odds_home_team_id = :team1_id OR odds_away_team_id = :team1_id
             OR odds_home_team_id = :team2_id OR odds_away_team_id = :team2_id)
    """), {
        'game_date': game_date,
        'team1_id': team1_id,
        'team2_id': team2_id
    }).fetchall()
    
    if not prop_records:
        print(f"    No prop records found for these teams on {game_date}")
        return 0
    
    print(f"    Found {len(prop_records)} prop records to update")
    
    # Step 6: For each prop record, search for matching player in ESPN data
    updated_count = 0
    
    for record in prop_records:
        props_id, player_id, normalized_name, odds_home_team_id, odds_away_team_id = record
        
        try:
            player_stats = None
            
            # Step 1: Look up ESPN player ID for this player (most reliable identifier)
            player_espn_id = conn.execute(text("""
                SELECT espn_player_id FROM nba_players WHERE id = :player_id
            """), {'player_id': player_id}).fetchone()
            
            # Step 2: If we have ESPN ID, search for it in ESPN data first
            if player_espn_id and player_espn_id[0]:
                for espn_name, stats in player_stats_lookup.items():
                    if stats.get('espn_player_id') == player_espn_id[0]:
                        player_stats = stats
                        print(f"      ⚡ Matched by ESPN ID: {normalized_name} (ID: {player_espn_id[0]})")
                        break
            
            # Step 3: If not found by ESPN ID, try exact normalized name match
            if not player_stats:
                player_stats = player_stats_lookup.get(normalized_name)
                if player_stats:
                    print(f"      ✓ Exact name match: {normalized_name}")
            
            # Step 4: If still not found, try strict first + last name matching with suffix stripping
            if not player_stats:
                for espn_name, stats in player_stats_lookup.items():
                    if names_match_strict(normalized_name, espn_name):
                        player_stats = stats
                        print(f"      🔍 Strict name match (suffix stripped): {normalized_name} → {espn_name}")
                        break
            
            if not player_stats:
                # No match found - check if this is a DNP or a real matching problem
                try: 
                    # Check if this player has other prop records with consistent ESPN IDs
                    other_props = conn.execute(text("""
                        SELECT DISTINCT p.espn_player_id 
                        FROM nba_player_props pp
                        JOIN nba_players p ON pp.player_id = p.id
                        WHERE pp.player_id = :player_id AND pp.id != :props_id
                    """), {'player_id': player_id, 'props_id': props_id}).fetchall()
                    
                    # Extract unique ESPN IDs (excluding None)
                    espn_ids = [row[0] for row in other_props if row[0] is not None]
                    unique_espn_ids = set(espn_ids)
                    
                    # If player has other records with exactly one consistent ESPN ID, likely just DNP
                    if len(unique_espn_ids) == 1:
                        print(f"      ℹ️  Player not in ESPN data (likely DNP): {normalized_name} (has ESPN ID {list(unique_espn_ids)[0]} from other games)")
                        continue
                    
                    # Otherwise, this is a real matching problem - log to mismatch table
                    if len(unique_espn_ids) == 0:
                        print(f"      ⚠️  No ESPN ID found in any records for {normalized_name}")
                    else:
                        print(f"      ⚠️  Inconsistent ESPN IDs for {normalized_name}: {unique_espn_ids}")
                    
                    # Get team names for the mismatch record
                    home_team_name = conn.execute(text("""
                        SELECT team_name FROM teams WHERE team_id = :team_id
                    """), {'team_id': odds_home_team_id}).fetchone()
                    
                    away_team_name = conn.execute(text("""
                        SELECT team_name FROM teams WHERE team_id = :team_id
                    """), {'team_id': odds_away_team_id}).fetchone()
                    
                    home_team_str = home_team_name[0] if home_team_name else 'Unknown'
                    away_team_str = away_team_name[0] if away_team_name else 'Unknown'
                    
                    # Check if this mismatch already exists (avoid duplicates)
                    existing_mismatch = conn.execute(text("""
                        SELECT id FROM nba_player_name_mismatch
                        WHERE nba_player_props_id = :props_id AND resolved = false
                    """), {'props_id': props_id}).fetchone()
                    
                    if not existing_mismatch:
                        # Insert new mismatch record
                        conn.execute(text("""
                            INSERT INTO nba_player_name_mismatch (
                                nba_player_props_id,
                                game_date,
                                odds_home_team_id,
                                odds_away_team_id,
                                odds_home_team,
                                odds_away_team,
                                normalized_name,
                                player_id,
                                resolved,
                                created_at,
                                updated_at
                            ) VALUES (
                                :props_id,
                                :game_date,
                                :home_team_id,
                                :away_team_id,
                                :home_team_name,
                                :away_team_name,
                                :normalized_name,
                                :player_id,
                                false,
                                CURRENT_TIMESTAMP,
                                CURRENT_TIMESTAMP
                            )
                        """), {
                            'props_id': props_id,
                            'game_date': game_date,
                            'home_team_id': odds_home_team_id,
                            'away_team_id': odds_away_team_id,
                            'home_team_name': home_team_str,
                            'away_team_name': away_team_str,
                            'normalized_name': normalized_name,
                            'player_id': player_id
                        })
                        print(f"      ⚠️  Unmatched player logged to mismatch table: {normalized_name} ({home_team_str} vs {away_team_str})")
                    
                except Exception as mismatch_error:
                    print(f"      ❌ Error processing mismatch for {normalized_name}: {mismatch_error}")
                
                continue
            
            # Update the record
            espn_player_id = player_stats.get('espn_player_id')
            is_dnp = player_stats.get('did_not_play', False)
            
            # Backfill ESPN ID if needed
            if espn_player_id and player_id:
                existing_espn_id = conn.execute(text("""
                    SELECT espn_player_id FROM nba_players WHERE id = :player_id
                """), {'player_id': player_id}).fetchone()
                
                if existing_espn_id and not existing_espn_id[0]:
                    # Check if ESPN ID already exists elsewhere
                    id_in_use = conn.execute(text("""
                        SELECT id FROM nba_players WHERE espn_player_id = :espn_player_id
                    """), {'espn_player_id': str(espn_player_id)}).fetchone()
                    
                    if not id_in_use:
                        conn.execute(text("""
                            UPDATE nba_players
                            SET espn_player_id = :espn_player_id
                            WHERE id = :player_id
                        """), {
                            'espn_player_id': str(espn_player_id),
                            'player_id': player_id
                        })
            
            # Determine player's team and opponent based on ESPN data (not odds data)
            player_team_espn_id = player_stats.get('player_team_espn_id')
            player_team_name = player_stats.get('player_team_name', 'Unknown')
            
            # Find the player's team ID by matching ESPN ID
            player_team_id = None
            opponent_team_id = None
            opponent_team_name = 'Unknown'
            
            for team_info in team_info_list:
                if team_info['espn_id'] == player_team_espn_id:
                    player_team_id = team_info['id']
                    break
            
            # Find the opponent team (the other team in the game)
            for team_info in team_info_list:
                if team_info['espn_id'] != player_team_espn_id:
                    opponent_team_id = team_info['id']
                    opponent_team_name = team_info['name']
                    break
            
            # Update prop record
            if is_dnp:
                conn.execute(text("""
                    UPDATE nba_player_props
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
                    'espn_event_id': game_id,
                    'record_id': props_id
                })
                print(f"      🚫 DNP: {normalized_name} ({player_team_name} vs {opponent_team_name})")
            else:
                conn.execute(text("""
                    UPDATE nba_player_props
                    SET actual_player_points = :points,
                        actual_player_rebounds = :rebounds,
                        actual_player_assists = :assists,
                        actual_player_threes = :threes,
                        actual_player_minutes = :minutes,
                        actual_player_fg = :fg,
                        actual_player_ft = :ft,
                        actual_plus_minus = :plus_minus,
                        player_team_name = :team_name,
                        player_team_id = :team_id,
                        opponent_team_name = :opponent_team_name,
                        opponent_team_id = :opponent_team_id,
                        espn_event_id = :espn_event_id,
                        did_not_play = false,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :record_id
                """), {
                    'points': player_stats['actual_points'],
                    'rebounds': player_stats['actual_rebounds'],
                    'assists': player_stats['actual_assists'],
                    'threes': player_stats['actual_threes'],
                    'minutes': player_stats['actual_minutes'],
                    'fg': player_stats['actual_fg'],
                    'ft': player_stats['actual_ft'],
                    'plus_minus': player_stats['actual_plus_minus'],
                    'team_name': player_team_name,
                    'team_id': player_team_id,
                    'opponent_team_name': opponent_team_name,
                    'opponent_team_id': opponent_team_id,
                    'espn_event_id': game_id,
                    'record_id': props_id
                })
                print(f"      ✅ {normalized_name} ({player_team_name} vs {opponent_team_name}): {player_stats['actual_points']}pts/{player_stats['actual_rebounds']}reb/{player_stats['actual_assists']}ast")
            
            updated_count += 1
            
        except Exception as e:
            print(f"      ❌ Error updating {normalized_name}: {e}")
            conn.rollback()
            conn.begin()
            continue
    
    print(f"    Successfully updated {updated_count} prop records")
    return updated_count


def import_historical_actuals_for_date_reverse(target_date: date, conn) -> int:
    """
    Import historical player actuals for a specific date using reverse approach.
    
    Args:
        target_date: Date to import
        conn: Database connection
        
    Returns:
        Number of player prop records updated
    """
    print(f"\n=== Importing Historical Player Actuals (Reverse) for {target_date} ===")
    
    # Step 1: Get all games for the date
    game_ids = get_nba_games_for_date(target_date)
    
    if not game_ids:
        print(f"No games found for {target_date}")
        return 0
    
    # Step 2: Process each game
    total_updated = 0
    
    for i, game_id in enumerate(game_ids, 1):
        print(f"\n  Processing game {i}/{len(game_ids)}: {game_id}")
        
        try:
            updated = process_game_reverse(conn, game_id, target_date)
            total_updated += updated
            
            # Rate limiting
            if i < len(game_ids):
                time.sleep(2)
                
        except Exception as e:
            print(f"    ❌ Error processing game {game_id}: {e}")
            continue
    
    return total_updated


def import_historical_actuals_date_range_reverse(start_date: date, end_date: date):
    """
    Import historical player actual stats for a date range using reverse approach.
    
    Args:
        start_date: Start date (inclusive) 
        end_date: End date (inclusive)
    """
    print(f"=== Historical NBA Player Actuals Import (Reverse Approach) ===")
    print(f"Date range: {start_date} to {end_date}")
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        current_date = start_date
        total_updated = 0
        
        while current_date <= end_date:
            try:
                daily_updated = import_historical_actuals_for_date_reverse(
                    current_date, conn
                )
                
                total_updated += daily_updated
                
                # Commit daily progress
                conn.commit()
                print(f"✅ Committed {daily_updated} records for {current_date}")
                
            except Exception as e:
                print(f"❌ Error processing {current_date}: {e}")
                conn.rollback()
            
            # Move to next date
            current_date += timedelta(days=1)
            
            # Rate limiting between dates
            if current_date <= end_date:
                time.sleep(3)
        
        print(f"\n🎉 Historical actuals import complete!")
        print(f"Total prop records updated: {total_updated}")
        print(f"Date range: {start_date} to {end_date}")
        
    except Exception as e:
        print(f"❌ Fatal error during historical import: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 nba_historical_player_actuals_import_reverse.py YYYY-MM-DD [YYYY-MM-DD]")
        print("Example: python3 nba_historical_player_actuals_import_reverse.py 2023-10-24")
        print("Example: python3 nba_historical_player_actuals_import_reverse.py 2023-10-24 2023-10-31")
        sys.exit(1)
    
    start_date_str = sys.argv[1]
    end_date_str = sys.argv[2] if len(sys.argv) > 2 else start_date_str
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    import_historical_actuals_date_range_reverse(start_date, end_date)
