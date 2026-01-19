#!/usr/bin/python3

import os
import sys
import requests
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pytz

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.player_resolver import PlayerResolver

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


def get_yesterdays_nba_games(retries=3, delay=1):
    """
    Fetch yesterday's completed NBA games from ESPN API (in Eastern Time).
    
    Returns:
        List of completed games with event IDs
    """
    print("Fetching yesterday's NBA games from ESPN (Eastern Time)...")
    
    # Get yesterday's date in Eastern Time
    eastern = pytz.timezone('US/Eastern')
    now_et = datetime.now(eastern)
    yesterday_et = now_et - timedelta(days=1)
    
    # ESPN API uses dates in format YYYYMMDD
    # We need to check both yesterday and today in UTC
    # because games late at night ET appear as next day in UTC
    dates_to_check = [
        yesterday_et.strftime('%Y%m%d'),  # Yesterday ET
        now_et.strftime('%Y%m%d')  # Today ET (for late games)
    ]
    
    all_games = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for date_str in dates_to_check:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
        
        for i in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                games = data.get('events', [])
                
                for game in games:
                    # Parse game date and convert to Eastern Time
                    game_date_str = game.get('date', '')
                    if game_date_str:
                        # Parse UTC time
                        game_dt_utc = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                        # Convert to Eastern Time
                        game_dt_et = game_dt_utc.astimezone(eastern)
                        # Check if game is on yesterday's date in ET
                        if game_dt_et.date() == yesterday_et.date():
                            status = game.get('status', {}).get('type', {}).get('name', '')
                            if status == 'STATUS_FINAL':
                                all_games.append(game)
                
                break  # Success, exit retry loop
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching games for {date_str} (attempt {i+1}/{retries}): {e}")
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    print(f"Failed to fetch games for {date_str} after {retries} attempts")
    
    print(f"Found {len(all_games)} completed NBA games from yesterday (Eastern Time)")
    return all_games


def get_nba_games_for_date_et(target_date: str, retries=3, delay=1):
    """
    Fetch NBA games for a specific date in Eastern Time.
    
    Args:
        target_date: Date string in format 'YYYY-MM-DD' (e.g., '2025-01-08')
        retries: Number of retry attempts
        delay: Delay between retries
    
    Returns:
        List of completed games with event IDs
    """
    print(f"Fetching NBA games for {target_date} (Eastern Time)...")
    
    # Parse the target date
    target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    
    # ESPN API uses dates in format YYYYMMDD
    # We need to check both the target date and the next day in UTC
    # because games late at night ET (e.g., 11:30 PM ET on 1/8) appear as 1/9 UTC
    dates_to_check = [
        target_dt.strftime('%Y%m%d'),  # The target date
        (target_dt + timedelta(days=1)).strftime('%Y%m%d')  # Next day (for late games in UTC)
    ]
    
    eastern = pytz.timezone('US/Eastern')
    all_games = []
    
    for date_str in dates_to_check:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        for i in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                games = data.get('events', [])
                
                for game in games:
                    # Parse game date and convert to Eastern Time
                    game_date_str = game.get('date', '')
                    if game_date_str:
                        # Parse UTC time
                        game_dt_utc = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                        # Convert to Eastern Time
                        game_dt_et = game_dt_utc.astimezone(eastern)
                        # Check if game is on target date in ET
                        if game_dt_et.date() == target_dt.date():
                            status = game.get('status', {}).get('type', {}).get('name', '')
                            if status == 'STATUS_FINAL':
                                all_games.append(game)
                
                break  # Success, exit retry loop
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching games for {date_str} (attempt {i+1}/{retries}): {e}")
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    print(f"Failed to fetch games for {date_str} after {retries} attempts")
    
    print(f"Found {len(all_games)} completed NBA games on {target_date} (Eastern Time)")
    return all_games


