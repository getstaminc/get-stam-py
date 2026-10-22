#!/usr/bin/python3
"""Historical NHL player-prop odds import from the Odds API, mirroring
jobs/nfl_historical_player_odds_import.py. No team D/ST equivalent exists for
NHL, so unlike the NFL job there's no separate defense-props split.

Team resolution uses shared_utils.convert_team_name + a direct team_name
lookup, NOT teams.odds_api_team_name (unpopulated for every NHL team today).
"""
import os
import sys
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import requests
import pytz
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shared_utils

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

NHL_MARKETS = "player_goals,player_assists,player_points,player_shots_on_goal,player_total_saves,player_goal_scorer_anytime"

# Maps Odds API market stat_type -> (line_col, over_col, under_col).
# goal_scorer_anytime has no under column (binary yes/no market).
STAT_COLUMNS = {
    'goals': ('odds_player_goals', 'odds_player_goals_over_price', 'odds_player_goals_under_price'),
    'assists': ('odds_player_assists', 'odds_player_assists_over_price', 'odds_player_assists_under_price'),
    'points': ('odds_player_points', 'odds_player_points_over_price', 'odds_player_points_under_price'),
    'shots_on_goal': ('odds_player_shots_on_goal', 'odds_player_shots_on_goal_over_price', 'odds_player_shots_on_goal_under_price'),
    'total_saves': ('odds_player_total_saves', 'odds_player_total_saves_over_price', 'odds_player_total_saves_under_price'),
    'goal_scorer_anytime': ('odds_player_goal_scorer_anytime', 'odds_player_goal_scorer_anytime_over_price', None),
}


def get_historical_nhl_events(target_date: date, retries=3, delay=2) -> List[Dict]:
    print(f"Fetching NHL events for {target_date}...")
    url = "https://api.the-odds-api.com/v4/historical/sports/icehockey_nhl/events"
    params = {'apiKey': ODDS_API_KEY, 'date': f"{target_date.strftime('%Y-%m-%d')}T12:00:00Z"}
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            events = data.get('data', data) if isinstance(data, dict) else data
            print(f"  Found {len(events)} NHL events for {target_date}")
            return events
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching events (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay * (i + 1))
            else:
                return []
    return []


def get_historical_player_odds(event_id: str, target_date: date, retries=3, delay=2) -> Optional[Dict]:
    print(f"    Fetching player odds for event {event_id}...")
    events = get_historical_nhl_events(target_date)
    commence_time = next((e.get('commence_time') for e in events if e.get('id') == event_id), None)

    if commence_time:
        commence_dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
        times_to_try = [
            (commence_dt - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            commence_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
        ]
    else:
        times_to_try = [f"{target_date.strftime('%Y-%m-%d')}T23:00:00Z"]

    url = f"https://api.the-odds-api.com/v4/historical/sports/icehockey_nhl/events/{event_id}/odds"
    for odds_query_time in times_to_try:
        params = {
            'apiKey': ODDS_API_KEY, 'date': odds_query_time, 'regions': 'us',
            'markets': NHL_MARKETS, 'oddsFormat': 'american', 'bookmakers': 'draftkings',
        }
        for i in range(3):
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 422:
                    break
                response.raise_for_status()
                data = response.json()
                odds_data = data.get('data', data) if isinstance(data, dict) else data
                if not odds_data or not odds_data.get('bookmakers'):
                    break
                print(f"      Found player odds for event {event_id} at {odds_query_time}")
                return odds_data
            except requests.exceptions.RequestException as e:
                print(f"      Error fetching odds (attempt {i+1}/3): {e}")
                time.sleep(2 * (i + 1))
    return None


def parse_historical_player_props(odds_data: Dict, commence_time: str) -> List[Dict]:
    """Parse historical NHL player props from odds data. Standard markets
    (goals/assists/points/shots_on_goal/total_saves) are Over/Under; goal_scorer_anytime
    is a binary Yes/No market stored with a fixed 0.5 line and only the over slot."""
    game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
    game_date = game_start.astimezone(pytz.timezone('US/Eastern')).date()
    props = []

    draftkings = next((bm for bm in odds_data.get('bookmakers', []) if bm['key'] == 'draftkings'), None)
    if not draftkings:
        return props

    event_id = odds_data['id']
    home_team = odds_data.get('home_team', '')
    away_team = odds_data.get('away_team', '')

    for market in draftkings.get('markets', []):
        stat_type = market['key'].replace('player_', '')
        outcomes = market.get('outcomes', [])

        if stat_type == 'goal_scorer_anytime':
            for outcome in outcomes:
                if (outcome.get('name') or '').strip().lower() != 'yes':
                    continue
                description = outcome.get('description', '')
                price = outcome.get('price')
                if not description or price is None:
                    continue
                props.append({
                    'player_name': description, 'event_id': event_id, 'game_date': game_date,
                    'home_team': home_team, 'away_team': away_team, 'bookmaker': 'draftkings',
                    'stat_type': stat_type, 'line': 0.5, 'over_price': price, 'under_price': None,
                })
            continue

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
                    'player_name': player_name, 'event_id': event_id, 'game_date': game_date,
                    'home_team': home_team, 'away_team': away_team, 'bookmaker': 'draftkings',
                    'stat_type': stat_type, 'line': point, 'over_price': None, 'under_price': None,
                }
            record = players_data[player_name]
            if bet_side == 'over':
                record['over_price'] = price
            elif bet_side == 'under':
                record['under_price'] = price

        for record in players_data.values():
            if record['over_price'] is not None:
                props.append(record)

    return props


