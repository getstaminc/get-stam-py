#!/usr/bin/python3

import os
import re
import sys
import requests
import time as _time
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from unidecode import unidecode

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

# NFL boxscore stat groups we care about, keyed by their ESPN 'name' field
RELEVANT_STAT_GROUPS = {'passing', 'rushing', 'receiving'}

# ESPN scoringPlays type.id values for touchdowns that never appear in the
# boxscore's per-athlete passing/rushing/receiving stats: Blocked FG Return,
# Kickoff Return, Punt Return, Interception Return, Blocked Punt, Fumble
# Return, and Sack+Opponent-Fumble-Recovery touchdowns. Found by sampling
# scoringPlays across ~110 games from the 2025 season.
MISC_TD_TYPE_IDS = {'18', '32', '34', '36', '37', '39', '80'}

# Matches the trailing "<Name> <N> Yd" (or "yd.") segment that precedes the
# return/recovery description in ESPN's scoringPlays text, e.g. "Tyler
# Lockett 0 Yd Fumble Recovery (...)" or "DaRon Bland 68 Yd Interception
# Return (...)". The LAST match in the text is used, since a few plays
# mention the scorer twice (e.g. "Blocked Kick Recovered by X (PHI) X 61 Yd
# Touchdown Return").
_MISC_TD_NAME_YARDS_RE = re.compile(r"([A-Z][A-Za-z'.\-]+(?:\s[A-Z][A-Za-z'.\-]+){0,3})\s+(\d+)\s*[Yy]d\.?\s")

# Fallback for the rare play with no yardage in the text (e.g. "George Holani
# Recovered Kickoff in End Zone for a Touchdown") - just the leading run of
# capitalized words.
_MISC_TD_NAME_FALLBACK_RE = re.compile(r"([A-Z][A-Za-z'.\-]+(?:\s[A-Z][A-Za-z'.\-]+){1,2})")


def parse_misc_td_scorer_name(play_text: str) -> Optional[str]:
    """Best-effort extraction of the scoring player's name from a scoringPlays
    'text' field. Returns None if nothing plausible is found."""
    if not play_text:
        return None
    matches = _MISC_TD_NAME_YARDS_RE.findall(play_text)
    if matches:
        return matches[-1][0].strip()
    fallback = _MISC_TD_NAME_FALLBACK_RE.match(play_text)
    return fallback.group(1).strip() if fallback else None


