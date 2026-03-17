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
ODDS_API_KEY = os.getenv("ODDS_API_KEY")


def get_historical_mlb_events(target_date: date, retries=3, delay=2) -> List[str]:
    """
    Get all MLB event IDs for a specific historical date.
    """
    print(f"Fetching MLB events for {target_date}...")

    date_str = target_date.strftime('%Y-%m-%d')

    url = f"https://api.the-odds-api.com/v4/historical/sports/baseball_mlb/events"
    params = {
        'apiKey': ODDS_API_KEY,
        'date': f"{date_str}T12:00:00Z"
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

            print(f"  Found {len(events)} MLB events for {target_date}")
            return events

        except requests.exceptions.RequestException as e:
            print(f"  Error fetching events (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay * (i + 1))
            else:
                print(f"  Failed to fetch events for {target_date}")
                return []

    return []


def get_historical_player_odds(event_id: str, target_date: date, retries=3, delay=2) -> Optional[Dict]:
    """
    Get historical player prop odds for a specific MLB event.
    """
    print(f"    Fetching player odds for event {event_id}...")

    commence_time = None
    today_events = get_historical_mlb_events(target_date)
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

    url = f"https://api.the-odds-api.com/v4/historical/sports/baseball_mlb/events/{event_id}/odds"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebSever/537.36"
    }
    for odds_query_time in times_to_try:
        params = {
            'apiKey': ODDS_API_KEY,
            'date': odds_query_time,
            'regions': 'us',
            'markets': 'batter_hits,batter_home_runs,batter_rbis,batter_runs_scored,batter_total_bases,pitcher_strikeouts,pitcher_earned_runs,pitcher_hits_allowed,pitcher_walks',
            'oddsFormat': 'american',
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
    Parse historical player props from MLB odds data.
    """
    game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
    eastern = pytz.timezone('US/Eastern')
    game_start_et = game_start.astimezone(eastern)
    game_date = game_start_et.date()
    props = []

    if not odds_data.get('bookmakers'):
        return props

    draftkings_data = None
    for bookmaker in odds_data['bookmakers']:
        if bookmaker['key'] == 'draftkings':
            draftkings_data = bookmaker
            break

    if not draftkings_data or not draftkings_data.get('markets'):
        return props

    event_id = odds_data['id']
    home_team = odds_data.get('home_team', '')
    away_team = odds_data.get('away_team', '')

    # stat_columns map: market_key -> (line_col, over_col, under_col)
    batter_stat_columns = {
        'batter_hits':        ('odds_batter_hits', 'odds_batter_hits_over_price', 'odds_batter_hits_under_price'),
        'batter_home_runs':   ('odds_batter_home_runs', 'odds_batter_home_runs_over_price', 'odds_batter_home_runs_under_price'),
        'batter_rbis':        ('odds_batter_rbi', 'odds_batter_rbi_over_price', 'odds_batter_rbi_under_price'),
        'batter_runs_scored': ('odds_batter_runs_scored', 'odds_batter_runs_scored_over_price', 'odds_batter_runs_scored_under_price'),
        'batter_total_bases': ('odds_batter_total_bases', 'odds_batter_total_bases_over_price', 'odds_batter_total_bases_under_price'),
    }
    pitcher_stat_columns = {
        'pitcher_strikeouts':   ('odds_pitcher_strikeouts', 'odds_pitcher_strikeouts_over_price', 'odds_pitcher_strikeouts_under_price'),
        'pitcher_earned_runs':  ('odds_pitcher_earned_runs', 'odds_pitcher_earned_runs_over_price', 'odds_pitcher_earned_runs_under_price'),
        'pitcher_hits_allowed': ('odds_pitcher_hits_allowed', 'odds_pitcher_hits_allowed_over_price', 'odds_pitcher_hits_allowed_under_price'),
        'pitcher_walks':        ('odds_pitcher_walks', 'odds_pitcher_walks_over_price', 'odds_pitcher_walks_under_price'),
    }
    stat_columns = {**batter_stat_columns, **pitcher_stat_columns}

    for market in draftkings_data['markets']:
        market_key = market['key']

        if market_key not in stat_columns:
            continue

        if market_key.startswith('batter_'):
            pass
        elif market_key.startswith('pitcher_'):
            pass
        else:
            continue

        outcomes = market.get('outcomes', [])
        players_data = {}

        for outcome in outcomes:
            bet_side = (outcome.get('name') or '').strip().lower()
            player_name = outcome.get('description', '')
            point = outcome.get('point')
            price = outcome.get('price')

            if not player_name or point is None:
                continue

            if player_name not in players_data:
                players_data[player_name] = {
                    'player_name': player_name,
                    'event_id': event_id,
                    'game_date': game_date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'bookmaker': 'draftkings',
                    'market_key': market_key,
                    'line': point,
                    'over_price': None,
                    'under_price': None
                }

            player_record = players_data[player_name]
            if bet_side == 'over':
                player_record['over_price'] = price
                if player_record['line'] is None:
                    player_record['line'] = point
            elif bet_side == 'under':
                player_record['under_price'] = price
                if player_record['line'] is None:
                    player_record['line'] = point

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
            WHERE odds_api_team_name = :odds_team_name AND sport = 'MLB'
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
    Raises on error so the caller's savepoint can roll back cleanly.
    """
    normalized = normalize_name_simple(player_name)

    # Step 1: Check aliases first
    alias_result = conn.execute(text("""
        SELECT player_id FROM mlb_player_aliases
        WHERE normalized_name = :name
        ORDER BY created_at DESC
        LIMIT 1
    """), {'name': normalized}).fetchone()

    if alias_result:
        print(f"    ✓ Found via alias: {player_name} -> player_id {alias_result[0]}")
        return alias_result[0]

    # Step 2: Check mlb_players table by normalized name
    player_result = conn.execute(text("""
        SELECT id FROM mlb_players WHERE normalized_name = :name
    """), {'name': normalized}).fetchone()

    if player_result:
        conn.execute(text("""
            INSERT INTO mlb_player_aliases (player_id, source, source_name, normalized_name, created_at)
            VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
            ON CONFLICT (source, normalized_name) DO NOTHING
        """), {
            'player_id': player_result[0],
            'source_name': player_name,
            'normalized_name': normalized
        })
        print(f"    ✓ Found existing player and added alias: {player_name} -> player_id {player_result[0]}")
        return player_result[0]

    # Step 3: Create new player
    new_player_result = conn.execute(text("""
        INSERT INTO mlb_players (player_name, normalized_name, first_seen_date, last_seen_date, created_at, updated_at)
        VALUES (:player_name, :normalized_name, :first_seen_date, :last_seen_date, NOW(), NOW())
        RETURNING id
    """), {
        'player_name': player_name,
        'normalized_name': normalized,
        'first_seen_date': game_date,
        'last_seen_date': game_date
    })

    player_id = new_player_result.fetchone()[0]

    conn.execute(text("""
        INSERT INTO mlb_player_aliases (player_id, source, source_name, normalized_name, created_at)
        VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
        ON CONFLICT (source, normalized_name) DO NOTHING
    """), {
        'player_id': player_id,
        'source_name': player_name,
        'normalized_name': normalized
    })

    print(f"    ➕ Created new player: {player_name} (ID: {player_id})")
    return player_id


def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American format."""
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))


def insert_historical_props_to_db(conn, props_data: List[Dict]) -> tuple:
    """
    Insert historical MLB player props to database.
    Returns (inserted_count, player_errors) where player_errors is a list of (player_name, error_str).
    """
    inserted_count = 0
    player_errors = []

    batter_stat_columns = {
        'batter_hits':        ('odds_batter_hits', 'odds_batter_hits_over_price', 'odds_batter_hits_under_price'),
        'batter_home_runs':   ('odds_batter_home_runs', 'odds_batter_home_runs_over_price', 'odds_batter_home_runs_under_price'),
        'batter_rbis':        ('odds_batter_rbi', 'odds_batter_rbi_over_price', 'odds_batter_rbi_under_price'),
        'batter_runs_scored': ('odds_batter_runs_scored', 'odds_batter_runs_scored_over_price', 'odds_batter_runs_scored_under_price'),
        'batter_total_bases': ('odds_batter_total_bases', 'odds_batter_total_bases_over_price', 'odds_batter_total_bases_under_price'),
    }
    pitcher_stat_columns = {
        'pitcher_strikeouts':   ('odds_pitcher_strikeouts', 'odds_pitcher_strikeouts_over_price', 'odds_pitcher_strikeouts_under_price'),
        'pitcher_earned_runs':  ('odds_pitcher_earned_runs', 'odds_pitcher_earned_runs_over_price', 'odds_pitcher_earned_runs_under_price'),
        'pitcher_hits_allowed': ('odds_pitcher_hits_allowed', 'odds_pitcher_hits_allowed_over_price', 'odds_pitcher_hits_allowed_under_price'),
        'pitcher_walks':        ('odds_pitcher_walks', 'odds_pitcher_walks_over_price', 'odds_pitcher_walks_under_price'),
    }

    for prop in props_data:
        market_key = prop['market_key']
        if market_key in batter_stat_columns:
            table_name = 'mlb_batter_props'
            line_col, over_col, under_col = batter_stat_columns[market_key]
        elif market_key in pitcher_stat_columns:
            table_name = 'mlb_pitcher_props'
            line_col, over_col, under_col = pitcher_stat_columns[market_key]
        else:
            continue

        try:
            with conn.begin_nested():  # savepoint — rolls back only this prop on failure
                player_id = resolve_player_simple(conn, prop['player_name'], prop['game_date'])

                if not player_id:
                    print(f"    Skipping {prop['player_name']} - could not resolve")
                    continue

                home_team_id = resolve_team_id_from_odds_api(conn, prop['home_team'])
                away_team_id = resolve_team_id_from_odds_api(conn, prop['away_team'])

                over_price_american = int(prop['over_price']) if prop['over_price'] is not None else None
                under_price_american = int(prop['under_price']) if prop['under_price'] is not None else None

                existing = conn.execute(text(f"""
                    SELECT id FROM {table_name}
                    WHERE player_id = :player_id AND odds_event_id = :odds_event_id
                """), {
                    'player_id': player_id,
                    'odds_event_id': prop['event_id']
                }).fetchone()

                if existing:
                    update_sql = f"""
                        UPDATE {table_name}
                        SET {line_col} = :line,
                            {over_col} = :over_price,
                            {under_col} = :under_price,
                            normalized_name = (SELECT normalized_name FROM mlb_players WHERE id = :player_id),
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
                    insert_sql = f"""
                        INSERT INTO {table_name} (
                            player_id, normalized_name, odds_event_id, game_date, bookmaker, odds_source,
                            odds_home_team, odds_away_team, odds_home_team_id, odds_away_team_id,
                            did_not_play,
                            {line_col}, {over_col}, {under_col}
                        ) VALUES (
                            :player_id,
                            (SELECT normalized_name FROM mlb_players WHERE id = :player_id),
                            :odds_event_id, :game_date, :bookmaker, :odds_source,
                            :odds_home_team, :odds_away_team, :odds_home_team_id, :odds_away_team_id,
                            FALSE,
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
            player_name = prop.get('player_name', 'unknown')
            error_str = str(e).splitlines()[0]  # first line only — keeps output readable
            print(f"    ❌ Error processing {player_name}: {error_str}")
            player_errors.append((player_name, error_str))
            continue

    return inserted_count, player_errors


def import_historical_player_odds_for_date(target_date: date, conn) -> int:
    """
    Import all historical MLB player odds for a specific date.
    """
    print(f"\n=== Importing Historical MLB Player Odds for {target_date} ===")

    events = get_historical_mlb_events(target_date)

    if not events:
        print(f"No events found for {target_date}")
        return 0

    eastern = pytz.timezone('US/Eastern')
    filtered_events = []

    for event in events:
        commence_time = event.get('commence_time')
        if commence_time:
            game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            game_start_et = game_start.astimezone(eastern)
            game_date_et = game_start_et.date()

            if game_date_et == target_date:
                filtered_events.append(event)

    print(f"  Filtered to {len(filtered_events)} events on {target_date} ET (from {len(events)} total API results)")

    if not filtered_events:
        print(f"  No events match target date {target_date} after timezone conversion")
        return 0

    total_props_imported = 0

    for i, event in enumerate(filtered_events, 1):
        event_id = event.get('id')
        commence_time = event.get('commence_time')

        if not event_id or not commence_time:
            continue

        print(f"\n  Processing event {i}/{len(filtered_events)}: {event_id}")

        try:
            odds_data = get_historical_player_odds(event_id, target_date)

            if not odds_data:
                continue

            props_data = parse_historical_player_props(odds_data, commence_time)

            if not props_data:
                print(f"    No player props found for event {event_id}")
                continue

            print(f"    Found {len(props_data)} player props")

            inserted, errors = insert_historical_props_to_db(conn, props_data)

            total_props_imported += inserted

            if errors:
                unique_errors = {}
                for name, err in errors:
                    if name not in unique_errors:
                        unique_errors[name] = err
                print(f"    ⚠️  {len(errors)} player prop(s) skipped due to errors:")
                for name, err in unique_errors.items():
                    print(f"       • {name}: {err}")

            if i < len(filtered_events):
                time.sleep(3)

        except Exception as e:
            print(f"    Error processing event {event_id}: {e}")
            continue

    return total_props_imported


def import_historical_odds_date_range(start_date: date, end_date: date):
    """
    Import historical MLB player odds for a date range.
    """
    print(f"=== Historical MLB Player Odds Import ===")
    print(f"Date range: {start_date} to {end_date}")

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

                conn.commit()
                print(f"✅ Committed {daily_imported} records for {current_date}")

            except Exception as e:
                print(f"❌ Error processing {current_date}: {e}")
                conn.rollback()

            current_date += timedelta(days=1)

            if current_date <= end_date:
                time.sleep(5)

        print(f"\n🎉 Historical MLB import complete!")
        print(f"Total player prop records imported: {total_imported}")
        print(f"Date range: {start_date} to {end_date}")

    except Exception as e:
        print(f"❌ Fatal error during historical import: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    start_date = date(2025, 7, 2)
    end_date = date(2025, 7, 2)

    import_historical_odds_date_range(start_date, end_date)
