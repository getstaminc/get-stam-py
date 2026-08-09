#!/usr/bin/python3

import os
import sys
import time as _time
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Reuse the NFL scoreboard/boxscore fetchers and team-id resolution already
# built for skill-position player actuals - the ESPN data source and game
# discovery are identical, only the stat groups consumed differ.
from jobs.nfl_historical_player_actuals_import_reverse import (
    get_nfl_games_for_date,
    get_game_boxscore,
    get_team_ids_from_boxscore,
    resolve_internal_team_ids,
    safe_int,
)

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

# Team-level boxscore stat groups relevant to D/ST props, keyed by ESPN 'name' field.
DEFENSE_STAT_GROUPS = {'defensive', 'interceptions', 'kickReturns', 'puntReturns'}

# Fields that can carry a fraction (half-sacks, yards-per-return averages).
DECIMAL_FIELDS = {'sacks', 'yardsPerKickReturn', 'yardsPerPuntReturn'}


def safe_decimal(value) -> Optional[float]:
    """Safely convert a value to a rounded float, return None if not possible."""
    if value is None or value == '':
        return None
    try:
        return round(float(value), 1)
    except (ValueError, TypeError):
        return None


def build_team_defense_stats_lookup(boxscore_data: Dict) -> Dict[str, Dict]:
    """
    Build a per-team defense/special-teams stat lookup from an ESPN NFL boxscore.

    Unlike individual player stats, D/ST props resolve off TEAM-wide totals, so
    this reads the 'totals' array of each relevant stat_block rather than the
    per-athlete 'athletes' array. An empty totals array means nobody on that
    team recorded a stat in that group this game (e.g. no punt returns), which
    is a real zero rather than missing data.

    Returns: espn_team_id -> stat dict (includes 'team_name', 'team_espn_id').
    """
    lookup: Dict[str, Dict] = {}

    boxscore = boxscore_data.get('boxscore', {})
    teams = boxscore.get('players', [])

    for team_data in teams:
        team_info = team_data.get('team', {})
        team_name = team_info.get('displayName', 'Unknown Team')
        team_espn_id = str(team_info.get('id', ''))

        if not team_espn_id:
            continue

        stats = {
            'team_name': team_name,
            'team_espn_id': team_espn_id,
            'actual_total_tackles': 0,
            'actual_solo_tackles': 0,
            'actual_sacks': 0,
            'actual_tackles_for_loss': 0,
            'actual_passes_defended': 0,
            'actual_qb_hits': 0,
            'actual_defensive_touchdowns': 0,
            'actual_interceptions': 0,
            'actual_interception_yards': 0,
            'actual_interception_touchdowns': 0,
            'actual_kick_returns': 0,
            'actual_kick_return_yards': 0,
            'actual_yards_per_kick_return': 0,
            'actual_long_kick_return': 0,
            'actual_kick_return_touchdowns': 0,
            'actual_punt_returns': 0,
            'actual_punt_return_yards': 0,
            'actual_yards_per_punt_return': 0,
            'actual_long_punt_return': 0,
            'actual_punt_return_touchdowns': 0,
        }

        for stat_block in team_data.get('statistics', []):
            group_name = stat_block.get('name', '')
            if group_name not in DEFENSE_STAT_GROUPS:
                continue

            keys = stat_block.get('keys', [])
            totals = stat_block.get('totals', [])
            totals_map = dict(zip(keys, totals)) if len(totals) == len(keys) else {}

            def get_num(key: str):
                raw = totals_map.get(key)
                return safe_decimal(raw) if key in DECIMAL_FIELDS else safe_int(raw)

            if group_name == 'defensive':
                stats['actual_total_tackles'] = get_num('totalTackles') or 0
                stats['actual_solo_tackles'] = get_num('soloTackles') or 0
                stats['actual_sacks'] = get_num('sacks') or 0
                stats['actual_tackles_for_loss'] = get_num('tacklesForLoss') or 0
                stats['actual_passes_defended'] = get_num('passesDefended') or 0
                stats['actual_qb_hits'] = get_num('QBHits') or 0
                stats['actual_defensive_touchdowns'] = get_num('defensiveTouchdowns') or 0
            elif group_name == 'interceptions':
                stats['actual_interceptions'] = get_num('interceptions') or 0
                stats['actual_interception_yards'] = get_num('interceptionYards') or 0
                stats['actual_interception_touchdowns'] = get_num('interceptionTouchdowns') or 0
            elif group_name == 'kickReturns':
                stats['actual_kick_returns'] = get_num('kickReturns') or 0
                stats['actual_kick_return_yards'] = get_num('kickReturnYards') or 0
                stats['actual_yards_per_kick_return'] = get_num('yardsPerKickReturn') or 0
                stats['actual_long_kick_return'] = get_num('longKickReturn') or 0
                stats['actual_kick_return_touchdowns'] = get_num('kickReturnTouchdowns') or 0
            elif group_name == 'puntReturns':
                stats['actual_punt_returns'] = get_num('puntReturns') or 0
                stats['actual_punt_return_yards'] = get_num('puntReturnYards') or 0
                stats['actual_yards_per_punt_return'] = get_num('yardsPerPuntReturn') or 0
                stats['actual_long_punt_return'] = get_num('longPuntReturn') or 0
                stats['actual_punt_return_touchdowns'] = get_num('puntReturnTouchdowns') or 0

        lookup[team_espn_id] = stats

    return lookup


