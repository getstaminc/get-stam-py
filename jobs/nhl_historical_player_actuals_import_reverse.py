#!/usr/bin/python3
"""Historical NHL player-prop actuals import from ESPN's free site API,
mirroring jobs/nfl_historical_player_actuals_import_reverse.py's "reverse"
approach: fetch ESPN's boxscore once per game, then match every nhl_player_props
row for that game against it (rather than resolving player-by-player).

Team resolution uses shared_utils.convert_team_name (teams.espn_team_id is
unpopulated for NHL). "skaters" is always empty in ESPN's NHL boxscore --
real skater stats live in "forwards" and "defenses", which never overlap.
"""
import os
import sys
import time as _time
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import requests
from unidecode import unidecode
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shared_utils

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

SKATER_STAT_GROUPS = {'forwards', 'defenses'}


def normalize_player_name(name: str) -> str:
    if not name:
        return ''
    normalized = unidecode(name).lower()
    normalized = normalized.replace("'", "").replace("-", "").replace(".", "")
    return ' '.join(normalized.split())


def strip_name_suffix(normalized_name: str) -> str:
    for suffix in [' jr', ' sr', ' ii', ' iii', ' iv', ' v']:
        if normalized_name.endswith(suffix):
            return normalized_name[:-len(suffix)].strip()
    return normalized_name


def parse_name_parts(normalized_name: str) -> Tuple[str, str]:
    parts = normalized_name.strip().split()
    if not parts:
        return '', ''
    if len(parts) == 1:
        return '', parts[0]
    return ' '.join(parts[:-1]), parts[-1]


def names_match_strict(odds_name: str, espn_name: str) -> bool:
    odds_first, odds_last = parse_name_parts(strip_name_suffix(odds_name))
    espn_first, espn_last = parse_name_parts(strip_name_suffix(espn_name))
    first_match = odds_first == espn_first
    if not first_match and odds_first and espn_first:
        first_match = (len(odds_first) == 1 and espn_first.startswith(odds_first)) or \
                      (len(espn_first) == 1 and odds_first.startswith(espn_first))
    return first_match and odds_last == espn_last