def get_game_boxscore(game_id: str, retries=3, delay=1) -> Optional[Dict]:
    """
    Fetch detailed boxscore for a specific game from ESPN.
    
    Args:
        game_id: ESPN game ID
        retries: Number of retry attempts
        delay: Delay between retries
        
    Returns:
        Boxscore data or None if failed
    """
    print(f"  Fetching boxscore for game {game_id}")
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}&enable=boxscore"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"    Error fetching boxscore (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                print(f"    Failed to get boxscore for game {game_id}")
                return None
    
    return None


def extract_player_stats_from_boxscore(boxscore_data: Dict, game_id: str, game_date: date) -> List[Dict]:
    """
    Extract individual player statistics from ESPN boxscore, including DNP and injured players.
    
    Args:
        boxscore_data: ESPN boxscore API response
        game_id: ESPN game ID
        game_date: Date of the game
        
    Returns:
        List of player stat records
    """
    player_stats = []
    
    # Navigate to boxscore players data
    boxscore = boxscore_data.get('boxscore', {})
    teams = boxscore.get('players', [])
    
    if not teams:
        print(f"    No player data found in boxscore for game {game_id}")
        return player_stats
    
    # Extract team info for both teams first (to determine opponent)
    team_info_list = []
    for team_data in teams:
        team_info = team_data.get('team', {})
        team_info_list.append({
            'name': team_info.get('displayName', 'Unknown Team'),
            'id': str(team_info.get('id', ''))
        })
    
    # Also extract injured/out players from the injuries section
    injuries = boxscore_data.get('injuries', [])
    for injury_entry in injuries:
        team_info = injury_entry.get('team', {})
        team_name = team_info.get('displayName', 'Unknown Team')
        team_id = str(team_info.get('id', ''))
        
        # Find opponent
        opponent_team_name = 'Unknown'
        opponent_team_id = ''
        for ti in team_info_list:
            if ti['id'] != team_id:
                opponent_team_name = ti['name']
                opponent_team_id = ti['id']
                break
        
        # Process each injured/out player
        for injury_detail in injury_entry.get('injuries', []):
            athlete = injury_detail.get('athlete', {})
            status = injury_detail.get('status', '')
            
            espn_player_id = str(athlete.get('id', ''))
            player_name = athlete.get('displayName', '')
            
            if espn_player_id and player_name and status == 'Out':
                # Add DNP record for injured/out player
                player_record = {
                    'espn_player_id': espn_player_id,
                    'player_name': player_name,
                    'athlete_data': athlete,
                    'event_id': game_id,
                    'game_date': game_date,
                    'team_name': team_name,
                    'team_id': team_id,
                    'opponent_team_name': opponent_team_name,
                    'opponent_team_id': opponent_team_id,
                    'did_not_play': True,
                    'actual_points': None,
                    'actual_rebounds': None,
                    'actual_assists': None,
                    'actual_threes': None,
                    'actual_minutes': None,
                    'actual_fg': None,
                    'actual_ft': None,
                    'actual_plus_minus': None,
                }
                player_stats.append(player_record)
        team_info = team_data.get('team', {})
        team_info_list.append({
            'name': team_info.get('displayName', 'Unknown Team'),
            'id': str(team_info.get('id', ''))
        })
    
    for idx, team_data in enumerate(teams):
        team_info = team_data.get('team', {})
        team_name = team_info.get('displayName', 'Unknown Team')
        team_id = str(team_info.get('id', ''))
        
        # Determine opponent (the other team)
        opponent_idx = 1 - idx  # 0 -> 1, 1 -> 0
        opponent_team_name = team_info_list[opponent_idx]['name'] if opponent_idx < len(team_info_list) else 'Unknown'
        opponent_team_id = team_info_list[opponent_idx]['id'] if opponent_idx < len(team_info_list) else ''
        
        print(f"    Processing {team_name} players...")
        
        # Get player statistics
        statistics = team_data.get('statistics', [])
        if not statistics:
            print(f"      No statistics found for {team_name}")
            continue
        
        # Usually the first stats group contains the main game stats
        main_stats = statistics[0] if statistics else {}
        athletes = main_stats.get('athletes', [])
        stat_names = main_stats.get('names', [])
        
        if not athletes or not stat_names:
            print(f"      No athlete data found for {team_name}")
            continue
        
        print(f"      Found {len(athletes)} players with stats")
        
        for athlete_data in athletes:
            try:
                athlete = athlete_data.get('athlete', {})
                stats = athlete_data.get('stats', [])
                did_not_play = athlete_data.get('didNotPlay', False)
                
                # Extract athlete info
                espn_player_id = str(athlete.get('id', ''))
                player_name = athlete.get('displayName', '')
                
                if not espn_player_id or not player_name:
                    continue
                
                # Handle DNP players (no stats, just mark them as DNP)
                if did_not_play or not stats:
                    player_record = {
                        'espn_player_id': espn_player_id,
                        'player_name': player_name,
                        'athlete_data': athlete,
                        'event_id': game_id,
                        'game_date': game_date,
                        'team_name': team_name,
                        'team_id': team_id,
                        'opponent_team_name': opponent_team_name,
                        'opponent_team_id': opponent_team_id,
                        'did_not_play': True,
                        'actual_points': None,
                        'actual_rebounds': None,
                        'actual_assists': None,
                        'actual_threes': None,
                        'actual_minutes': None,
                        'actual_fg': None,
                        'actual_ft': None,
                        'actual_plus_minus': None,
                    }
                    player_stats.append(player_record)
                    continue
                
                # Map stats to dictionary
                if len(stats) != len(stat_names):
                    print(f"        Warning: Stat mismatch for {player_name}")
                    continue
                
                stat_dict = dict(zip(stat_names, stats))
                
                # Extract key stats (handle missing gracefully)
                player_record = {
                    'espn_player_id': espn_player_id,
                    'player_name': player_name,
                    'athlete_data': athlete,  # Full athlete object for resolver
                    'event_id': game_id,
                    'game_date': game_date,
                    'team_name': team_name,
                    'team_id': team_id,
                    'opponent_team_name': opponent_team_name,
                    'opponent_team_id': opponent_team_id,
                    'did_not_play': False,
                    
                    # Core stats
                    'actual_points': safe_int(stat_dict.get('PTS')),
                    'actual_rebounds': safe_int(stat_dict.get('REB')),
                    'actual_assists': safe_int(stat_dict.get('AST')),
                    'actual_threes': safe_int(stat_dict.get('3PT', '').split('-')[0] if '3PT' in stat_dict else None),
                    
                    # Additional stats
                    'actual_minutes': stat_dict.get('MIN', ''),
                    'actual_fg': stat_dict.get('FG', ''),
                    'actual_ft': stat_dict.get('FT', ''),
                    'actual_plus_minus': safe_int(stat_dict.get('+/-')),
                }
                
                player_stats.append(player_record)
                
            except Exception as e:
                print(f"        Error processing player stats: {e}")
                continue
    
    return player_stats


def normalize_player_name(name: str) -> str:
    """
    Normalize player name to match the format used in odds ingestion.
    This removes apostrophes, hyphens, periods, and collapses whitespace.
    
    Args:
        name: Raw player name (e.g., "De'Aaron Fox", "Karl-Anthony Towns")
        
    Returns:
        Normalized name (e.g., "deaaron fox", "karlanthony towns")
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


def normalize_player_name(name: str) -> str:
    """
    Normalize player name to match the format used in odds ingestion.
    This removes apostrophes, hyphens, periods, and collapses whitespace.
    
    Args:
        name: Raw player name (e.g., "De'Aaron Fox", "Karl-Anthony Towns")
        
    Returns:
        Normalized name (e.g., "deaaron fox", "karlanthony towns")
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
    Remove common name suffixes for fuzzy matching.
    
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


def get_last_name(normalized_name: str) -> str:
    """
    Extract last name from normalized player name.
    
    Args:
        normalized_name: Normalized player name (e.g., "lebron james")
        
    Returns:
        Last name (e.g., "james")
    """
    parts = normalized_name.strip().split()
    return parts[-1] if parts else ''


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


def resolve_team_id(conn, espn_team_id: str, espn_team_name: str) -> Optional[int]:
    """
    Resolve ESPN team ID to internal team_id from teams table.
    
    Args:
        conn: Database connection
        espn_team_id: ESPN team ID (e.g., "11" for Pacers)
        espn_team_name: Team name from ESPN for logging (e.g., "Indiana Pacers")
        
    Returns:
        team_id from teams table if found, None otherwise
    """
    try:
        # Look up by ESPN team ID
        result = conn.execute(text("""
            SELECT team_id, team_name FROM teams 
            WHERE espn_team_id = :espn_team_id AND sport = 'NBA'
        """), {'espn_team_id': espn_team_id}).fetchone()
        
        if result:
            return result[0]
        
        print(f"    ⚠️ Could not resolve team: {espn_team_name} (ESPN ID: {espn_team_id})")
        return None
        
    except Exception as e:
        print(f"    ❌ Error resolving team {espn_team_name}: {e}")
        return None


def test_single_game(event_id: str, odds_date: Optional[date] = None):
    """
    Test function to process a single game by event ID.
    
    Args:
        event_id: ESPN event ID to test
        odds_date: Optional date to use for matching odds (if different from game date)
    """
    print(f"=== Testing Single Game Import: Event {event_id} ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Fetch the boxscore (no PlayerResolver needed for this part)
        print(f"\nFetching boxscore for event {event_id}...")
        boxscore_data = get_game_boxscore(event_id)
        
        if not boxscore_data:
            print(f"❌ Could not fetch boxscore for event {event_id}")
            return
        
        # Get game date from boxscore
        header = boxscore_data.get('header', {})
        competition = header.get('competitions', [{}])[0]
        game_date_str = competition.get('date', '')
        
        if game_date_str:
            game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00')).date()
        else:
            game_date = date.today()
        
        print(f"Game date from ESPN: {game_date}")
        
        # Use odds_date if provided (for matching odds records)
        if odds_date:
            print(f"Using odds date for matching: {odds_date}")
            game_date = odds_date
            
            # Get team names for display
            competitors = competition.get('competitors', [])
            team_names = [team.get('team', {}).get('displayName', 'Unknown') for team in competitors]
            print(f"Game: {' vs '.join(team_names)}")
            
            # Extract player stats
            player_stats = extract_player_stats_from_boxscore(boxscore_data, event_id, game_date)
            
            if not player_stats:
                print("❌ No player stats found in boxscore")
                return
            
            print(f"\n✅ Extracted stats for {len(player_stats)} players")
            
        # Update player props with actuals (no PlayerResolver needed - we're not creating players)
        updated = update_player_props_with_actuals_simple(conn, player_stats)
        
        # Commit transaction
        conn.commit()
        print(f"\n✅ Successfully updated {updated} player prop records")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        conn.close()


def update_player_props_with_actuals_simple(conn, player_stats: List[Dict]):
    """
    Update nba_player_props records with actual game statistics.
    Uses fuzzy matching with team verification for unmatched players.
    
    Args:
        conn: Database connection
        player_stats: List of player stat records from ESPN
    """
    print(f"Updating player props with {len(player_stats)} player stat records...")
    
    updated_count = 0
    fuzzy_matched_count = 0
    
    for stat_record in player_stats:
        try:
            # Normalize player name for matching (same logic as odds ingestion)
            espn_player_name = stat_record['player_name']
            normalized_name = normalize_player_name(espn_player_name)
            espn_team_name = stat_record['team_name']
            espn_player_id = stat_record['athlete_data'].get('id')
            
            # Resolve team IDs from ESPN team IDs
            team_id = resolve_team_id(conn, stat_record['team_id'], stat_record['team_name'])
            opponent_team_id = resolve_team_id(conn, stat_record['opponent_team_id'], stat_record['opponent_team_name'])
            
            existing = None
            
            # Step 1: Try espn_player_id lookup first (fastest, most reliable)
            if espn_player_id:
                existing = conn.execute(text("""
                    SELECT pp.id, pp.player_id, pp.odds_home_team_id, pp.odds_away_team_id 
                    FROM nba_player_props pp
                    JOIN nba_players p ON pp.player_id = p.id
                    WHERE p.espn_player_id = :espn_player_id AND pp.game_date = :game_date
                """), {
                    'espn_player_id': str(espn_player_id),
                    'game_date': stat_record['game_date']
                }).fetchone()
                
                if existing:
                    print(f"  ⚡ Fast ID match: {espn_player_name} (ESPN ID: {espn_player_id})")
            
            # Step 2: If not found by ID, try direct normalized_name match
            if not existing:
                existing = conn.execute(text("""
                    SELECT id, player_id, odds_home_team_id, odds_away_team_id FROM nba_player_props
                    WHERE normalized_name = :normalized_name AND game_date = :game_date
                """), {
                    'normalized_name': normalized_name,
                    'game_date': stat_record['game_date']
                }).fetchone()
            
            # Step 3: If still not found, try fuzzy matching with team ID verification
            if not existing:
                # Strip suffixes first, then extract last name
                name_without_suffix = strip_name_suffix(normalized_name)
                last_name = get_last_name(name_without_suffix)
                
                if last_name and team_id:
                    # Find props with matching last name on same date
                    # Check if last name appears in the name (handles suffixes on either side)
                    fuzzy_candidates = conn.execute(text("""
                        SELECT id, player_id, normalized_name, odds_home_team_id, odds_away_team_id 
                        FROM nba_player_props
                        WHERE game_date = :game_date 
                        AND (
                            normalized_name LIKE :last_name_pattern_end
                            OR normalized_name LIKE :last_name_pattern_middle
                            OR normalized_name = :name_without_suffix
                        )
                        AND (odds_home_team_id = :team_id OR odds_away_team_id = :team_id)
                    """), {
                        'game_date': stat_record['game_date'],
                        'last_name_pattern_end': f'% {last_name}',  # Ends with last name (no suffix)
                        'last_name_pattern_middle': f'% {last_name} %',  # Last name in middle (has suffix)
                        'name_without_suffix': name_without_suffix,
                        'team_id': team_id
                    }).fetchall()
                    
                    # Use fuzzy match only if exactly 1 valid candidate
                    if len(fuzzy_candidates) == 1:
                        existing = fuzzy_candidates[0]
                        fuzzy_matched_count += 1
                        print(f"  🔍 Fuzzy matched: ESPN '{espn_player_name}' → Odds '{existing[2]}' (team ID verified)")
            
            if existing:
                # Found existing props record (direct or fuzzy match)
                props_id = existing[0]
                existing_player_id = existing[1]
                
                # Backfill ESPN ID if we have it and it's not set yet
                if espn_player_id and existing_player_id:
                    # Check if player already has ESPN ID
                    player_info = conn.execute(text("""
                        SELECT espn_player_id FROM nba_players WHERE id = :player_id
                    """), {'player_id': existing_player_id}).fetchone()
                    
                    if player_info and not player_info[0]:
                        # Update player with ESPN ID for faster future lookups
                        conn.execute(text("""
                            UPDATE nba_players
                            SET espn_player_id = :espn_player_id
                            WHERE id = :player_id
                        """), {
                            'espn_player_id': str(espn_player_id),
                            'player_id': existing_player_id
                        })
                        print(f"    💾 Backfilled ESPN ID {espn_player_id} for future fast lookups")
                
                # Check if this is a DNP (did not play) record
                is_dnp = stat_record.get('did_not_play', False)
                
                if is_dnp:
                    # Update with ESPN event ID and mark as DNP (no stats)
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
                        'team_name': stat_record['team_name'],
                        'team_id': team_id,
                        'opponent_team_name': stat_record['opponent_team_name'],
                        'opponent_team_id': opponent_team_id,
                        'espn_event_id': stat_record['event_id'],
                        'record_id': props_id
                    })
                    print(f"  🚫 DNP: {espn_player_name} (event_id: {stat_record['event_id']})")
                else:
                    # Update existing props record with actual stats and team info
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
                        'points': stat_record['actual_points'],
                        'rebounds': stat_record['actual_rebounds'],
                        'assists': stat_record['actual_assists'],
                        'threes': stat_record['actual_threes'],
                        'minutes': stat_record['actual_minutes'],
                        'fg': stat_record['actual_fg'],
                        'ft': stat_record['actual_ft'],
                        'plus_minus': stat_record['actual_plus_minus'],
                        'team_name': stat_record['team_name'],
                        'team_id': team_id,
                        'opponent_team_name': stat_record['opponent_team_name'],
                        'opponent_team_id': opponent_team_id,
                        'espn_event_id': stat_record['event_id'],
                        'record_id': props_id
                    })
                    print(f"  ✅ Updated {espn_player_name}: {stat_record['actual_points']}pts/{stat_record['actual_rebounds']}reb/{stat_record['actual_assists']}ast")
                updated_count += 1
                # Commit after each successful update to avoid transaction poisoning
                conn.commit()
                
            else:
                # No existing nba_player_props record - this means we didn't have odds for this player
                print(f"  ℹ️ No props record found for {espn_player_name} on {stat_record['game_date']} (event_id: {stat_record['event_id']}, no odds were available)")
                
        except Exception as e:
            print(f"  ❌ Error updating {stat_record.get('player_name', 'unknown')}: {e}")
            # Rollback the failed transaction
            conn.rollback()
            continue
    
    print(f"Successfully updated {updated_count} player prop records with actuals")
    if fuzzy_matched_count > 0:
        print(f"  (Including {fuzzy_matched_count} fuzzy-matched players)")
    return updated_count