def process_game_defense_reverse(conn, game_id: str, game_date: date) -> int:
    """
    Update nfl_defense_props actuals for both teams in a single NFL game.
    """
    print(f"\n  Processing game (defense): {game_id}")

    boxscore_data = get_game_boxscore(game_id)
    if not boxscore_data:
        return 0

    espn_team_id_1, espn_team_id_2 = get_team_ids_from_boxscore(boxscore_data)
    if not espn_team_id_1 or not espn_team_id_2:
        print(f"    ❌ Could not extract team IDs from boxscore")
        return 0

    team1_id, team2_id = resolve_internal_team_ids(conn, espn_team_id_1, espn_team_id_2)
    if not team1_id or not team2_id:
        print(f"    ❌ Could not resolve internal team IDs")
        return 0

    internal_id_by_espn = {espn_team_id_1: team1_id, espn_team_id_2: team2_id}
    espn_by_internal_id = {team1_id: espn_team_id_1, team2_id: espn_team_id_2}

    team_defense_lookup = build_team_defense_stats_lookup(boxscore_data)

    defense_records = conn.execute(text("""
        SELECT id, team_id
        FROM nfl_defense_props
        WHERE game_date = :game_date
        AND (team_id = :team1_id OR team_id = :team2_id)
    """), {
        'game_date': game_date,
        'team1_id': team1_id,
        'team2_id': team2_id
    }).fetchall()

    if not defense_records:
        print(f"    No D/ST prop records found for these teams on {game_date}")
        return 0

    updated_count = 0

    for record_id, team_id in defense_records:
        espn_team_id = espn_by_internal_id.get(team_id)
        stats = team_defense_lookup.get(espn_team_id)

        if not stats:
            print(f"      ⚠️  No ESPN defense stats found for team_id {team_id}")
            continue

        opponent_espn_id = espn_team_id_2 if espn_team_id == espn_team_id_1 else espn_team_id_1
        opponent_stats = team_defense_lookup.get(opponent_espn_id)
        opponent_team_id = internal_id_by_espn.get(opponent_espn_id)
        opponent_team_name = opponent_stats['team_name'] if opponent_stats else 'Unknown'

        anytime_td = (
            (stats['actual_defensive_touchdowns'] or 0)
            + (stats['actual_interception_touchdowns'] or 0)
            + (stats['actual_kick_return_touchdowns'] or 0)
            + (stats['actual_punt_return_touchdowns'] or 0)
        ) > 0

        try:
            conn.execute(text("""
                UPDATE nfl_defense_props
                SET actual_total_tackles = :total_tackles,
                    actual_solo_tackles = :solo_tackles,
                    actual_sacks = :sacks,
                    actual_tackles_for_loss = :tackles_for_loss,
                    actual_passes_defended = :passes_defended,
                    actual_qb_hits = :qb_hits,
                    actual_defensive_touchdowns = :defensive_touchdowns,
                    actual_interceptions = :interceptions,
                    actual_interception_yards = :interception_yards,
                    actual_interception_touchdowns = :interception_touchdowns,
                    actual_kick_returns = :kick_returns,
                    actual_kick_return_yards = :kick_return_yards,
                    actual_yards_per_kick_return = :yards_per_kick_return,
                    actual_long_kick_return = :long_kick_return,
                    actual_kick_return_touchdowns = :kick_return_touchdowns,
                    actual_punt_returns = :punt_returns,
                    actual_punt_return_yards = :punt_return_yards,
                    actual_yards_per_punt_return = :yards_per_punt_return,
                    actual_long_punt_return = :long_punt_return,
                    actual_punt_return_touchdowns = :punt_return_touchdowns,
                    actual_anytime_td = :anytime_td,
                    team_name = :team_name,
                    opponent_team_name = :opponent_team_name,
                    opponent_team_id = :opponent_team_id,
                    espn_event_id = :espn_event_id,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :record_id
            """), {
                'total_tackles': stats['actual_total_tackles'],
                'solo_tackles': stats['actual_solo_tackles'],
                'sacks': stats['actual_sacks'],
                'tackles_for_loss': stats['actual_tackles_for_loss'],
                'passes_defended': stats['actual_passes_defended'],
                'qb_hits': stats['actual_qb_hits'],
                'defensive_touchdowns': stats['actual_defensive_touchdowns'],
                'interceptions': stats['actual_interceptions'],
                'interception_yards': stats['actual_interception_yards'],
                'interception_touchdowns': stats['actual_interception_touchdowns'],
                'kick_returns': stats['actual_kick_returns'],
                'kick_return_yards': stats['actual_kick_return_yards'],
                'yards_per_kick_return': stats['actual_yards_per_kick_return'],
                'long_kick_return': stats['actual_long_kick_return'],
                'kick_return_touchdowns': stats['actual_kick_return_touchdowns'],
                'punt_returns': stats['actual_punt_returns'],
                'punt_return_yards': stats['actual_punt_return_yards'],
                'yards_per_punt_return': stats['actual_yards_per_punt_return'],
                'long_punt_return': stats['actual_long_punt_return'],
                'punt_return_touchdowns': stats['actual_punt_return_touchdowns'],
                'anytime_td': anytime_td,
                'team_name': stats['team_name'],
                'opponent_team_name': opponent_team_name,
                'opponent_team_id': opponent_team_id,
                'espn_event_id': game_id,
                'record_id': record_id,
            })

            print(f"      ✅ {stats['team_name']} vs {opponent_team_name}: "
                  f"anytime_td={anytime_td} "
                  f"(def_td={stats['actual_defensive_touchdowns']}, "
                  f"int_td={stats['actual_interception_touchdowns']}, "
                  f"kr_td={stats['actual_kick_return_touchdowns']}, "
                  f"pr_td={stats['actual_punt_return_touchdowns']})")

            updated_count += 1

        except Exception as e:
            print(f"      ❌ Error updating team_id {team_id}: {e}")
            conn.rollback()
            conn.begin()
            continue

    print(f"    Successfully updated {updated_count} D/ST prop records")
    return updated_count


