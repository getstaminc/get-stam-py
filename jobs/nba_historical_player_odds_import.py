#!/usr/bin/python3

import os
import sys
import requests
import time
import pytz
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", 'e143ef401675904470a5b72e6145091a')


def get_historical_nba_events(target_date: date, retries=3, delay=2) -> List[str]:
    """
    Get all NBA event IDs for a specific historical date.
    
    Args:
        target_date: Date to fetch events for
        retries: Number of retry attempts
        delay: Delay between retries
        
    Returns:
        List of event IDs for that date
    """
    print(f"Fetching NBA events for {target_date}...")
    
    # Format date as required by historical API
    date_str = target_date.strftime('%Y-%m-%d')
    
    url = f"https://api.the-odds-api.com/v4/historical/sports/basketball_nba/events"
    params = {
        'apiKey': ODDS_API_KEY,
        'date': f"{date_str}T12:00:00Z"  # Noon UTC to catch games
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            events_data = response.json()
            
            if isinstance(events_data, dict) and 'data' in events_data:
                events = events_data['data']
            elif isinstance(events_data, list):
                events = events_data
            else:
                print(f"  Unexpected API response format: {type(events_data)}")
                return []
            
            # Return full event data (with commence_time) for timezone conversion
            print(f"  Found {len(events)} NBA events for {target_date}")
            return events
            
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching events (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay * (i + 1))  # Exponential backoff
            else:
                print(f"  Failed to fetch events for {target_date}")
                return []
    
    return []


def get_historical_player_odds(event_id: str, target_date: date, retries=3, delay=2) -> Optional[Dict]:
    """
    Get historical player prop odds for a specific event.
    
    Args:
        event_id: Odds API event ID  
        target_date: Date of the event
        retries: Number of retry attempts
        delay: Delay between retries
        
    Returns:
        Player odds data or None if failed/unavailable
    """
    print(f"    Fetching player odds for event {event_id}...")
    
    # Enhanced: Try multiple times (5 min before, exact, 1 min after commence_time)
    commence_time = None
    today_events = get_historical_nba_events(target_date)
    for event in today_events:
        if event.get('id') == event_id:
            commence_time = event.get('commence_time')
            break
    if not commence_time:
        print(f"      Could not find commence_time for event {event_id}, using fallback time.")
        date_str = target_date.strftime('%Y-%m-%d')
        times_to_try = [f"{date_str}T22:45:00Z"]
    else:
        commence_dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
        times_to_try = [
            (commence_dt - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            commence_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            (commence_dt + timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        ]
    url = f"https://api.the-odds-api.com/v4/historical/sports/basketball_nba/events/{event_id}/odds"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebSever/537.36"
    }
    for odds_query_time in times_to_try:
        params = {
            'apiKey': ODDS_API_KEY,
            'date': odds_query_time,
            'regions': 'us',
            'markets': 'player_points,player_rebounds,player_assists,player_threes',
            'oddsFormat': 'decimal',
            'bookmakers': 'draftkings'
        }
        for i in range(retries):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 422:
                    print(f"      No player odds available for event {event_id} at {odds_query_time}")
                    break
                response.raise_for_status()
                response_data = response.json()
                if isinstance(response_data, dict) and 'data' in response_data:
                    odds_data = response_data['data']
                else:
                    odds_data = response_data
                if not odds_data or not odds_data.get('bookmakers'):
                    print(f"      No bookmaker data for event {event_id} at {odds_query_time}")
                    break
                print(f"      ✅ Found player odds for event {event_id} at {odds_query_time}")
                return odds_data
            except requests.exceptions.RequestException as e:
                print(f"      Error fetching odds (attempt {i+1}/{retries}) at {odds_query_time}: {e}")
                if i < retries - 1:
                    time.sleep(delay * (i + 1))
                else:
                    print(f"      Failed to get odds for event {event_id} at {odds_query_time}")
    return None


def parse_historical_player_props(odds_data: Dict, commence_time: str) -> List[Dict]:
    """
    Parse historical player props from odds data.
    New format: outcomes have 'name' (Over/Under), 'description' (player name), 'price', 'point'
    
    Args:
        odds_data: Historical odds API response
        commence_time: ISO timestamp of when the event starts
        
    Returns:
        List of player prop records
    """
    # Convert commence time to Eastern Time to get correct game date
    game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
    eastern = pytz.timezone('US/Eastern')
    game_start_et = game_start.astimezone(eastern)
    game_date = game_start_et.date()
    props = []
    
    if not odds_data.get('bookmakers'):
        return props
    
    # Find DraftKings bookmaker
    draftkings_data = None
    for bookmaker in odds_data['bookmakers']:
        if bookmaker['key'] == 'draftkings':
            draftkings_data = bookmaker
            break
    
    if not draftkings_data or not draftkings_data.get('markets'):
        return props
    
    # Event info
    event_id = odds_data['id']
    home_team = odds_data.get('home_team', '')
    away_team = odds_data.get('away_team', '')
    
    # Process each market
    for market in draftkings_data['markets']:
        market_key = market['key']
        
        if not market_key.startswith('player_'):
            continue
        
        stat_type = market_key.replace('player_', '')
        
        # New format: outcomes contain 'name' (Over/Under) and 'description' (player name)
        outcomes = market.get('outcomes', [])
        
        # Group by player name, then find over/under pairs
        players_data = {}
        
        for outcome in outcomes:
            bet_side = (outcome.get('name') or '').strip().lower()
            player_name = outcome.get('description', '')
            point = outcome.get('point')
            price = outcome.get('price')
            
            if not player_name or point is None:
                continue
            
            # Initialize player record
            if player_name not in players_data:
                players_data[player_name] = {
                    'player_name': player_name,
                    'event_id': event_id,
                    'game_date': game_date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'bookmaker': 'draftkings',
                    'stat_type': stat_type,
                    'line': point,
                    'over_price': None,
                    'under_price': None
                }
            
            # Assign over/under price
            player_record = players_data[player_name]
            if bet_side == 'over':
                player_record['over_price'] = price
                if player_record['line'] is None:
                    player_record['line'] = point
            elif bet_side == 'under':
                player_record['under_price'] = price
                if player_record['line'] is None:
                    player_record['line'] = point
        
        # Add completed records with at least one price
        for player_record in players_data.values():
            if player_record['over_price'] is not None:
                props.append(player_record)
    
    return props


def normalize_name_simple(name: str) -> str:
    """Simple name normalization"""
    if not name:
        return ""
    return name.lower().strip().replace("'", "").replace("-", "").replace(".", "")


def resolve_team_id_from_odds_api(conn, odds_team_name: str) -> Optional[int]:
    """
    Resolve team_id from odds_api_team_name in teams table.
    """
    try:
        result = conn.execute(text("""
            SELECT team_id FROM teams 
            WHERE odds_api_team_name = :odds_team_name AND sport = 'NBA'
        """), {'odds_team_name': odds_team_name}).fetchone()
        
        if result:
            return result[0]
        
        print(f"    ⚠️ Could not resolve team: {odds_team_name}")
        return None
        
    except Exception as e:
        print(f"    ❌ Error resolving team {odds_team_name}: {e}")
        return None


def resolve_player_simple(conn, player_name: str, game_date: date) -> Optional[int]:
    """
    Player resolver that checks aliases first, then creates new players if needed.
    """
    normalized = normalize_name_simple(player_name)
    
    try:
        # Step 1: Check aliases first (most reliable for name variations)
        alias_result = conn.execute(text("""
            SELECT player_id FROM nba_player_aliases 
            WHERE normalized_name = :name
            ORDER BY created_at DESC
            LIMIT 1
        """), {'name': normalized}).fetchone()
        
        if alias_result:
            print(f"    ✓ Found via alias: {player_name} -> player_id {alias_result[0]}")
            return alias_result[0]
        
        # Step 2: Check nba_players table by normalized name
        player_result = conn.execute(text("""
            SELECT id FROM nba_players WHERE normalized_name = :name
        """), {'name': normalized}).fetchone()
        
        if player_result:
            # Found existing player - add this name as an alias for future lookups
            conn.execute(text("""
                INSERT INTO nba_player_aliases (player_id, source, source_name, normalized_name, created_at)
                VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
                ON CONFLICT (source, normalized_name) DO NOTHING
            """), {
                'player_id': player_result[0],
                'source_name': player_name,
                'normalized_name': normalized
            })
            print(f"    ✓ Found existing player and added alias: {player_name} -> player_id {player_result[0]}")
            return player_result[0]
        
        # Step 3: Create new player (no existing match found)
        new_player_result = conn.execute(text("""
            INSERT INTO nba_players (player_name, normalized_name, first_seen_date, last_seen_date, created_at, updated_at)
            VALUES (:player_name, :normalized_name, :first_seen_date, :last_seen_date, NOW(), NOW())
            RETURNING id
        """), {
            'player_name': player_name,
            'normalized_name': normalized,
            'first_seen_date': game_date,
            'last_seen_date': game_date
        })
        
        player_id = new_player_result.fetchone()[0]
        
        # Create alias for the new player
        conn.execute(text("""
            INSERT INTO nba_player_aliases (player_id, source, source_name, normalized_name, created_at)
            VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
            ON CONFLICT (source, normalized_name) DO NOTHING
        """), {
            'player_id': player_id,
            'source_name': player_name,
            'normalized_name': normalized
        })
        
        print(f"    ➕ Created new player: {player_name} (ID: {player_id})")
        return player_id
        
    except Exception as e:
        print(f"    ❌ Error resolving player {player_name}: {e}")
        return None


def insert_historical_props_to_db(conn, props_data: List[Dict]) -> int:
    """
    Insert historical player props to database.
    """
    inserted_count = 0
    
    for prop in props_data:
        try:
            # Resolve player
            player_id = resolve_player_simple(conn, prop['player_name'], prop['game_date'])
            
            if not player_id:
                print(f"    Skipping {prop['player_name']} - could not resolve")
                continue
            
            # Resolve team IDs
            home_team_id = resolve_team_id_from_odds_api(conn, prop['home_team'])
            away_team_id = resolve_team_id_from_odds_api(conn, prop['away_team'])
            
            # Map stat types to columns
            stat_columns = {
                'points': ('odds_player_points', 'odds_player_points_over_price', 'odds_player_points_under_price'),
                'rebounds': ('odds_player_rebounds', 'odds_player_rebounds_over_price', 'odds_player_rebounds_under_price'),
                'assists': ('odds_player_assists', 'odds_player_assists_over_price', 'odds_player_assists_under_price'),
                'threes': ('odds_player_threes', 'odds_player_threes_over_price', 'odds_player_threes_under_price')
            }
            
            if prop['stat_type'] not in stat_columns:
                continue
            
            line_col, over_col, under_col = stat_columns[prop['stat_type']]
            
            # Convert decimal odds to American format
            over_price_american = decimal_to_american(prop['over_price']) if prop['over_price'] else None
            under_price_american = decimal_to_american(prop['under_price']) if prop['under_price'] else None
            
            # Check if record exists
            existing = conn.execute(text("""
                SELECT id FROM nba_player_props 
                WHERE player_id = :player_id AND odds_event_id = :odds_event_id
            """), {
                'player_id': player_id,
                'odds_event_id': prop['event_id']
            }).fetchone()
            
            if existing:
                # Update existing record
                update_sql = f"""
                    UPDATE nba_player_props 
                    SET {line_col} = :line,
                        {over_col} = :over_price,
                        {under_col} = :under_price,
                        normalized_name = (SELECT normalized_name FROM nba_players WHERE id = :player_id),
                        odds_home_team = :odds_home_team,
                        odds_away_team = :odds_away_team,
                        odds_home_team_id = :odds_home_team_id,
                        odds_away_team_id = :odds_away_team_id,
                        updated_at = NOW()
                    WHERE id = :record_id
                """
                
                conn.execute(text(update_sql), {
                    'line': prop['line'],
                    'over_price': over_price_american,
                    'under_price': under_price_american,
                    'player_id': player_id,
                    'odds_home_team': prop['home_team'],
                    'odds_away_team': prop['away_team'],
                    'odds_home_team_id': home_team_id,
                    'odds_away_team_id': away_team_id,
                    'record_id': existing[0]
                })
            else:
                # Insert new record
                insert_sql = f"""
                    INSERT INTO nba_player_props (
                        player_id, normalized_name, odds_event_id, game_date, bookmaker, odds_source,
                        odds_home_team, odds_away_team, odds_home_team_id, odds_away_team_id,
                        {line_col}, {over_col}, {under_col}
                    ) VALUES (
                        :player_id, 
                        (SELECT normalized_name FROM nba_players WHERE id = :player_id),
                        :odds_event_id, :game_date, :bookmaker, :odds_source,
                        :odds_home_team, :odds_away_team, :odds_home_team_id, :odds_away_team_id,
                        :line, :over_price, :under_price
                    )
                """
                
                conn.execute(text(insert_sql), {
                    'player_id': player_id,
                    'odds_event_id': prop['event_id'],
                    'game_date': prop['game_date'],
                    'bookmaker': prop['bookmaker'],
                    'odds_source': 'odds_api',
                    'odds_home_team': prop['home_team'],
                    'odds_away_team': prop['away_team'],
                    'odds_home_team_id': home_team_id,
                    'odds_away_team_id': away_team_id,
                    'line': prop['line'],
                    'over_price': over_price_american,
                    'under_price': under_price_american
                })
                
                inserted_count += 1
                
        except Exception as e:
            print(f"    Error processing {prop.get('player_name', 'unknown')}: {e}")
            continue
    
    return inserted_count


def decimal_to_american(decimal_odds: float) -> int:
    """
    Convert decimal odds to American format.
    """
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))


