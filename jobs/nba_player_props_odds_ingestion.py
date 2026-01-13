#!/usr/bin/env python3
"""
Simple NBA Player Props Ingestion - Working Version

This version avoids the transaction issues by creating fresh connections for each player resolution.
"""

import os
import time
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Configuration
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

if not ODDS_API_KEY:
    raise ValueError("ODDS_API_KEY environment variable is required")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")


def normalize_name_simple(name: str) -> str:
    """Simple name normalization"""
    if not name:
        return ""
    return name.lower().strip().replace("'", "").replace("-", "").replace(".", "")


def resolve_team_id_from_odds_api(conn, odds_team_name: str) -> Optional[int]:
    """
    Resolve team_id from odds_api_team_name in teams table.
    
    Args:
        conn: Database connection
        odds_team_name: Team name from Odds API (e.g., "Denver Nuggets")
        
    Returns:
        team_id from teams table if found, None otherwise
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


def resolve_player_simple(conn, player_name: str, game_date: date) -> int:
    """
    Simple player resolver that reuses the provided connection to avoid too many connections.
    """
    normalized = normalize_name_simple(player_name)
    
    try:
        # Step 1: Try to find existing player by normalized name
        result = conn.execute(text("""
            SELECT id FROM nba_players WHERE normalized_name = :name
        """), {'name': normalized})
        
        row = result.fetchone()
        if row:
            print(f"  Found existing player: {player_name} -> ID {row[0]}")
            return row[0]
        
        # Step 2: Create new player
        result = conn.execute(text("""
            INSERT INTO nba_players (player_name, normalized_name, first_seen_date, last_seen_date, created_at, updated_at)
            VALUES (:player_name, :normalized_name, :first_seen_date, :last_seen_date, NOW(), NOW())
            RETURNING id
        """), {
            'player_name': player_name,
            'normalized_name': normalized,
            'first_seen_date': game_date,
            'last_seen_date': game_date
        })
        
        player_id = result.fetchone()[0]
        
        # Step 3: Create alias
        conn.execute(text("""
            INSERT INTO nba_player_aliases (player_id, source, source_name, normalized_name, created_at)
            VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
        """), {
            'player_id': player_id,
            'source_name': player_name,
            'normalized_name': normalized
        })
        
        print(f"  Created new player: {player_name} -> ID {player_id}")
        return player_id
        
    except Exception as e:
        print(f"  Error resolving {player_name}: {e}")
        return None


def get_upcoming_nba_games(hours_ahead=6) -> List[Dict]:
    """Get upcoming NBA games"""
    print(f"Fetching NBA games in next {hours_ahead} hours...")
    
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h',
        'oddsFormat': 'american'
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 422:
            print("No NBA games available in the next few days (422 response)")
            return []
        
        response.raise_for_status()
        games_data = response.json()
        
        # Filter for games in next X hours
        now = datetime.utcnow().replace(tzinfo=None)
        cutoff_time = now + timedelta(hours=hours_ahead)
        upcoming_games = []
        
        for game in games_data:
            game_start = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            game_start_naive = game_start.replace(tzinfo=None)
            
            if now < game_start_naive <= cutoff_time and game.get('bookmakers'):
                upcoming_games.append({
                    'id': game['id'],
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'commence_time': game['commence_time'],
                    'game_start': game_start
                })
                game_date_str = game_start.strftime('%Y-%m-%d %H:%M UTC')
                print(f"  Found: {game['away_team']} @ {game['home_team']} ({game_date_str}) - Event ID: {game['id']}")
        
        print(f"Found {len(upcoming_games)} upcoming NBA games")
        return upcoming_games
        
    except Exception as e:
        print(f"Error fetching games: {e}")
        return []


def fetch_player_props_for_event(event_id: str) -> Optional[Dict]:
    """Fetch player props for a specific event"""
    print(f"  Fetching player props for event {event_id}...")
    
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'player_points,player_rebounds,player_assists,player_threes',
        'oddsFormat': 'american',
        'bookmakers': 'draftkings,fanduel'
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 422:
            print(f"    No player props available for event {event_id}")
            return None
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"    Error fetching player props for {event_id}: {e}")
        return None


def parse_player_props_from_game(game: Dict) -> List[Dict]:
    """Extract player props from game data"""
    props = []
    
    if not game.get('bookmakers'):
        return props
    
    # Choose preferred bookmaker
    preferred_books = ['draftkings', 'fanduel', 'bovada', 'betmgm']
    selected_bookmaker = None
    selected_book_key = None
    
    for pb in preferred_books:
        for bookmaker in game['bookmakers']:
            if bookmaker.get('key') == pb and bookmaker.get('markets'):
                if any(m.get('key', '').startswith('player_') for m in bookmaker.get('markets', [])):
                    selected_bookmaker = bookmaker
                    selected_book_key = pb
                    break
        if selected_bookmaker:
            break

    if not selected_bookmaker:
        print(f"  No bookmaker with player props available")
        return props

    print(f"  Using {selected_book_key.title()} odds")

    # Game info
    event_id = game['id']
    game_start = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
    # Convert to Eastern Time to get correct game date
    eastern = pytz.timezone('US/Eastern')
    game_start_et = game_start.astimezone(eastern)
    game_date = game_start_et.date()
    home_team = game['home_team']
    away_team = game['away_team']

    # Process each market
    for market in selected_bookmaker.get('markets', []):
        market_key = market['key']
        
        if not market_key.startswith('player_'):
            continue
        
        stat_type = market_key.replace('player_', '')
        
        # Group outcomes by player
        players_in_market = {}
        
        for outcome in market.get('outcomes', []):
            bet_side = (outcome.get('name') or '').strip().lower()
            player_name = outcome.get('description') or outcome.get('name') or outcome.get('player')
            point = outcome.get('point')
            price = outcome.get('price')

            if not player_name:
                continue

            if player_name not in players_in_market:
                players_in_market[player_name] = {
                    'player_name': player_name,
                    'event_id': event_id,
                    'game_date': game_date,
                    'game_start_time': game_start,
                    'home_team': home_team,
                    'away_team': away_team,
                    'bookmaker': selected_book_key,
                    'stat_type': stat_type,
                    'line': point,
                    'over_price': None,
                    'under_price': None
                }

            current_record = players_in_market[player_name]

            if bet_side == 'over':
                current_record['over_price'] = price
                if current_record['line'] is None:
                    current_record['line'] = point
            elif bet_side == 'under':
                current_record['under_price'] = price
                if current_record['line'] is None:
                    current_record['line'] = point
        
        # Add completed records
        for player_record in players_in_market.values():
            if player_record['over_price'] is not None:
                props.append(player_record)
    
    return props


def insert_player_props_to_db(props_data: List[Dict]):
    """Insert player props to database using a single connection"""
    print(f"Inserting {len(props_data)} player prop records...")
    
    # Create single connection with proper pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    conn = engine.connect()
    
    try:
        inserted_count = 0
        skipped_count = 0
        
        for prop in props_data:
            try:
                # Resolve player with connection reuse
                player_id = resolve_player_simple(conn, prop['player_name'], prop['game_date'])
                
                if not player_id:
                    print(f"  Skipping {prop['player_name']} - could not resolve")
                    skipped_count += 1
                    continue
                
                # Resolve team IDs from odds_api_team_name
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
                    print(f"  Skipping unknown stat type: {prop['stat_type']}")
                    skipped_count += 1
                    continue
                
                line_col, over_col, under_col = stat_columns[prop['stat_type']]
                
                # Check if record exists (reusing connection)
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
                        'over_price': prop['over_price'],
                        'under_price': prop['under_price'],
                        'player_id': player_id,
                        'odds_home_team': prop['home_team'],
                        'odds_away_team': prop['away_team'],
                        'odds_home_team_id': home_team_id,
                        'odds_away_team_id': away_team_id,
                        'record_id': existing[0]
                    })
                    
                    print(f"  Updated {prop['player_name']} {prop['stat_type']}: {prop['line']}")
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
                        'over_price': prop['over_price'],
                        'under_price': prop['under_price']
                    })
                    
                    print(f"  Inserted {prop['player_name']} {prop['stat_type']}: {prop['line']}")
                    inserted_count += 1
                
            except Exception as e:
                print(f"  Error processing {prop.get('player_name', 'unknown')}: {e}")
                skipped_count += 1
                continue
        
        # Commit all changes at once
        conn.commit()
        
        print(f"Successfully processed {inserted_count} player prop records")
        print(f"Skipped {skipped_count} records due to errors")
        return inserted_count
        
    except Exception as e:
        print(f"❌ Error during insertion: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def seed_upcoming_player_props():
    """Main function - Run twice daily at 2:00 AM and 2:00 PM ET"""
    print("=== Starting NBA Player Props Odds Ingestion (Simple Version) ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"UTC Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("Note: Designed to run twice daily (2:00 AM and 2:00 PM ET) for maximum prop coverage")
    
    try:
        # Get upcoming games
        upcoming_games = get_upcoming_nba_games()
        
        if not upcoming_games:
            print("✅ No upcoming NBA games found")
            return
        
        total_props = []
        games_with_props = 0
        
        # Process each game
        for i, game_info in enumerate(upcoming_games, 1):
            event_id = game_info['id']
            game_start = game_info['game_start']
            hours_until = (game_start.replace(tzinfo=None) - datetime.utcnow()).total_seconds() / 3600
            
            print(f"\nProcessing game {i}/{len(upcoming_games)}: {game_info['away_team']} @ {game_info['home_team']}")
            print(f"  Event ID: {event_id}")
            print(f"  Start time: {game_start.strftime('%Y-%m-%d %H:%M UTC')} ({hours_until:.1f} hours from now)")
            
            try:
                game_data = fetch_player_props_for_event(event_id)
                
                if game_data and game_data.get('bookmakers'):
                    game_props = parse_player_props_from_game(game_data)
                    
                    if game_props:
                        total_props.extend(game_props)
                        games_with_props += 1
                        print(f"    ✅ Found {len(game_props)} player props")
                    else:
                        print(f"    ❌ No player props available")
                else:
                    print(f"    ❌ No player props available for this game")
                
                # Rate limiting
                if i < len(upcoming_games):
                    time.sleep(1)
                    
            except Exception as e:
                print(f"    ❌ Error processing game: {e}")
                continue
        
        print(f"\nSummary:")
        print(f"  Games checked: {len(upcoming_games)}")
        print(f"  Games with player props: {games_with_props}")
        print(f"  Total player props found: {len(total_props)}")
        
        if total_props:
            inserted = insert_player_props_to_db(total_props)
            print(f"\n✅ Successfully seeded {inserted} player prop records")
        else:
            print("\n❌ No player props data to insert")
        
    except Exception as e:
        print(f"❌ Error during player props seeding: {e}")
        raise


if __name__ == "__main__":
    seed_upcoming_player_props()