def safe_int(value) -> Optional[int]:
    if value is None or value == '':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def get_nhl_games_for_date(target_date: date, retries=3, delay=2) -> List[Dict]:
    """Returns completed NHL games for target_date, sorted by start time:
    [{'game_id', 'game_datetime', 'espn_home_team_id', 'espn_away_team_id'}, ...]"""
    date_str = target_date.strftime('%Y%m%d')
    url = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
    for i in range(retries):
        try:
            response = requests.get(url, params={'dates': date_str, 'limit': 50}, timeout=30)
            response.raise_for_status()
            _time.sleep(0.2)
            data = response.json()
            games = []
            for event in data.get('events', []):
                comp = event.get('competitions', [{}])[0]
                if not comp.get('status', {}).get('type', {}).get('completed'):
                    continue
                game_datetime = None
                if event.get('date'):
                    game_datetime = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
                espn_home_id = espn_away_id = None
                for competitor in comp.get('competitors', []):
                    if competitor.get('homeAway') == 'home':
                        espn_home_id = str(competitor.get('team', {}).get('id', ''))
                    elif competitor.get('homeAway') == 'away':
                        espn_away_id = str(competitor.get('team', {}).get('id', ''))
                games.append({
                    'game_id': event.get('id'), 'game_datetime': game_datetime,
                    'espn_home_team_id': espn_home_id, 'espn_away_team_id': espn_away_id,
                })
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            games.sort(key=lambda g: g['game_datetime'] or epoch)
            return games
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching games (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                _time.sleep(delay * (i + 1))
            else:
                return []
    return []


def get_game_boxscore(game_id: str, retries=3, delay=2) -> Optional[Dict]:
    url = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary"
    for i in range(retries):
        try:
            response = requests.get(url, params={'event': game_id, 'enable': 'boxscore'}, timeout=30)
            response.raise_for_status()
            _time.sleep(0.2)
            data = response.json()
            if not data.get('boxscore'):
                return None
            return data
        except requests.exceptions.RequestException as e:
            print(f"    Error fetching boxscore (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                _time.sleep(delay * (i + 1))
            else:
                return None
    return None


def build_player_stats_lookup_nhl(boxscore_data: Dict) -> Tuple[Dict, List[Dict]]:
    """Build a normalized_name -> stat dict lookup from an ESPN NHL boxscore.
    Skater stats come from 'forwards'+'defenses' (never overlapping; 'skaters'
    is always empty); goalie stats from 'goalies'. points = goals + assists."""
    player_lookup: Dict[str, Dict] = {}
    team_info_list: List[Dict] = []

    for team_data in boxscore_data.get('boxscore', {}).get('players', []):
        team_info = team_data.get('team', {})
        team_name = team_info.get('displayName', 'Unknown Team')
        team_espn_id = str(team_info.get('id', ''))
        team_info_list.append({'name': team_name, 'espn_id': team_espn_id})

        for stat_block in team_data.get('statistics', []):
            group_name = stat_block.get('name', '')
            keys = stat_block.get('keys', [])
            athletes = stat_block.get('athletes', [])
            if group_name not in SKATER_STAT_GROUPS and group_name != 'goalies':
                continue

            for athlete_data in athletes:
                athlete = athlete_data.get('athlete', {})
                stats = athlete_data.get('stats', [])
                espn_player_id = str(athlete.get('id', ''))
                player_name = athlete.get('displayName', '')
                if not espn_player_id or not player_name or len(stats) != len(keys):
                    continue

                stat_dict = dict(zip(keys, stats))
                normalized_name = normalize_player_name(player_name)

                if normalized_name not in player_lookup:
                    player_lookup[normalized_name] = {
                        'espn_player_id': espn_player_id, 'player_name': player_name,
                        'normalized_name': normalized_name, 'did_not_play': False,
                        'player_team_espn_id': team_espn_id, 'player_team_name': team_name,
                        'actual_goals': None, 'actual_assists': None,
                        'actual_shots_on_goal': None, 'actual_total_saves': None,
                    }
                record = player_lookup[normalized_name]

                if group_name in SKATER_STAT_GROUPS:
                    record['actual_goals'] = safe_int(stat_dict.get('goals'))
                    record['actual_assists'] = safe_int(stat_dict.get('assists'))
                    record['actual_shots_on_goal'] = safe_int(stat_dict.get('shotsTotal'))
                elif group_name == 'goalies':
                    record['actual_total_saves'] = safe_int(stat_dict.get('saves'))

    return player_lookup, team_info_list


def get_team_ids_from_boxscore(boxscore_data: Dict) -> Tuple[Optional[str], Optional[str]]:
    teams = boxscore_data.get('boxscore', {}).get('players', [])
    ids = [str(t.get('team', {}).get('id', '')) for t in teams if t.get('team', {}).get('id')]
    return (ids[0], ids[1]) if len(ids) >= 2 else (None, None)


def resolve_internal_team_id_by_espn_name(conn, team_info_list: List[Dict]) -> None:
    """Mutates each entry in team_info_list, setting its internal 'id' by
    resolving the ESPN displayName through convert_team_name."""
    for team_info in team_info_list:
        db_name = shared_utils.convert_team_name(team_info['name'])
        result = conn.execute(text("""
            SELECT team_id FROM teams WHERE team_name = :team_name AND sport = 'NHL'
        """), {'team_name': db_name}).fetchone()
        team_info['id'] = result[0] if result else None


def find_player_in_lookup(normalized_name: str, lookup: Dict, conn, player_id: int) -> Optional[Dict]:
    """4-step match: ESPN ID -> exact normalized name -> alias table -> strict
    first+last name."""
    normalized_name = normalize_player_name(normalized_name)

    player_row = conn.execute(text("""
        SELECT espn_player_id FROM nhl_players WHERE id = :player_id
    """), {'player_id': player_id}).fetchone()
    if player_row and player_row[0]:
        for stats in lookup.values():
            if stats.get('espn_player_id') == player_row[0]:
                return stats

    player_stats = lookup.get(normalized_name)
    if player_stats:
        return player_stats

    alias_rows = conn.execute(text("""
        SELECT normalized_name FROM nhl_player_aliases WHERE player_id = :player_id
    """), {'player_id': player_id}).fetchall()
    for alias_row in alias_rows:
        player_stats = lookup.get(alias_row[0])
        if player_stats:
            return player_stats

    for espn_name, stats in lookup.items():
        if names_match_strict(normalized_name, espn_name):
            return stats

    return None


def process_game_reverse(conn, game_id: str, game_date: date) -> int:
    """Fetch one ESPN boxscore and update every nhl_player_props row for that
    game. Unmatched players with a known ESPN id whose current team matches
    this game are marked did_not_play; everyone else gets a nhl_player_name_mismatch
    row for manual review."""
    boxscore_data = get_game_boxscore(game_id)
    if not boxscore_data:
        return 0

    espn_team_id_1, espn_team_id_2 = get_team_ids_from_boxscore(boxscore_data)
    if not espn_team_id_1 or not espn_team_id_2:
        print("    Could not extract team IDs from boxscore")
        return 0

    player_lookup, team_info_list = build_player_stats_lookup_nhl(boxscore_data)
    resolve_internal_team_id_by_espn_name(conn, team_info_list)

    team1_id = next((t['id'] for t in team_info_list if t['espn_id'] == espn_team_id_1), None)
    team2_id = next((t['id'] for t in team_info_list if t['espn_id'] == espn_team_id_2), None)
    if not team1_id or not team2_id:
        print("    Could not resolve internal team IDs")
        return 0

    prop_records = conn.execute(text("""
        SELECT id, player_id, normalized_name, odds_home_team_id, odds_away_team_id
        FROM nhl_player_props
        WHERE game_date = :game_date
          AND (odds_home_team_id IN (:team1_id, :team2_id) OR odds_away_team_id IN (:team1_id, :team2_id))
    """), {'game_date': game_date, 'team1_id': team1_id, 'team2_id': team2_id}).fetchall()

    updated_count = 0
    for props_id, player_id, normalized_name, odds_home_team_id, odds_away_team_id in prop_records:
        player_stats = find_player_in_lookup(normalized_name, player_lookup, conn, player_id)

        if not player_stats:
            player_row = conn.execute(text("""
                SELECT espn_player_id, team_id FROM nhl_players WHERE id = :player_id
            """), {'player_id': player_id}).fetchone()
            confirmed_espn_id = player_row[0] if player_row else None

            if confirmed_espn_id and player_row[1] in (team1_id, team2_id):
                conn.execute(text("""
                    UPDATE nhl_player_props
                    SET espn_event_id = :espn_event_id, did_not_play = true,
                        actuals_unavailable_reason = 'did_not_play', updated_at = CURRENT_TIMESTAMP
                    WHERE id = :record_id
                """), {'espn_event_id': game_id, 'record_id': props_id})
            elif not confirmed_espn_id:
                home_name = conn.execute(text("SELECT team_name FROM teams WHERE team_id = :id"), {'id': odds_home_team_id}).fetchone()
                away_name = conn.execute(text("SELECT team_name FROM teams WHERE team_id = :id"), {'id': odds_away_team_id}).fetchone()
                existing = conn.execute(text("""
                    SELECT id FROM nhl_player_name_mismatch WHERE nhl_player_props_id = :props_id AND resolved = false
                """), {'props_id': props_id}).fetchone()
                if not existing:
                    conn.execute(text("""
                        INSERT INTO nhl_player_name_mismatch (
                            nhl_player_props_id, game_date, odds_home_team_id, odds_away_team_id,
                            odds_home_team, odds_away_team, normalized_name, player_id, resolved, created_at, updated_at
                        ) VALUES (
                            :props_id, :game_date, :home_id, :away_id, :home_name, :away_name,
                            :normalized_name, :player_id, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                    """), {
                        'props_id': props_id, 'game_date': game_date, 'home_id': odds_home_team_id,
                        'away_id': odds_away_team_id, 'home_name': home_name[0] if home_name else 'Unknown',
                        'away_name': away_name[0] if away_name else 'Unknown',
                        'normalized_name': normalized_name, 'player_id': player_id,
                    })
            continue

        espn_player_id = player_stats.get('espn_player_id')
        if espn_player_id and player_id:
            existing_espn_id = conn.execute(text("SELECT espn_player_id FROM nhl_players WHERE id = :id"), {'id': player_id}).fetchone()
            if existing_espn_id and not existing_espn_id[0]:
                in_use = conn.execute(text("SELECT id FROM nhl_players WHERE espn_player_id = :id"), {'id': str(espn_player_id)}).fetchone()
                if not in_use:
                    conn.execute(text("UPDATE nhl_players SET espn_player_id = :id WHERE id = :pid"),
                                 {'id': str(espn_player_id), 'pid': player_id})

        player_team_espn_id = player_stats.get('player_team_espn_id')
        player_team_id = next((t['id'] for t in team_info_list if t['espn_id'] == player_team_espn_id), None)
        opponent_info = next((t for t in team_info_list if t['espn_id'] != player_team_espn_id), None)

        if player_stats.get('did_not_play'):
            conn.execute(text("""
                UPDATE nhl_player_props
                SET player_team_name = :team_name, player_team_id = :team_id,
                    opponent_team_name = :opp_name, opponent_team_id = :opp_id,
                    espn_event_id = :espn_event_id, did_not_play = true, updated_at = CURRENT_TIMESTAMP
                WHERE id = :record_id
            """), {
                'team_name': player_stats.get('player_team_name'), 'team_id': player_team_id,
                'opp_name': opponent_info['name'] if opponent_info else 'Unknown',
                'opp_id': opponent_info['id'] if opponent_info else None,
                'espn_event_id': game_id, 'record_id': props_id,
            })
            updated_count += 1
            continue

        goals = player_stats.get('actual_goals')
        assists = player_stats.get('actual_assists')
        points = (goals or 0) + (assists or 0) if (goals is not None or assists is not None) else None

        conn.execute(text("""
            UPDATE nhl_player_props
            SET actual_player_goals = :goals, actual_player_assists = :assists,
                actual_player_points = :points, actual_player_shots_on_goal = :sog,
                actual_player_total_saves = :saves,
                actual_player_goal_scorer_anytime = :scored_anytime,
                player_team_name = :team_name, player_team_id = :team_id,
                opponent_team_name = :opp_name, opponent_team_id = :opp_id,
                espn_event_id = :espn_event_id, updated_at = CURRENT_TIMESTAMP
            WHERE id = :record_id
        """), {
            'goals': goals, 'assists': assists, 'points': points,
            'sog': player_stats.get('actual_shots_on_goal'),
            'saves': player_stats.get('actual_total_saves'),
            'scored_anytime': (goals or 0) > 0 if goals is not None else None,
            'team_name': player_stats.get('player_team_name'), 'team_id': player_team_id,
            'opp_name': opponent_info['name'] if opponent_info else 'Unknown',
            'opp_id': opponent_info['id'] if opponent_info else None,
            'espn_event_id': game_id, 'record_id': props_id,
        })
        updated_count += 1

    return updated_count


def import_historical_actuals_for_date_reverse(target_date: date, conn) -> int:
    games = get_nhl_games_for_date(target_date)
    print(f"\n=== Importing NHL Actuals for {target_date} ({len(games)} games) ===")
    total = 0
    for game in games:
        total += process_game_reverse(conn, game['game_id'], target_date)
    return total


def import_historical_actuals_date_range_reverse(start_date: date, end_date: date):
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        current_date = start_date
        total = 0
        while current_date <= end_date:
            try:
                total += import_historical_actuals_for_date_reverse(current_date, conn)
                conn.commit()
            except Exception as e:
                print(f"Error processing {current_date}: {e}")
                conn.rollback()
            current_date += timedelta(days=1)
        print(f"\nTotal records updated: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        start = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end = datetime.strptime(sys.argv[2], '%Y-%m-%d').date() if len(sys.argv) >= 3 else start
    else:
        start = end = date.today() - timedelta(days=1)
    import_historical_actuals_date_range_reverse(start, end)
