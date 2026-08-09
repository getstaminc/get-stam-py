#!/usr/bin/python3

import os
import re
import sys
import requests
import time
import pytz
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

NFL_MARKETS = "player_pass_yds,player_pass_tds,player_rush_yds,player_reception_yds,player_receptions,player_anytime_td"

# The player_anytime_td market includes team D/ST as a valid entrant (e.g.
# "Arizona Cardinals D/ST") alongside skill-position players. Those route to
# nfl_defense_props instead of nfl_player_props.
DEFENSE_SUFFIX_RE = re.compile(r'\s+D/ST$', re.IGNORECASE)


def parse_defense_team_name(description: str) -> Optional[str]:
    """Return the bare team name if this outcome description is a team D/ST
    entry (e.g. "Arizona Cardinals D/ST" -> "Arizona Cardinals"), else None."""
    if not description:
        return None
    match = DEFENSE_SUFFIX_RE.search(description)
    if not match:
        return None
    return description[:match.start()].strip()


def get_historical_nfl_events(target_date: date, retries=3, delay=2) -> List[Dict]:
    """
    Get all NFL event objects for a specific historical date.
    """
    print(f"Fetching NFL events for {target_date}...")

    date_str = target_date.strftime('%Y-%m-%d')

    url = f"https://api.the-odds-api.com/v4/historical/sports/americanfootball_nfl/events"
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

            print(f"  Found {len(events)} NFL events for {target_date}")
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
    Get historical player prop odds for a specific NFL event.
    """
    print(f"    Fetching player odds for event {event_id}...")

    commence_time = None
    today_events = get_historical_nfl_events(target_date)
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

    url = f"https://api.the-odds-api.com/v4/historical/sports/americanfootball_nfl/events/{event_id}/odds"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for odds_query_time in times_to_try:
        params = {
            'apiKey': ODDS_API_KEY,
            'date': odds_query_time,
            'regions': 'us',
            'markets': NFL_MARKETS,
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


def parse_historical_player_props(odds_data: Dict, commence_time: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Parse historical NFL player props from odds data.

    Five of the six markets (pass_yds, pass_tds, rush_yds, reception_yds, receptions)
    are standard Over/Under markets: outcomes have 'name' (Over/Under), 'description'
    (player name), 'price', 'point'.

    player_anytime_td is a binary Yes/No market with no 'point' - we store a fixed
    0.5 sentinel line and only populate the 'over' price slot (there is no 'under'
    column for this market). Team D/ST entries in this market are split out into a
    separate return list rather than mixed into the player props.

    Returns (props, defense_props).
    """
    game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
    eastern = pytz.timezone('US/Eastern')
    game_start_et = game_start.astimezone(eastern)
    game_date = game_start_et.date()
    props = []
    defense_props = []

    if not odds_data.get('bookmakers'):
        return props, defense_props

    draftkings_data = None
    for bookmaker in odds_data['bookmakers']:
        if bookmaker['key'] == 'draftkings':
            draftkings_data = bookmaker
            break

    if not draftkings_data or not draftkings_data.get('markets'):
        return props, defense_props

    event_id = odds_data['id']
    home_team = odds_data.get('home_team', '')
    away_team = odds_data.get('away_team', '')

    for market in draftkings_data['markets']:
        market_key = market['key']

        if not market_key.startswith('player_'):
            continue

        stat_type = market_key.replace('player_', '')
        outcomes = market.get('outcomes', [])

        if stat_type == 'anytime_td':
            # Binary Yes/No market - no point, only a "Yes" price
            for outcome in outcomes:
                bet_side = (outcome.get('name') or '').strip().lower()
                description = outcome.get('description', '')
                price = outcome.get('price')

                if not description or bet_side != 'yes' or price is None:
                    continue

                defense_team_name = parse_defense_team_name(description)
                if defense_team_name:
                    defense_props.append({
                        'team_name': defense_team_name,
                        'event_id': event_id,
                        'game_date': game_date,
                        'home_team': home_team,
                        'away_team': away_team,
                        'bookmaker': 'draftkings',
                        'line': 0.5,
                        'over_price': price,
                    })
                    continue

                props.append({
                    'player_name': description,
                    'event_id': event_id,
                    'game_date': game_date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'bookmaker': 'draftkings',
                    'stat_type': stat_type,
                    'line': 0.5,
                    'over_price': price,
                    'under_price': None,
                })
            continue

        # Standard Over/Under markets
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
                    'stat_type': stat_type,
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

    return props, defense_props


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
            WHERE odds_api_team_name = :odds_team_name AND sport = 'NFL'
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
        alias_result = conn.execute(text("""
            SELECT player_id FROM nfl_player_aliases
            WHERE normalized_name = :name
            ORDER BY created_at DESC
            LIMIT 1
        """), {'name': normalized}).fetchone()

        if alias_result:
            print(f"    ✓ Found via alias: {player_name} -> player_id {alias_result[0]}")
            return alias_result[0]

        player_result = conn.execute(text("""
            SELECT id FROM nfl_players WHERE normalized_name = :name
        """), {'name': normalized}).fetchone()

        if player_result:
            conn.execute(text("""
                INSERT INTO nfl_player_aliases (player_id, source, source_name, normalized_name, created_at)
                VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
                ON CONFLICT (source, normalized_name) DO NOTHING
            """), {
                'player_id': player_result[0],
                'source_name': player_name,
                'normalized_name': normalized
            })
            print(f"    ✓ Found existing player and added alias: {player_name} -> player_id {player_result[0]}")
            return player_result[0]

        new_player_result = conn.execute(text("""
            INSERT INTO nfl_players (player_name, normalized_name, first_seen_date, last_seen_date, created_at, updated_at)
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
            INSERT INTO nfl_player_aliases (player_id, source, source_name, normalized_name, created_at)
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


# Maps stat_type -> (line_col, over_col, under_col). anytime_td has no under column.
STAT_COLUMNS = {
    'pass_yds': ('odds_player_pass_yds', 'odds_player_pass_yds_over_price', 'odds_player_pass_yds_under_price'),
    'pass_tds': ('odds_player_pass_tds', 'odds_player_pass_tds_over_price', 'odds_player_pass_tds_under_price'),
    'rush_yds': ('odds_player_rush_yds', 'odds_player_rush_yds_over_price', 'odds_player_rush_yds_under_price'),
    'reception_yds': ('odds_player_reception_yds', 'odds_player_reception_yds_over_price', 'odds_player_reception_yds_under_price'),
    'receptions': ('odds_player_receptions', 'odds_player_receptions_over_price', 'odds_player_receptions_under_price'),
    'anytime_td': ('odds_player_anytime_td', 'odds_player_anytime_td_over_price', None),
}


def insert_historical_props_to_db(conn, props_data: List[Dict]) -> int:
    """
    Insert historical NFL player props to database.
    """
    inserted_count = 0

    for prop in props_data:
        try:
            player_id = resolve_player_simple(conn, prop['player_name'], prop['game_date'])

            if not player_id:
                print(f"    Skipping {prop['player_name']} - could not resolve")
                continue

            home_team_id = resolve_team_id_from_odds_api(conn, prop['home_team'])
            away_team_id = resolve_team_id_from_odds_api(conn, prop['away_team'])

            if prop['stat_type'] not in STAT_COLUMNS:
                continue

            line_col, over_col, under_col = STAT_COLUMNS[prop['stat_type']]

            existing = conn.execute(text("""
                SELECT id FROM nfl_player_props
                WHERE player_id = :player_id AND odds_event_id = :odds_event_id
            """), {
                'player_id': player_id,
                'odds_event_id': prop['event_id']
            }).fetchone()

            under_set_clause = f"{under_col} = :under_price," if under_col else ""
            under_insert_col = f", {under_col}" if under_col else ""
            under_insert_val = ", :under_price" if under_col else ""

            if existing:
                update_sql = f"""
                    UPDATE nfl_player_props
                    SET {line_col} = :line,
                        {over_col} = :over_price,
                        {under_set_clause}
                        normalized_name = (SELECT normalized_name FROM nfl_players WHERE id = :player_id),
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
            else:
                insert_sql = f"""
                    INSERT INTO nfl_player_props (
                        player_id, normalized_name, odds_event_id, game_date, bookmaker, odds_source,
                        odds_home_team, odds_away_team, odds_home_team_id, odds_away_team_id,
                        {line_col}, {over_col}{under_insert_col}
                    ) VALUES (
                        :player_id,
                        (SELECT normalized_name FROM nfl_players WHERE id = :player_id),
                        :odds_event_id, :game_date, :bookmaker, :odds_source,
                        :odds_home_team, :odds_away_team, :odds_home_team_id, :odds_away_team_id,
                        :line, :over_price{under_insert_val}
                    )
                """

                params = {
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
                }
                if under_col:
                    params['under_price'] = prop['under_price']

                conn.execute(text(insert_sql), params)

                inserted_count += 1

        except Exception as e:
            print(f"    Error processing {prop.get('player_name', 'unknown')}: {e}")
            continue

    return inserted_count


def insert_historical_defense_props_to_db(conn, defense_props_data: List[Dict]) -> int:
    """
    Insert historical NFL team D/ST anytime-TD props to nfl_defense_props.
    """
    inserted_count = 0

    for prop in defense_props_data:
        try:
            team_id = resolve_team_id_from_odds_api(conn, prop['team_name'])

            if not team_id:
                print(f"    Skipping D/ST {prop['team_name']} - could not resolve team")
                continue

            home_team_id = resolve_team_id_from_odds_api(conn, prop['home_team'])
            away_team_id = resolve_team_id_from_odds_api(conn, prop['away_team'])

            is_home = prop['team_name'] == prop['home_team']
            opponent_team_name = prop['away_team'] if is_home else prop['home_team']
            opponent_team_id = away_team_id if is_home else home_team_id

            existing = conn.execute(text("""
                SELECT id FROM nfl_defense_props
                WHERE team_id = :team_id AND odds_event_id = :odds_event_id
            """), {
                'team_id': team_id,
                'odds_event_id': prop['event_id']
            }).fetchone()

            if existing:
                conn.execute(text("""
                    UPDATE nfl_defense_props
                    SET odds_anytime_td = :line,
                        odds_anytime_td_over_price = :over_price,
                        team_name = :team_name,
                        opponent_team_name = :opponent_team_name,
                        opponent_team_id = :opponent_team_id,
                        odds_home_team = :odds_home_team,
                        odds_away_team = :odds_away_team,
                        odds_home_team_id = :odds_home_team_id,
                        odds_away_team_id = :odds_away_team_id,
                        updated_at = NOW()
                    WHERE id = :record_id
                """), {
                    'line': prop['line'],
                    'over_price': prop['over_price'],
                    'team_name': prop['team_name'],
                    'opponent_team_name': opponent_team_name,
                    'opponent_team_id': opponent_team_id,
                    'odds_home_team': prop['home_team'],
                    'odds_away_team': prop['away_team'],
                    'odds_home_team_id': home_team_id,
                    'odds_away_team_id': away_team_id,
                    'record_id': existing[0]
                })
            else:
                conn.execute(text("""
                    INSERT INTO nfl_defense_props (
                        team_id, team_name, odds_event_id, game_date, bookmaker, odds_source,
                        odds_home_team, odds_away_team, odds_home_team_id, odds_away_team_id,
                        opponent_team_name, opponent_team_id,
                        odds_anytime_td, odds_anytime_td_over_price
                    ) VALUES (
                        :team_id, :team_name, :odds_event_id, :game_date, :bookmaker, :odds_source,
                        :odds_home_team, :odds_away_team, :odds_home_team_id, :odds_away_team_id,
                        :opponent_team_name, :opponent_team_id,
                        :line, :over_price
                    )
                """), {
                    'team_id': team_id,
                    'team_name': prop['team_name'],
                    'odds_event_id': prop['event_id'],
                    'game_date': prop['game_date'],
                    'bookmaker': prop['bookmaker'],
                    'odds_source': 'odds_api',
                    'odds_home_team': prop['home_team'],
                    'odds_away_team': prop['away_team'],
                    'odds_home_team_id': home_team_id,
                    'odds_away_team_id': away_team_id,
                    'opponent_team_name': opponent_team_name,
                    'opponent_team_id': opponent_team_id,
                    'line': prop['line'],
                    'over_price': prop['over_price'],
                })

                inserted_count += 1

        except Exception as e:
            print(f"    Error processing D/ST {prop.get('team_name', 'unknown')}: {e}")
            continue

    return inserted_count


def import_historical_player_odds_for_date(target_date: date, conn) -> int:
    """
    Import all historical NFL player odds for a specific date.
    """
    print(f"\n=== Importing Historical NFL Player Odds for {target_date} ===")

    events = get_historical_nfl_events(target_date)

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

            props_data, defense_props_data = parse_historical_player_props(odds_data, commence_time)

            if not props_data and not defense_props_data:
                print(f"    No player props found for event {event_id}")
                continue

            print(f"    Found {len(props_data)} player props, {len(defense_props_data)} D/ST props")

            inserted = insert_historical_props_to_db(conn, props_data)
            defense_inserted = insert_historical_defense_props_to_db(conn, defense_props_data)

            total_props_imported += inserted + defense_inserted

            if i < len(filtered_events):
                time.sleep(3)

        except Exception as e:
            print(f"    Error processing event {event_id}: {e}")
            continue

    return total_props_imported


def import_historical_odds_date_range(start_date: date, end_date: date):
    """
    Import historical NFL player odds for a date range.
    """
    print(f"=== Historical NFL Player Odds Import ===")
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
    if len(sys.argv) >= 2:
        start = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end = datetime.strptime(sys.argv[2], '%Y-%m-%d').date() if len(sys.argv) >= 3 else start
    else:
        start = end = date.today() - timedelta(days=1)

    import_historical_odds_date_range(start, end)