def get_nfl_games_for_date(target_date: date, retries=3, delay=2) -> List[Dict]:
    """
    Get all NFL games for a specific historical date from ESPN.

    Returns a list of dicts sorted by game_datetime:
        {
            'game_id': str,
            'game_datetime': datetime,       # UTC
            'espn_home_team_id': str,
            'espn_away_team_id': str,
        }
    """
    print(f"Fetching NFL games for {target_date}...")

    date_str = target_date.strftime('%Y%m%d')

    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
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

                status = event.get('status', {}).get('type', {}).get('name', '')
                if status != 'STATUS_FINAL':
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
            print(f"  Found {len(games)} completed NFL games for {target_date}")
            return games
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching games (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                _time.sleep(delay * (i + 1))
            else:
                print(f"  Failed to fetch games for {target_date}")
                return []
    return []


def get_game_boxscore(game_id: str, retries=3, delay=2) -> Optional[Dict]:
    """
    Get boxscore data from ESPN for a specific NFL game.
    """
    print(f"    Fetching boxscore for game {game_id}...")

    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
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


def parse_name_parts(normalized_name: str) -> Tuple[str, str]:
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
        if len(odds_first) == 1 and espn_first.startswith(odds_first):
            first_match = True
        elif len(espn_first) == 1 and odds_first.startswith(espn_first):
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


def build_player_stats_lookup_nfl(boxscore_data: Dict) -> Tuple[Dict, List[Dict]]:
    """
    Build a unified player stat lookup from an ESPN NFL boxscore.

    Unlike MLB (mutually exclusive batting/pitching blocks) or NBA (one flat stat
    line per player), NFL's boxscore groups stats into named categories (passing,
    rushing, receiving) and the SAME player can appear in more than one category
    (e.g. a rushing RB who also catches passes, or a scrambling QB in both passing
    and rushing). Stats are merged per athlete across all relevant groups.

    Returns:
        Tuple of (player_lookup, team_info_list)
        - player_lookup: normalized_name -> merged stat dict
        - team_info_list: list of dicts with 'name', 'espn_id'
    """
    player_lookup: Dict[str, Dict] = {}
    team_info_list: List[Dict] = []

    boxscore = boxscore_data.get('boxscore', {})
    teams = boxscore.get('players', [])

    if not teams:
        return player_lookup, team_info_list

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

        for stat_block in statistics:
            group_name = stat_block.get('name', '')
            if group_name not in RELEVANT_STAT_GROUPS:
                continue

            keys = stat_block.get('keys', [])
            athletes = stat_block.get('athletes', [])

            for athlete_data in athletes:
                try:
                    athlete = athlete_data.get('athlete', {})
                    stats = athlete_data.get('stats', [])

                    espn_player_id = str(athlete.get('id', ''))
                    player_name = athlete.get('displayName', '')

                    if not espn_player_id or not player_name or not stats:
                        continue

                    if len(stats) != len(keys):
                        continue

                    stat_dict = dict(zip(keys, stats))
                    normalized_name = normalize_player_name(player_name)

                    if normalized_name not in player_lookup:
                        player_lookup[normalized_name] = {
                            'espn_player_id': espn_player_id,
                            'player_name': player_name,
                            'normalized_name': normalized_name,
                            'did_not_play': False,
                            'player_team_espn_id': team_espn_id,
                            'player_team_name': team_name,
                            'actual_pass_yds': None,
                            'actual_pass_tds': None,
                            'actual_rush_yds': None,
                            'actual_rush_tds': None,
                            'actual_receptions': None,
                            'actual_reception_yds': None,
                            'actual_receiving_tds': None,
                        }

                    record = player_lookup[normalized_name]

                    if group_name == 'passing':
                        record['actual_pass_yds'] = safe_int(stat_dict.get('passingYards'))
                        record['actual_pass_tds'] = safe_int(stat_dict.get('passingTouchdowns'))
                    elif group_name == 'rushing':
                        record['actual_rush_yds'] = safe_int(stat_dict.get('rushingYards'))
                        record['actual_rush_tds'] = safe_int(stat_dict.get('rushingTouchdowns'))
                    elif group_name == 'receiving':
                        record['actual_receptions'] = safe_int(stat_dict.get('receptions'))
                        record['actual_reception_yds'] = safe_int(stat_dict.get('receivingYards'))
                        record['actual_receiving_tds'] = safe_int(stat_dict.get('receivingTouchdowns'))

                except Exception as e:
                    print(f"        Error processing player in {group_name}: {e}")
                    continue

    # Merge in inactive/DNP players from the injuries section (mirrors NBA's approach) -
    # a player with no offensive stat line isn't necessarily inactive (e.g. an O-lineman),
    # so we only mark players explicitly listed as "Out" to avoid false DNPs.
    injuries = boxscore_data.get('injuries', [])
    for injury_entry in injuries:
        team_info = injury_entry.get('team', {})
        team_name = team_info.get('displayName', 'Unknown Team')
        team_espn_id = str(team_info.get('id', ''))

        for injury_detail in injury_entry.get('injuries', []):
            athlete = injury_detail.get('athlete', {})
            status = injury_detail.get('status', '')
            espn_player_id = str(athlete.get('id', ''))
            player_name = athlete.get('displayName', '')

            if not espn_player_id or not player_name or status != 'Out':
                continue

            normalized_name = normalize_player_name(player_name)
            if normalized_name not in player_lookup:
                player_lookup[normalized_name] = {
                    'espn_player_id': espn_player_id,
                    'player_name': player_name,
                    'normalized_name': normalized_name,
                    'did_not_play': True,
                    'player_team_espn_id': team_espn_id,
                    'player_team_name': team_name,
                    'actual_pass_yds': None,
                    'actual_pass_tds': None,
                    'actual_rush_yds': None,
                    'actual_rush_tds': None,
                    'actual_receptions': None,
                    'actual_reception_yds': None,
                    'actual_receiving_tds': None,
                }

    return player_lookup, team_info_list


def get_team_ids_from_boxscore(boxscore_data: Dict) -> Tuple[Optional[str], Optional[str]]:
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


def resolve_internal_team_ids(conn, espn_team_id_1: str, espn_team_id_2: str) -> Tuple[Optional[int], Optional[int]]:
    """Resolve ESPN team IDs to internal team_ids from teams table."""
    team1_id = None
    team2_id = None

    try:
        result = conn.execute(text("""
            SELECT team_id FROM teams
            WHERE espn_team_id = :espn_team_id AND sport = 'NFL'
        """), {'espn_team_id': espn_team_id_1}).fetchone()

        if result:
            team1_id = result[0]
    except Exception as e:
        print(f"    ❌ Error resolving team {espn_team_id_1}: {e}")

    try:
        result = conn.execute(text("""
            SELECT team_id FROM teams
            WHERE espn_team_id = :espn_team_id AND sport = 'NFL'
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
    normalized_name = normalize_player_name(normalized_name)

    player_espn_id = conn.execute(text("""
        SELECT espn_player_id FROM nfl_players WHERE id = :player_id
    """), {'player_id': player_id}).fetchone()

    if player_espn_id and player_espn_id[0]:
        for espn_name, stats in lookup.items():
            if stats.get('espn_player_id') == player_espn_id[0]:
                print(f"      ⚡ Matched by ESPN ID: {normalized_name} (ID: {player_espn_id[0]})")
                return stats

    player_stats = lookup.get(normalized_name)
    if player_stats:
        print(f"      ✓ Exact name match: {normalized_name}")
        return player_stats

    try:
        alias_results = conn.execute(text("""
            SELECT normalized_name FROM nfl_player_aliases
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

    for espn_name, stats in lookup.items():
        if names_match_strict(normalized_name, espn_name):
            print(f"      🔍 Strict name match (suffix stripped): {normalized_name} → {espn_name}")
            return stats

    return None


def apply_misc_touchdowns(
    conn,
    boxscore_data: Dict,
    game_date: date,
    espn_team_id_1: str,
    espn_team_id_2: str,
    team1_id: int,
    team2_id: int,
) -> int:
    """
    Parse ESPN's scoringPlays feed for TD types the boxscore's per-athlete stats
    never capture (return/recovery TDs - see MISC_TD_TYPE_IDS), match the scorer
    against this game's existing nfl_player_props rows, and set actual_misc_td /
    actual_player_anytime_td on the matched row.

    Only touches players who already have a prop row for this game (i.e. had an
    odds line) - a scorer with no prop row has nothing to correct, so they're
    skipped and logged rather than backfilled.

    Recomputes a total count per player rather than incrementing, so this is
    safe to re-run for the same game without double-counting.
    """
    scoring_plays = boxscore_data.get('scoringPlays', [])
    misc_td_plays = [p for p in scoring_plays if (p.get('type') or {}).get('id') in MISC_TD_TYPE_IDS]

    if not misc_td_plays:
        return 0

    prop_rows = conn.execute(text("""
        SELECT id, normalized_name, player_team_id
        FROM nfl_player_props
        WHERE game_date = :game_date
          AND ((odds_home_team_id = :team1_id AND odds_away_team_id = :team2_id)
               OR (odds_home_team_id = :team2_id AND odds_away_team_id = :team1_id))
    """), {
        'game_date': game_date,
        'team1_id': team1_id,
        'team2_id': team2_id,
    }).fetchall()

    # Tally misc TD counts per matched record_id first, so a re-run SETs the
    # correct total instead of incrementing on top of a prior run's value.
    counts_by_record_id: Dict[int, int] = {}

    for play in misc_td_plays:
        play_type_text = (play.get('type') or {}).get('text', 'Misc TD')
        play_text = play.get('text', '')
        scoring_espn_team_id = str((play.get('team') or {}).get('id', ''))

        if scoring_espn_team_id == espn_team_id_1:
            scoring_team_id = team1_id
        elif scoring_espn_team_id == espn_team_id_2:
            scoring_team_id = team2_id
        else:
            print(f"      ⚠️  Misc TD play team {scoring_espn_team_id} not in this game: {play_text}")
            continue

        scorer_name = parse_misc_td_scorer_name(play_text)
        if not scorer_name:
            print(f"      ⚠️  Could not parse scorer name from misc TD play: {play_text}")
            continue

        normalized_scorer = normalize_player_name(scorer_name)

        record_id = None
        for row in prop_rows:
            if row.player_team_id and row.player_team_id != scoring_team_id:
                continue
            if row.normalized_name == normalized_scorer or names_match_strict(normalized_scorer, row.normalized_name):
                record_id = row.id
                break

        if record_id is None:
            print(f"      ℹ️  No existing prop row for misc TD scorer (skipped): "
                  f"{scorer_name} ({play_type_text})")
            continue

        counts_by_record_id[record_id] = counts_by_record_id.get(record_id, 0) + 1
        print(f"      ✅ Misc TD matched: {scorer_name} - {play_type_text}")

    for record_id, count in counts_by_record_id.items():
        conn.execute(text("""
            UPDATE nfl_player_props
            SET actual_misc_td = :count,
                actual_player_anytime_td = true,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :record_id
        """), {'count': count, 'record_id': record_id})

    return len(counts_by_record_id)


def process_game_reverse(conn, game_id: str, game_date: date) -> int:
    """
    Process a single NFL game using the reverse approach.
    """
    print(f"\n  Processing game: {game_id}")

    boxscore_data = get_game_boxscore(game_id)

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

    player_lookup, team_info_list = build_player_stats_lookup_nfl(boxscore_data)

    if not player_lookup:
        print(f"    No player stats found in boxscore")
        return 0

    for team_info in team_info_list:
        try:
            result = conn.execute(text("""
                SELECT team_id FROM teams
                WHERE espn_team_id = :espn_team_id AND sport = 'NFL'
            """), {'espn_team_id': team_info['espn_id']}).fetchone()
            team_info['id'] = result[0] if result else None
        except Exception as e:
            print(f"    ❌ Error resolving team {team_info['name']}: {e}")
            team_info['id'] = None

    print(f"    Built lookup for {len(player_lookup)} players from ESPN")

    prop_records = conn.execute(text("""
        SELECT id, player_id, normalized_name, odds_home_team_id, odds_away_team_id
        FROM nfl_player_props
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

    updated_count = 0

    for record in prop_records:
        props_id, player_id, normalized_name, odds_home_team_id, odds_away_team_id = record

        try:
            player_stats = find_player_in_lookup(normalized_name, player_lookup, conn, player_id, props_id)

            if not player_stats:
                try:
                    other_props = conn.execute(text("""
                        SELECT DISTINCT p.espn_player_id
                        FROM nfl_player_props pp
                        JOIN nfl_players p ON pp.player_id = p.id
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

                    existing_mismatch = conn.execute(text("""
                        SELECT id FROM nfl_player_name_mismatch
                        WHERE nfl_player_props_id = :props_id AND resolved = false
                    """), {'props_id': props_id}).fetchone()

                    if not existing_mismatch:
                        conn.execute(text("""
                            INSERT INTO nfl_player_name_mismatch (
                                nfl_player_props_id, game_date, odds_home_team_id, odds_away_team_id,
                                odds_home_team, odds_away_team, normalized_name, player_id,
                                resolved, created_at, updated_at
                            ) VALUES (
                                :props_id, :game_date, :home_team_id, :away_team_id,
                                :home_team_name, :away_team_name, :normalized_name, :player_id,
                                false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            )
                        """), {
                            'props_id': props_id, 'game_date': game_date,
                            'home_team_id': odds_home_team_id, 'away_team_id': odds_away_team_id,
                            'home_team_name': home_team_str, 'away_team_name': away_team_str,
                            'normalized_name': normalized_name, 'player_id': player_id
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
                    SELECT espn_player_id FROM nfl_players WHERE id = :player_id
                """), {'player_id': player_id}).fetchone()

                if existing_espn_id and not existing_espn_id[0]:
                    id_in_use = conn.execute(text("""
                        SELECT id FROM nfl_players WHERE espn_player_id = :espn_player_id
                    """), {'espn_player_id': str(espn_player_id)}).fetchone()

                    if not id_in_use:
                        conn.execute(text("""
                            UPDATE nfl_players SET espn_player_id = :espn_player_id
                            WHERE id = :player_id
                        """), {'espn_player_id': str(espn_player_id), 'player_id': player_id})

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
                conn.execute(text("""
                    UPDATE nfl_player_props
                    SET player_team_name = :team_name, player_team_id = :team_id,
                        opponent_team_name = :opponent_team_name, opponent_team_id = :opponent_team_id,
                        espn_event_id = :espn_event_id, did_not_play = true,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :record_id
                """), {
                    'team_name': player_team_name, 'team_id': player_team_id,
                    'opponent_team_name': opponent_team_name, 'opponent_team_id': opponent_team_id,
                    'espn_event_id': game_id, 'record_id': props_id
                })
                print(f"      🚫 DNP: {normalized_name} ({player_team_name} vs {opponent_team_name})")
            else:
                rush_td = player_stats.get('actual_rush_tds') or 0
                rec_td = player_stats.get('actual_receiving_tds') or 0
                anytime_td = (rush_td + rec_td) > 0

                conn.execute(text("""
                    UPDATE nfl_player_props
                    SET actual_player_pass_yds = :pass_yds,
                        actual_player_pass_tds = :pass_tds,
                        actual_player_rush_yds = :rush_yds,
                        actual_player_rushing_td = :rushing_td,
                        actual_player_reception_yds = :reception_yds,
                        actual_player_receptions = :receptions,
                        actual_player_receiving_td = :receiving_td,
                        actual_player_anytime_td = :anytime_td,
                        player_team_name = :team_name, player_team_id = :team_id,
                        opponent_team_name = :opponent_team_name, opponent_team_id = :opponent_team_id,
                        espn_event_id = :espn_event_id, did_not_play = false,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :record_id
                """), {
                    'pass_yds': player_stats.get('actual_pass_yds'),
                    'pass_tds': player_stats.get('actual_pass_tds'),
                    'rush_yds': player_stats.get('actual_rush_yds'),
                    'rushing_td': player_stats.get('actual_rush_tds'),
                    'reception_yds': player_stats.get('actual_reception_yds'),
                    'receptions': player_stats.get('actual_receptions'),
                    'receiving_td': player_stats.get('actual_receiving_tds'),
                    'anytime_td': anytime_td,
                    'team_name': player_team_name, 'team_id': player_team_id,
                    'opponent_team_name': opponent_team_name, 'opponent_team_id': opponent_team_id,
                    'espn_event_id': game_id, 'record_id': props_id
                })
                print(f"      ✅ {normalized_name} ({player_team_name} vs {opponent_team_name}): "
                      f"{player_stats.get('actual_pass_yds') or 0}pass_yds/"
                      f"{player_stats.get('actual_rush_yds') or 0}rush_yds/"
                      f"{player_stats.get('actual_reception_yds') or 0}rec_yds/"
                      f"{player_stats.get('actual_receptions') or 0}rec/"
                      f"anytime_td={anytime_td}")

            updated_count += 1

        except Exception as e:
            print(f"      ❌ Error updating {normalized_name}: {e}")
            conn.rollback()
            conn.begin()
            continue

    print(f"    Successfully updated {updated_count} prop records")

    misc_td_updated = apply_misc_touchdowns(
        conn, boxscore_data, game_date, espn_team_id_1, espn_team_id_2, team1_id, team2_id
    )
    if misc_td_updated:
        print(f"    Applied misc TDs to {misc_td_updated} prop records")

    return updated_count


def import_historical_actuals_for_date_reverse(target_date: date, conn) -> int:
    """
    Import historical NFL player actuals for a specific date using reverse approach.
    """
    print(f"\n=== Importing Historical NFL Player Actuals (Reverse) for {target_date} ===")

    all_day_games = get_nfl_games_for_date(target_date)

    if not all_day_games:
        print(f"No games found for {target_date}")
        return 0

    total_updated = 0

    for i, game_info in enumerate(all_day_games, 1):
        game_id = game_info['game_id']
        print(f"\n  Processing game {i}/{len(all_day_games)}: {game_id}")

        try:
            updated = process_game_reverse(conn, game_id, target_date)
            total_updated += updated

            if i < len(all_day_games):
                _time.sleep(2)

        except Exception as e:
            print(f"    ❌ Error processing game {game_id}: {e}")
            continue

    return total_updated


def import_historical_actuals_date_range_reverse(start_date: date, end_date: date):
    """
    Import historical NFL player actual stats for a date range using reverse approach.
    """
    print(f"=== Historical NFL Player Actuals Import (Reverse Approach) ===")
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
                _time.sleep(3)

        print(f"\n🎉 Historical NFL actuals import complete!")
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
        print("Usage: python3 nfl_historical_player_actuals_import_reverse.py YYYY-MM-DD [YYYY-MM-DD]")
        print("Example: python3 nfl_historical_player_actuals_import_reverse.py 2025-10-05")
        print("Example: python3 nfl_historical_player_actuals_import_reverse.py 2025-10-05 2025-10-06")
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
