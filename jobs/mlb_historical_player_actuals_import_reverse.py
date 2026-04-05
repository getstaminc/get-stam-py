#!/usr/bin/python3

import os
import sys
import requests
import time
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import time as _time
from unidecode import unidecode

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


def get_mlb_games_for_date(target_date: date, retries=3, delay=2) -> List[Dict]:
    """
    Get all MLB games for a specific historical date from ESPN.

    Returns a list of dicts sorted by game_datetime:
        {
            'game_id': str,
            'game_datetime': datetime,       # UTC
            'espn_home_team_id': str,
            'espn_away_team_id': str,
        }
    """
    print(f"Fetching MLB games for {target_date}...")

    date_str = target_date.strftime('%Y%m%d')

    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    params = {
        'dates': date_str,
        'limit': 50
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            _time.sleep(0.2)
            data = response.json()
            if not data.get('events'):
                print(f"  No games found for {target_date}")
                return []
            games = []
            for event in data['events']:
                game_id = event.get('id')
                date_str_raw = event.get('date')
                if not game_id:
                    continue

                game_datetime = None
                if date_str_raw:
                    try:
                        game_datetime = datetime.fromisoformat(date_str_raw.replace('Z', '+00:00'))
                    except ValueError:
                        pass

                espn_home_team_id = None
                espn_away_team_id = None
                competitions = event.get('competitions', [])
                if competitions:
                    for competitor in competitions[0].get('competitors', []):
                        home_away = competitor.get('homeAway', '')
                        team_id = str(competitor.get('team', {}).get('id', ''))
                        if home_away == 'home':
                            espn_home_team_id = team_id
                        elif home_away == 'away':
                            espn_away_team_id = team_id

                games.append({
                    'game_id': game_id,
                    'game_datetime': game_datetime,
                    'espn_home_team_id': espn_home_team_id,
                    'espn_away_team_id': espn_away_team_id,
                })

            _epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            games.sort(key=lambda g: g['game_datetime'] or _epoch)
            print(f"  Found {len(games)} MLB games for {target_date}")
            return games
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
    Get historical boxscore data from ESPN for a specific MLB game.
    """
    print(f"    Fetching boxscore for game {game_id}...")

    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary"
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
    """Normalize player name to match the format used in odds ingestion."""
    if not name:
        return ''
    
    # Remove accents/diacritics
    name = unidecode(name)
    
    normalized = name.lower()
    normalized = normalized.replace("'", "").replace("-", "").replace(".", "")
    normalized = ' '.join(normalized.split())
    return normalized


def strip_name_suffix(normalized_name: str) -> str:
    """Remove common name suffixes for strict matching."""
    suffixes = [' jr', ' sr', ' ii', ' iii', ' iv', ' v', ' 2nd', ' 3rd', ' 4th']
    for suffix in suffixes:
        if normalized_name.endswith(suffix):
            return normalized_name[:-len(suffix)].strip()
    return normalized_name


def parse_name_parts(normalized_name: str) -> tuple[str, str]:
    """Parse a normalized name into first and last name parts."""
    parts = normalized_name.strip().split()
    if len(parts) == 0:
        return '', ''
    elif len(parts) == 1:
        return '', parts[0]
    else:
        return ' '.join(parts[:-1]), parts[-1]


def names_match_strict(odds_name: str, espn_name: str) -> bool:
    """Check if two normalized names match using strict first + last name comparison."""
    odds_clean = strip_name_suffix(odds_name)
    espn_clean = strip_name_suffix(espn_name)

    odds_first, odds_last = parse_name_parts(odds_clean)
    espn_first, espn_last = parse_name_parts(espn_clean)

    first_match = False
    if odds_first == espn_first:
        first_match = True
    elif odds_first and espn_first:
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
        if isinstance(value, str) and '-' in value:
            return int(value.split('-')[0])
        return int(float(value))
    except (ValueError, TypeError):
        return None


def build_player_stats_lookup_mlb(boxscore_data: Dict) -> Tuple[Dict, Dict, List[Dict]]:
    """
    Build batter and pitcher stat lookup dictionaries from ESPN MLB boxscore.

    MLB boxscore has multiple statistics blocks per team, typed by 'type':
    'batting', 'pitching', 'fielding'. We use batting and pitching only.

    Returns:
        Tuple of (batter_lookup, pitcher_lookup, team_info_list)
        - batter_lookup: normalized_name -> batter stat dict
        - pitcher_lookup: normalized_name -> pitcher stat dict
        - team_info_list: list of dicts with 'name', 'espn_id'
    """
    batter_lookup = {}
    pitcher_lookup = {}
    team_info_list = []

    boxscore = boxscore_data.get('boxscore', {})
    teams = boxscore.get('players', [])

    if not teams:
        return batter_lookup, pitcher_lookup, team_info_list

    for team_data in teams:
        team_info = team_data.get('team', {})
        team_name = team_info.get('displayName', 'Unknown Team')
        team_espn_id = str(team_info.get('id', ''))

        team_info_list.append({
            'name': team_name,
            'espn_id': team_espn_id
        })

        statistics = team_data.get('statistics', [])
        if not statistics:
            continue

        # Find batting block
        batting_block = None
        pitching_block = None
        for stat_block in statistics:
            block_type = stat_block.get('type', '').lower()
            if block_type == 'batting':
                batting_block = stat_block
            elif block_type == 'pitching':
                pitching_block = stat_block

        # Process batters
        if batting_block:
            stat_names = batting_block.get('keys', batting_block.get('names', []))
            athletes = batting_block.get('athletes', [])

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

                    if did_not_play or not stats:
                        batter_lookup[normalized_name] = {
                            'espn_player_id': espn_player_id,
                            'player_name': player_name,
                            'normalized_name': normalized_name,
                            'did_not_play': True,
                            'player_team_espn_id': team_espn_id,
                            'player_team_name': team_name,
                            'actual_batter_hits': None,
                            'actual_batter_home_runs': None,
                            'actual_batter_rbi': None,
                            'actual_batter_runs_scored': None,
                            'actual_batter_at_bats': None,
                            'actual_batter_walks': None,
                            'actual_batter_strikeouts': None,
                        }
                        continue

                    if len(stats) != len(stat_names):
                        continue

                    stat_dict = dict(zip(stat_names, stats))

                    batter_lookup[normalized_name] = {
                        'espn_player_id': espn_player_id,
                        'player_name': player_name,
                        'normalized_name': normalized_name,
                        'did_not_play': False,
                        'player_team_espn_id': team_espn_id,
                        'player_team_name': team_name,
                        'actual_batter_hits': safe_int(stat_dict.get('hits')),
                        'actual_batter_home_runs': safe_int(stat_dict.get('homeRuns')),
                        'actual_batter_rbi': safe_int(stat_dict.get('RBIs')),
                        'actual_batter_runs_scored': safe_int(stat_dict.get('runs')),
                        'actual_batter_at_bats': safe_int(stat_dict.get('atBats')),
                        'actual_batter_walks': safe_int(stat_dict.get('walks')),
                        'actual_batter_strikeouts': safe_int(stat_dict.get('strikeouts')),
                    }

                except Exception as e:
                    print(f"        Error processing batter in lookup: {e}")
                    continue

        # Process pitchers
        if pitching_block:
            stat_names = pitching_block.get('keys', pitching_block.get('names', []))
            athletes = pitching_block.get('athletes', [])

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

                    if did_not_play or not stats:
                        pitcher_lookup[normalized_name] = {
                            'espn_player_id': espn_player_id,
                            'player_name': player_name,
                            'normalized_name': normalized_name,
                            'did_not_play': True,
                            'player_team_espn_id': team_espn_id,
                            'player_team_name': team_name,
                            'actual_pitcher_strikeouts': None,
                            'actual_pitcher_earned_runs': None,
                            'actual_pitcher_hits_allowed': None,
                            'actual_pitcher_walks': None,
                            'actual_pitcher_innings_pitched': None,
                        }
                        continue

                    if len(stats) != len(stat_names):
                        continue

                    stat_dict = dict(zip(stat_names, stats))

                    pitcher_lookup[normalized_name] = {
                        'espn_player_id': espn_player_id,
                        'player_name': player_name,
                        'normalized_name': normalized_name,
                        'did_not_play': False,
                        'player_team_espn_id': team_espn_id,
                        'player_team_name': team_name,
                        'actual_pitcher_strikeouts': safe_int(stat_dict.get('strikeouts')),
                        'actual_pitcher_earned_runs': safe_int(stat_dict.get('earnedRuns')),
                        'actual_pitcher_hits_allowed': safe_int(stat_dict.get('hits')),
                        'actual_pitcher_walks': safe_int(stat_dict.get('walks')),
                        'actual_pitcher_innings_pitched': stat_dict.get('inningsPitched', ''),
                    }

                except Exception as e:
                    print(f"        Error processing pitcher in lookup: {e}")
                    continue

    return batter_lookup, pitcher_lookup, team_info_list


def get_team_ids_from_boxscore(boxscore_data: Dict) -> tuple[Optional[str], Optional[str]]:
    """Extract the two ESPN team IDs from the boxscore data."""
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
    """Resolve ESPN team IDs to internal team_ids from teams table."""
    team1_id = None
    team2_id = None

    try:
        result = conn.execute(text("""
            SELECT team_id FROM teams
            WHERE espn_team_id = :espn_team_id AND sport = 'MLB'
        """), {'espn_team_id': espn_team_id_1}).fetchone()

        if result:
            team1_id = result[0]
    except Exception as e:
        print(f"    ❌ Error resolving team {espn_team_id_1}: {e}")

    try:
        result = conn.execute(text("""
            SELECT team_id FROM teams
            WHERE espn_team_id = :espn_team_id AND sport = 'MLB'
        """), {'espn_team_id': espn_team_id_2}).fetchone()

        if result:
            team2_id = result[0]
    except Exception as e:
        print(f"    ❌ Error resolving team {espn_team_id_2}: {e}")

    return team1_id, team2_id


def find_player_in_lookup(normalized_name: str, lookup: Dict, conn, player_id: int, props_id: int) -> Optional[Dict]:
    """
    4-step match: ESPN ID -> exact normalized name -> alias table -> strict first+last name.
    Returns stats dict or None.
    """
    # Normalize the database name to handle accents consistently
    normalized_name = normalize_player_name(normalized_name)
    
    # Step 1: Look up ESPN player ID
    player_espn_id = conn.execute(text("""
        SELECT espn_player_id FROM mlb_players WHERE id = :player_id
    """), {'player_id': player_id}).fetchone()

    if player_espn_id and player_espn_id[0]:
        for espn_name, stats in lookup.items():
            if stats.get('espn_player_id') == player_espn_id[0]:
                print(f"      ⚡ Matched by ESPN ID: {normalized_name} (ID: {player_espn_id[0]})")
                return stats

    # Step 2: Exact normalized name match
    player_stats = lookup.get(normalized_name)
    if player_stats:
        print(f"      ✓ Exact name match: {normalized_name}")
        return player_stats

    # Step 3: Check alias table for alternative names
    try:
        alias_results = conn.execute(text("""
            SELECT normalized_name FROM mlb_player_aliases 
            WHERE player_id = :player_id
        """), {'player_id': player_id}).fetchall()
        
        for alias_row in alias_results:
            alias_name = alias_row[0]
            player_stats = lookup.get(alias_name)
            if player_stats:
                print(f"      🔗 Alias match: {normalized_name} → {alias_name}")
                return player_stats
                
    except Exception as e:
        print(f"      Error checking aliases: {e}")

    # Step 4: Strict first+last name matching with suffix stripping
    for espn_name, stats in lookup.items():
        if names_match_strict(normalized_name, espn_name):
            print(f"      🔍 Strict name match (suffix stripped): {normalized_name} → {espn_name}")
            return stats

    return None


def get_doubleheader_game_index(
    game_id: str,
    espn_team_id_1: str,
    espn_team_id_2: str,
    all_day_games: List[Dict],
) -> int:
    """
    Return the 0-based position of game_id among all ESPN games today for this matchup.
    For a normal (non-doubleheader) game this always returns 0.
    For a doubleheader, returns 0 for the earlier game and 1 for the later game.
    """
    team_ids = {espn_team_id_1, espn_team_id_2}
    matchup_games = [
        g for g in all_day_games
        if {g.get('espn_home_team_id'), g.get('espn_away_team_id')} == team_ids
    ]
    # all_day_games is already sorted by game_datetime; maintain that order
    for idx, g in enumerate(matchup_games):
        if g['game_id'] == game_id:
            return idx
    return 0


def select_doubleheader_prop_record(conn, records: list, espn_game_index: int) -> Optional[tuple]:
    """
    Given multiple prop records for the same player on the same date (doubleheader),
    return the record that corresponds to the ESPN game at position espn_game_index.

    Primary sort key: start_time from mlb_games (via odds_event_id).
    Fallback: created_at on the prop record itself.

    records: list of tuples — (id, player_id, normalized_name, home_id, away_id,
                                player_type, odds_event_id, created_at)
    """
    ODDS_EVENT_ID_IDX = 6
    CREATED_AT_IDX = 7

    def get_sort_key(record):
        odds_event_id = record[ODDS_EVENT_ID_IDX]
        if odds_event_id:
            try:
                row = conn.execute(text("""
                    SELECT start_time FROM mlb_games WHERE odds_event_id = :eid
                """), {'eid': odds_event_id}).fetchone()
                if row and row[0]:
                    return (0, row[0])
            except Exception:
                pass
        # Fallback: use created_at
        created_at = record[CREATED_AT_IDX]
        return (1, created_at) if created_at else (2, None)

    sorted_records = sorted(records, key=get_sort_key)

    if espn_game_index >= len(sorted_records):
        print(f"      ⚠️  Doubleheader index {espn_game_index} out of range ({len(sorted_records)} records); using last")
        return sorted_records[-1]

    return sorted_records[espn_game_index]


def process_game_reverse(conn, game_id: str, game_date: date, espn_game_datetime: Optional[datetime] = None, all_day_games: Optional[List[Dict]] = None) -> int:
    """
    Process a single MLB game using the reverse approach.
    """
    print(f"\n  Processing game: {game_id}")

    boxscore_data = get_historical_game_boxscore(game_id, game_date)

    if not boxscore_data:
        return 0

    espn_team_id_1, espn_team_id_2 = get_team_ids_from_boxscore(boxscore_data)

    if not espn_team_id_1 or not espn_team_id_2:
        print(f"    ❌ Could not extract team IDs from boxscore")
        return 0

    print(f"    Found teams: {espn_team_id_1}, {espn_team_id_2}")

    team1_id, team2_id = resolve_internal_team_ids(conn, espn_team_id_1, espn_team_id_2)

    if not team1_id or not team2_id:
        print(f"    ❌ Could not resolve internal team IDs")
        return 0

    print(f"    Internal team IDs: {team1_id}, {team2_id}")

    batter_lookup, pitcher_lookup, team_info_list = build_player_stats_lookup_mlb(boxscore_data)

    if not batter_lookup and not pitcher_lookup:
        print(f"    No player stats found in boxscore")
        return 0

    # Resolve internal team IDs for team info list
    for team_info in team_info_list:
        try:
            result = conn.execute(text("""
                SELECT team_id FROM teams
                WHERE espn_team_id = :espn_team_id AND sport = 'MLB'
            """), {'espn_team_id': team_info['espn_id']}).fetchone()
            team_info['id'] = result[0] if result else None
        except Exception as e:
            print(f"    ❌ Error resolving team {team_info['name']}: {e}")
            team_info['id'] = None

    print(f"    Built lookup for {len(batter_lookup)} batters, {len(pitcher_lookup)} pitchers from ESPN")

    # Determine doubleheader position for this ESPN game
    espn_game_index = 0
    if all_day_games and espn_team_id_1 and espn_team_id_2:
        espn_game_index = get_doubleheader_game_index(game_id, espn_team_id_1, espn_team_id_2, all_day_games)
        if espn_game_index > 0:
            print(f"    🎯 Doubleheader detected: this is game {espn_game_index + 1} of the day for these teams")

    # Get all prop records for this game from both tables
    batter_records = conn.execute(text("""
        SELECT id, player_id, normalized_name, odds_home_team_id, odds_away_team_id,
               'batter' AS player_type, odds_event_id, created_at
        FROM mlb_batter_props
        WHERE game_date = :game_date
        AND (odds_home_team_id = :team1_id OR odds_away_team_id = :team1_id
             OR odds_home_team_id = :team2_id OR odds_away_team_id = :team2_id)
    """), {
        'game_date': game_date,
        'team1_id': team1_id,
        'team2_id': team2_id
    }).fetchall()

    pitcher_records = conn.execute(text("""
        SELECT id, player_id, normalized_name, odds_home_team_id, odds_away_team_id,
               'pitcher' AS player_type, odds_event_id, created_at
        FROM mlb_pitcher_props
        WHERE game_date = :game_date
        AND (odds_home_team_id = :team1_id OR odds_away_team_id = :team1_id
             OR odds_home_team_id = :team2_id OR odds_away_team_id = :team2_id)
    """), {
        'game_date': game_date,
        'team1_id': team1_id,
        'team2_id': team2_id
    }).fetchall()

    prop_records = list(batter_records) + list(pitcher_records)

    if not prop_records:
        print(f"    No prop records found for these teams on {game_date}")
        return 0

    print(f"    Found {len(prop_records)} prop records to update ({len(batter_records)} batters, {len(pitcher_records)} pitchers)")

    # For doubleheaders: group by (player_id, player_type) and select only the record
    # that corresponds to this ESPN game's position in the day's schedule.
    player_type_groups = defaultdict(list)
    for record in prop_records:
        key = (record[1], record[5])  # (player_id, player_type)
        player_type_groups[key].append(record)

    records_to_process_ids = set()
    for (pid, ptype), recs in player_type_groups.items():
        if len(recs) == 1:
            records_to_process_ids.add(recs[0][0])
        else:
            chosen = select_doubleheader_prop_record(conn, recs, espn_game_index)
            if chosen:
                records_to_process_ids.add(chosen[0])
                print(f"    🎯 Doubleheader: selected record {chosen[0]} (game {espn_game_index + 1}) for {recs[0][2]}")
            else:
                for r in recs:
                    records_to_process_ids.add(r[0])

    prop_records_filtered = [r for r in prop_records if r[0] in records_to_process_ids]

    updated_count = 0

    for record in prop_records_filtered:
        props_id, player_id, normalized_name, odds_home_team_id, odds_away_team_id, player_type, *_ = record

        # Determine table and lookup based on player_type
        if player_type == 'batter':
            table_name = 'mlb_batter_props'
            lookup = batter_lookup
        else:
            table_name = 'mlb_pitcher_props'
            lookup = pitcher_lookup

        try:

            player_stats = find_player_in_lookup(normalized_name, lookup, conn, player_id, props_id)

            if not player_stats:
                try:
                    other_props = conn.execute(text(f"""
                        SELECT DISTINCT p.espn_player_id
                        FROM {table_name} pp
                        JOIN mlb_players p ON pp.player_id = p.id
                        WHERE pp.player_id = :player_id AND pp.id != :props_id
                    """), {'player_id': player_id, 'props_id': props_id}).fetchall()

                    espn_ids = [row[0] for row in other_props if row[0] is not None]
                    unique_espn_ids = set(espn_ids)

                    if len(unique_espn_ids) == 1:
                        print(f"      ℹ️  Player not in ESPN data (likely DNP): {normalized_name} (has ESPN ID {list(unique_espn_ids)[0]} from other games)")
                        continue

                    if len(unique_espn_ids) == 0:
                        print(f"      ⚠️  No ESPN ID found in any records for {normalized_name}")
                    else:
                        print(f"      ⚠️  Inconsistent ESPN IDs for {normalized_name}: {unique_espn_ids}")

                    home_team_name = conn.execute(text("""
                        SELECT team_name FROM teams WHERE team_id = :team_id
                    """), {'team_id': odds_home_team_id}).fetchone()

                    away_team_name = conn.execute(text("""
                        SELECT team_name FROM teams WHERE team_id = :team_id
                    """), {'team_id': odds_away_team_id}).fetchone()

                    home_team_str = home_team_name[0] if home_team_name else 'Unknown'
                    away_team_str = away_team_name[0] if away_team_name else 'Unknown'

                    if player_type == 'batter':
                        mismatch_id_col = 'batter_props_id'
                    else:
                        mismatch_id_col = 'pitcher_props_id'

                    existing_mismatch = conn.execute(text(f"""
                        SELECT id FROM mlb_player_name_mismatch
                        WHERE {mismatch_id_col} = :props_id AND resolved = false
                    """), {'props_id': props_id}).fetchone()

                    if not existing_mismatch:
                        conn.execute(text(f"""
                            INSERT INTO mlb_player_name_mismatch (
                                {mismatch_id_col},
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

            # Backfill ESPN ID if needed
            espn_player_id = player_stats.get('espn_player_id')
            is_dnp = player_stats.get('did_not_play', False)

            if espn_player_id and player_id:
                existing_espn_id = conn.execute(text("""
                    SELECT espn_player_id FROM mlb_players WHERE id = :player_id
                """), {'player_id': player_id}).fetchone()

                if existing_espn_id and not existing_espn_id[0]:
                    id_in_use = conn.execute(text("""
                        SELECT id FROM mlb_players WHERE espn_player_id = :espn_player_id
                    """), {'espn_player_id': str(espn_player_id)}).fetchone()

                    if not id_in_use:
                        conn.execute(text("""
                            UPDATE mlb_players
                            SET espn_player_id = :espn_player_id
                            WHERE id = :player_id
                        """), {
                            'espn_player_id': str(espn_player_id),
                            'player_id': player_id
                        })

            # Determine player's team and opponent
            player_team_espn_id = player_stats.get('player_team_espn_id')
            player_team_name = player_stats.get('player_team_name', 'Unknown')

            player_team_id = None
            opponent_team_id = None
            opponent_team_name = 'Unknown'

            for team_info in team_info_list:
                if team_info['espn_id'] == player_team_espn_id:
                    player_team_id = team_info['id']
                    break

            for team_info in team_info_list:
                if team_info['espn_id'] != player_team_espn_id:
                    opponent_team_id = team_info['id']
                    opponent_team_name = team_info['name']
                    break

            if is_dnp:
                conn.execute(text(f"""
                    UPDATE {table_name}
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
            elif player_type == 'batter':
                conn.execute(text(f"""
                    UPDATE {table_name}
                    SET actual_batter_hits = :hits,
                        actual_batter_home_runs = :home_runs,
                        actual_batter_rbi = :rbi,
                        actual_batter_runs_scored = :runs_scored,
                        actual_batter_at_bats = :at_bats,
                        actual_batter_walks = :walks,
                        actual_batter_strikeouts = :strikeouts,
                        player_team_name = :team_name,
                        player_team_id = :team_id,
                        opponent_team_name = :opponent_team_name,
                        opponent_team_id = :opponent_team_id,
                        espn_event_id = :espn_event_id,
                        did_not_play = false,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :record_id
                """), {
                    'hits': player_stats['actual_batter_hits'],
                    'home_runs': player_stats['actual_batter_home_runs'],
                    'rbi': player_stats['actual_batter_rbi'],
                    'runs_scored': player_stats['actual_batter_runs_scored'],
                    'at_bats': player_stats['actual_batter_at_bats'],
                    'walks': player_stats['actual_batter_walks'],
                    'strikeouts': player_stats['actual_batter_strikeouts'],
                    'team_name': player_team_name,
                    'team_id': player_team_id,
                    'opponent_team_name': opponent_team_name,
                    'opponent_team_id': opponent_team_id,
                    'espn_event_id': game_id,
                    'record_id': props_id
                })
                print(f"      ✅ {normalized_name} ({player_team_name} vs {opponent_team_name}): {player_stats['actual_batter_hits']}H/{player_stats['actual_batter_home_runs']}HR/{player_stats['actual_batter_rbi']}RBI")
            elif player_type == 'pitcher':
                conn.execute(text(f"""
                    UPDATE {table_name}
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
                    'espn_event_id': game_id,
                    'record_id': props_id
                })
                print(f"      ✅ {normalized_name} ({player_team_name} vs {opponent_team_name}): {player_stats['actual_pitcher_strikeouts']}K/{player_stats['actual_pitcher_earned_runs']}ER/{player_stats['actual_pitcher_innings_pitched']}IP")

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
    Import historical MLB player actuals for a specific date using reverse approach.
    """
    print(f"\n=== Importing Historical MLB Player Actuals (Reverse) for {target_date} ===")

    all_day_games = get_mlb_games_for_date(target_date)

    if not all_day_games:
        print(f"No games found for {target_date}")
        return 0

    total_updated = 0

    for i, game_info in enumerate(all_day_games, 1):
        game_id = game_info['game_id']
        game_datetime = game_info['game_datetime']
        print(f"\n  Processing game {i}/{len(all_day_games)}: {game_id}")

        try:
            updated = process_game_reverse(conn, game_id, target_date, game_datetime, all_day_games)
            total_updated += updated

            if i < len(all_day_games):
                time.sleep(2)

        except Exception as e:
            print(f"    ❌ Error processing game {game_id}: {e}")
            continue

    return total_updated


def import_historical_actuals_date_range_reverse(start_date: date, end_date: date):
    """
    Import historical MLB player actual stats for a date range using reverse approach.
    """
    print(f"=== Historical MLB Player Actuals Import (Reverse Approach) ===")
    print(f"Date range: {start_date} to {end_date}")

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

                conn.commit()
                print(f"✅ Committed {daily_updated} records for {current_date}")

            except Exception as e:
                print(f"❌ Error processing {current_date}: {e}")
                conn.rollback()

            current_date += timedelta(days=1)

            if current_date <= end_date:
                time.sleep(3)

        print(f"\n🎉 Historical MLB actuals import complete!")
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
        print("Usage: python3 mlb_historical_player_actuals_import_reverse.py YYYY-MM-DD [YYYY-MM-DD]")
        print("Example: python3 mlb_historical_player_actuals_import_reverse.py 2025-07-02")
        print("Example: python3 mlb_historical_player_actuals_import_reverse.py 2025-07-01 2025-07-07")
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