def normalize_name_simple(name: str) -> str:
    if not name:
        return ""
    return name.lower().strip().replace("'", "").replace("-", "").replace(".", "")


def resolve_team_id_from_name(conn, odds_team_name: str) -> Optional[int]:
    db_name = shared_utils.convert_team_name(odds_team_name)
    result = conn.execute(text("""
        SELECT team_id FROM teams WHERE team_name = :team_name AND sport = 'NHL'
    """), {'team_name': db_name}).fetchone()
    if result:
        return result[0]
    print(f"    Could not resolve NHL team: {odds_team_name} (converted: {db_name})")
    return None


def resolve_player_simple(conn, player_name: str, game_date: date) -> Optional[int]:
    """Exact alias match -> exact normalized-name match (+ add alias) -> create
    placeholder player (+ add alias). No fuzzy matching here, same as NFL's
    resolve_player_simple -- fuzzy/mismatched cases get logged to
    nhl_player_name_mismatch by the actuals job instead, for manual review."""
    normalized = normalize_name_simple(player_name)

    alias_result = conn.execute(text("""
        SELECT player_id FROM nhl_player_aliases WHERE normalized_name = :name
        ORDER BY created_at DESC LIMIT 1
    """), {'name': normalized}).fetchone()
    if alias_result:
        return alias_result[0]

    player_result = conn.execute(text("""
        SELECT id FROM nhl_players WHERE normalized_name = :name
    """), {'name': normalized}).fetchone()
    if player_result:
        conn.execute(text("""
            INSERT INTO nhl_player_aliases (player_id, source, source_name, normalized_name, created_at)
            VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
            ON CONFLICT (source, normalized_name) DO NOTHING
        """), {'player_id': player_result[0], 'source_name': player_name, 'normalized_name': normalized})
        return player_result[0]

    new_player = conn.execute(text("""
        INSERT INTO nhl_players (player_name, normalized_name, first_seen_date, last_seen_date, created_at, updated_at)
        VALUES (:player_name, :normalized_name, :first_seen_date, :last_seen_date, NOW(), NOW())
        RETURNING id
    """), {'player_name': player_name, 'normalized_name': normalized, 'first_seen_date': game_date, 'last_seen_date': game_date})
    player_id = new_player.fetchone()[0]

    conn.execute(text("""
        INSERT INTO nhl_player_aliases (player_id, source, source_name, normalized_name, created_at)
        VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
        ON CONFLICT (source, normalized_name) DO NOTHING
    """), {'player_id': player_id, 'source_name': player_name, 'normalized_name': normalized})
    print(f"    Created new NHL player: {player_name} (ID: {player_id})")
    return player_id