def import_historical_defense_actuals_for_date_reverse(target_date: date, conn) -> int:
    """
    Import historical NFL D/ST actuals for a specific date.
    """
    print(f"\n=== Importing Historical NFL Defense Actuals for {target_date} ===")

    all_day_games = get_nfl_games_for_date(target_date)

    if not all_day_games:
        print(f"No games found for {target_date}")
        return 0

    total_updated = 0

    for i, game_info in enumerate(all_day_games, 1):
        game_id = game_info['game_id']
        print(f"\n  Processing game {i}/{len(all_day_games)}: {game_id}")

        try:
            updated = process_game_defense_reverse(conn, game_id, target_date)
            total_updated += updated

            if i < len(all_day_games):
                _time.sleep(2)

        except Exception as e:
            print(f"    ❌ Error processing game {game_id}: {e}")
            continue

    return total_updated


def import_historical_defense_actuals_date_range_reverse(start_date: date, end_date: date):
    """
    Import historical NFL D/ST actual stats for a date range.
    """
    print(f"=== Historical NFL Defense Actuals Import ===")
    print(f"Date range: {start_date} to {end_date}")

    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    try:
        current_date = start_date
        total_updated = 0

        while current_date <= end_date:
            try:
                daily_updated = import_historical_defense_actuals_for_date_reverse(
                    current_date, conn
                )

                total_updated += daily_updated

                conn.commit()
                print(f"✅ Committed {daily_updated} D/ST records for {current_date}")

            except Exception as e:
                print(f"❌ Error processing {current_date}: {e}")
                conn.rollback()

            current_date += timedelta(days=1)

            if current_date <= end_date:
                _time.sleep(3)

        print(f"\n🎉 Historical NFL defense actuals import complete!")
        print(f"Total D/ST prop records updated: {total_updated}")
        print(f"Date range: {start_date} to {end_date}")

    except Exception as e:
        print(f"❌ Fatal error during historical import: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 nfl_historical_defense_actuals_import_reverse.py YYYY-MM-DD [YYYY-MM-DD]")
        print("Example: python3 nfl_historical_defense_actuals_import_reverse.py 2025-10-05")
        print("Example: python3 nfl_historical_defense_actuals_import_reverse.py 2025-10-05 2025-10-06")
        sys.exit(1)

    from datetime import datetime

    start_date_str = sys.argv[1]
    end_date_str = sys.argv[2] if len(sys.argv) > 2 else start_date_str

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    import_historical_defense_actuals_date_range_reverse(start_date, end_date)