def seed_yesterdays_player_actuals():
    """
    Fetch yesterday's completed NBA games and update player props with actual stats.
    """
    print("=== NBA Player Props Actuals Ingestion (Yesterday) ===\n")
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Get yesterday's completed games
        games = get_yesterdays_nba_games()
        
        if not games:
            print("No completed NBA games found for yesterday")
            return
        
        # Initialize player resolver
        with PlayerResolver(conn) as resolver:
            
            total_player_stats = []
            
            # Process each game
            for i, game in enumerate(games, 1):
                game_id = game.get('id')
                competitors = game.get('competitions', [{}])[0].get('competitors', [])
                
                # Get team names for display
                team_names = []
                for team in competitors:
                    team_names.append(team.get('team', {}).get('displayName', 'Unknown'))
                
                print(f"\nProcessing game {i}/{len(games)}: {' vs '.join(team_names)} (ID: {game_id})")
                
                try:
                    # Get game date and convert to Eastern Time for matching odds
                    eastern = pytz.timezone('US/Eastern')
                    game_dt_utc = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
                    game_dt_et = game_dt_utc.astimezone(eastern)
                    game_date_et = game_dt_et.date()
                    
                    print(f"  Game time: {game_dt_et.strftime('%Y-%m-%d %I:%M %p')} ET")
                    
                    # Fetch detailed boxscore
                    boxscore_data = get_game_boxscore(game_id)
                    
                    if boxscore_data:
                        # Extract player stats (use ET date for matching odds)
                        game_stats = extract_player_stats_from_boxscore(
                            boxscore_data, game_id, game_date_et
                        )
                        total_player_stats.extend(game_stats)
                        print(f"  Extracted stats for {len(game_stats)} players")
                    else:
                        print(f"  Could not get boxscore data for game {game_id}")
                    
                    # Rate limiting - be nice to ESPN
                    if i < len(games):
                        time.sleep(2)
                        
                except Exception as e:
                    print(f"  Error processing game {game_id}: {e}")
                    continue
            
            print(f"\nTotal player stat records: {len(total_player_stats)}")
            
            if total_player_stats:
                # Update player_props records with actuals using the new fuzzy matching logic
                updated = update_player_props_with_actuals_simple(conn, total_player_stats)
                
                # Commit transaction
                conn.commit()
                print(f"\n✅ Successfully updated {updated} player prop records with actual results")
            else:
                print("❌ No player stats data found to update")
        
    except Exception as e:
        print(f"❌ Error during player actuals ingestion: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def seed_player_actuals_for_date(target_date: str):
    """
    Fetch NBA games for a specific date (Eastern Time) and update player props with actual stats.
    
    Args:
        target_date: Date string in format 'YYYY-MM-DD' (e.g., '2025-01-08')
    """
    print(f"=== NBA Player Props Actuals Ingestion for {target_date} (Eastern Time) ===\n")
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Get games for the specific date in Eastern Time
        games = get_nba_games_for_date_et(target_date)
        
        if not games:
            print(f"No completed NBA games found for {target_date}")
            return
        
        # Initialize player resolver
        with PlayerResolver(conn) as resolver:
            
            total_player_stats = []
            
            # Process each game
            for i, game in enumerate(games, 1):
                game_id = game.get('id')
                competitors = game.get('competitions', [{}])[0].get('competitors', [])
                
                # Get team names for display
                team_names = []
                for team in competitors:
                    team_names.append(team.get('team', {}).get('displayName', 'Unknown'))
                
                print(f"\nProcessing game {i}/{len(games)}: {' vs '.join(team_names)} (ID: {game_id})")
                
                try:
                    # Get game date
                    game_date = datetime.fromisoformat(
                        game['date'].replace('Z', '+00:00')
                    ).date()
                    
                    # For matching odds records, we want to use the Eastern Time date
                    eastern = pytz.timezone('US/Eastern')
                    game_dt_utc = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
                    game_dt_et = game_dt_utc.astimezone(eastern)
                    game_date_et = game_dt_et.date()
                    
                    print(f"  Game time: {game_dt_et.strftime('%Y-%m-%d %I:%M %p')} ET")
                    
                    # Fetch detailed boxscore
                    boxscore_data = get_game_boxscore(game_id)
                    
                    if boxscore_data:
                        # Extract player stats (use ET date for matching odds)
                        game_stats = extract_player_stats_from_boxscore(
                            boxscore_data, game_id, game_date_et
                        )
                        total_player_stats.extend(game_stats)
                        print(f"  Extracted stats for {len(game_stats)} players")
                    else:
                        print(f"  Could not get boxscore data for game {game_id}")
                    
                    # Rate limiting - be nice to ESPN
                    if i < len(games):
                        time.sleep(2)
                        
                except Exception as e:
                    print(f"  Error processing game {game_id}: {e}")
                    continue
            
            print(f"\nTotal player stat records: {len(total_player_stats)}")
            
            if total_player_stats:
                # Update player_props records with actuals using the new fuzzy matching logic
                updated = update_player_props_with_actuals_simple(conn, total_player_stats)
                
                # Commit transaction
                conn.commit()
                print(f"\n✅ Successfully updated {updated} player prop records with actual results for {target_date}")
            else:
                print("❌ No player stats data found to update")
        
    except Exception as e:
        print(f"❌ Error during player actuals ingestion: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    # Usage:
    #   python nba_player_props_actuals_ingestion.py                     # Import yesterday's games
    #   python nba_player_props_actuals_ingestion.py 2025-01-08          # Import all games for specific date (ET)
    #   python nba_player_props_actuals_ingestion.py <event_id> <date>   # Import single game (old behavior)
    
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        
        # Check if first argument is a date (YYYY-MM-DD format)
        if '-' in first_arg and len(first_arg) == 10:
            # It's a date - import all games for that date in Eastern Time
            target_date = first_arg
            seed_player_actuals_for_date(target_date)
        else:
            # It's an event ID - old behavior for testing single game
            event_id = first_arg
            # Optional: provide odds date as second argument (format: YYYY-MM-DD)
            odds_date = None
            if len(sys.argv) > 2:
                from datetime import datetime
                odds_date = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
            test_single_game(event_id, odds_date)
    else:
        # No arguments - import yesterday's games
        seed_yesterdays_player_actuals()