def insert_historical_props_to_db(conn, props_data: List[Dict]) -> int:
    inserted_count = 0
    for prop in props_data:
        if prop['stat_type'] not in STAT_COLUMNS:
            continue
        player_id = resolve_player_simple(conn, prop['player_name'], prop['game_date'])
        if not player_id:
            continue

        home_team_id = resolve_team_id_from_name(conn, prop['home_team'])
        away_team_id = resolve_team_id_from_name(conn, prop['away_team'])
        line_col, over_col, under_col = STAT_COLUMNS[prop['stat_type']]

        existing = conn.execute(text("""
            SELECT id FROM nhl_player_props WHERE player_id = :player_id AND odds_event_id = :odds_event_id
        """), {'player_id': player_id, 'odds_event_id': prop['event_id']}).fetchone()

        under_set_clause = f"{under_col} = :under_price," if under_col else ""
        under_insert_col = f", {under_col}" if under_col else ""
        under_insert_val = ", :under_price" if under_col else ""

        if existing:
            conn.execute(text(f"""
                UPDATE nhl_player_props
                SET {line_col} = :line, {over_col} = :over_price, {under_set_clause}
                    odds_home_team = :odds_home_team, odds_away_team = :odds_away_team,
                    odds_home_team_id = :odds_home_team_id, odds_away_team_id = :odds_away_team_id,
                    updated_at = NOW()
                WHERE id = :record_id
            """), {
                'line': prop['line'], 'over_price': prop['over_price'], 'under_price': prop['under_price'],
                'odds_home_team': prop['home_team'], 'odds_away_team': prop['away_team'],
                'odds_home_team_id': home_team_id, 'odds_away_team_id': away_team_id,
                'record_id': existing[0],
            })
        else:
            params = {
                'player_id': player_id, 'odds_event_id': prop['event_id'], 'game_date': prop['game_date'],
                'bookmaker': prop['bookmaker'], 'odds_source': 'odds_api',
                'odds_home_team': prop['home_team'], 'odds_away_team': prop['away_team'],
                'odds_home_team_id': home_team_id, 'odds_away_team_id': away_team_id,
                'line': prop['line'], 'over_price': prop['over_price'],
            }
            if under_col:
                params['under_price'] = prop['under_price']
            conn.execute(text(f"""
                INSERT INTO nhl_player_props (
                    player_id, normalized_name, odds_event_id, game_date, bookmaker, odds_source,
                    odds_home_team, odds_away_team, odds_home_team_id, odds_away_team_id,
                    {line_col}, {over_col}{under_insert_col}
                ) VALUES (
                    :player_id, (SELECT normalized_name FROM nhl_players WHERE id = :player_id),
                    :odds_event_id, :game_date, :bookmaker, :odds_source,
                    :odds_home_team, :odds_away_team, :odds_home_team_id, :odds_away_team_id,
                    :line, :over_price{under_insert_val}
                )
            """), params)
            inserted_count += 1
    return inserted_count


def import_historical_player_odds_for_date(target_date: date, conn) -> int:
    print(f"\n=== Importing Historical NHL Player Odds for {target_date} ===")
    events = get_historical_nhl_events(target_date)
    if not events:
        return 0

    eastern = pytz.timezone('US/Eastern')
    filtered = [
        e for e in events
        if e.get('commence_time')
        and datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00')).astimezone(eastern).date() == target_date
    ]
    print(f"  Filtered to {len(filtered)} events on {target_date} ET")

    total_imported = 0
    for i, event in enumerate(filtered, 1):
        event_id, commence_time = event.get('id'), event.get('commence_time')
        if not event_id or not commence_time:
            continue
        print(f"\n  Processing event {i}/{len(filtered)}: {event_id}")
        odds_data = get_historical_player_odds(event_id, target_date)
        if not odds_data:
            continue
        props_data = parse_historical_player_props(odds_data, commence_time)
        if not props_data:
            continue
        total_imported += insert_historical_props_to_db(conn, props_data)
        if i < len(filtered):
            time.sleep(3)
    return total_imported


def import_historical_odds_date_range(start_date: date, end_date: date):
    print("=== Historical NHL Player Odds Import ===")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        current_date = start_date
        total = 0
        while current_date <= end_date:
            try:
                total += import_historical_player_odds_for_date(current_date, conn)
                conn.commit()
            except Exception as e:
                print(f"Error processing {current_date}: {e}")
                conn.rollback()
            current_date += timedelta(days=1)
            if current_date <= end_date:
                time.sleep(5)
        print(f"\nTotal player prop records imported: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        start = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end = datetime.strptime(sys.argv[2], '%Y-%m-%d').date() if len(sys.argv) >= 3 else start
    else:
        start = end = date.today() - timedelta(days=1)
    import_historical_odds_date_range(start, end)