def import_historical_player_odds_for_date(target_date: date, conn) -> int:
    """
    Import all historical player odds for a specific date.
    
    Args:
        target_date: Date to import
        conn: Database connection
        
    Returns:
        Number of player prop records imported
    """
    print(f"\n=== Importing Historical Player Odds for {target_date} ===")
    
    # Step 1: Get all events for the date (now returns full event objects)
    events = get_historical_nba_events(target_date)
    
    if not events:
        print(f"No events found for {target_date}")
        return 0
    
    # Step 2: Filter events to only include games on the target date (in ET)
    eastern = pytz.timezone('US/Eastern')
    filtered_events = []
    
    for event in events:
        commence_time = event.get('commence_time')
        if commence_time:
            # Convert UTC commence_time to Eastern Time
            game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            game_start_et = game_start.astimezone(eastern)
            game_date_et = game_start_et.date()
            
            # Only include events where ET game date matches target date
            if game_date_et == target_date:
                filtered_events.append(event)
    
    print(f"  Filtered to {len(filtered_events)} events on {target_date} ET (from {len(events)} total API results)")
    
    if not filtered_events:
        print(f"  No events match target date {target_date} after timezone conversion")
        return 0
    
    # Step 3: Process each filtered event
    total_props_imported = 0
    
    for i, event in enumerate(filtered_events, 1):
        event_id = event.get('id')
        commence_time = event.get('commence_time')
        
        if not event_id or not commence_time:
            continue
            
        print(f"\n  Processing event {i}/{len(filtered_events)}: {event_id}")
        
        try:
            # Get player odds for this event
            odds_data = get_historical_player_odds(event_id, target_date)
            
            if not odds_data:
                continue
            
            # Parse player props (pass commence_time for timezone conversion)
            props_data = parse_historical_player_props(odds_data, commence_time)
            
            if not props_data:
                print(f"    No player props found for event {event_id}")
                continue
            
            print(f"    Found {len(props_data)} player props")
            
            # Insert to database
            inserted = insert_historical_props_to_db(conn, props_data)
            
            total_props_imported += inserted
            
            # Rate limiting - be very nice to historical API
            if i < len(filtered_events):
                time.sleep(3)  # 3 seconds between events
                
        except Exception as e:
            print(f"    Error processing event {event_id}: {e}")
            continue
    
    return total_props_imported


def import_historical_odds_date_range(start_date: date, end_date: date):
    """
    Import historical player odds for a date range.
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    """
    print(f"=== Historical NBA Player Odds Import ===")
    print(f"Date range: {start_date} to {end_date}")
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        current_date = start_date
        total_imported = 0
        
        while current_date <= end_date:
            try:
                daily_imported = import_historical_player_odds_for_date(
                    current_date, conn
                )
                
                total_imported += daily_imported
                
                # Commit daily progress
                conn.commit()
                print(f"✅ Committed {daily_imported} records for {current_date}")
                
            except Exception as e:
                print(f"❌ Error processing {current_date}: {e}")
                conn.rollback()
            
            # Move to next date
            current_date += timedelta(days=1)
            
            # Rate limiting between dates
            if current_date <= end_date:
                time.sleep(5)  # 5 seconds between dates
        
        print(f"\n🎉 Historical import complete!")
        print(f"Total player prop records imported: {total_imported}")
        print(f"Date range: {start_date} to {end_date}")
        
    except Exception as e:
        print(f"❌ Fatal error during historical import: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Import for specific date: June 12, 2023
    start_date = date(2023, 6, 12)
    end_date = date(2023, 6, 12)
    
    import_historical_odds_date_range(start_date, end_date)