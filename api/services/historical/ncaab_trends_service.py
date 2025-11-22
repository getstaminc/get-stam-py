"""NCAAB Trends Service - Analyze historical NCAAB game trends."""

import os
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime
import time

from .base_service import BaseHistoricalService
from .ncaab_service import NCAABService


class NCAABTrendsService(BaseHistoricalService):
    """Service for analyzing NCAAB game trends from historical data using batched queries."""

    @staticmethod
    def _norm_name(s: Optional[str]) -> Optional[str]:
        if s is None:
            return None
        try:
            return s.strip().lower()
        except Exception:
            return s
    
    @classmethod
    def analyze_multiple_games_trends(
        cls,
        games: List[Dict[str, Any]],
        limit: int = 5,
        min_trend_length: int = 3
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Analyze trends for multiple NCAAB games using batched database queries."""
        start_time = time.time()
        print(f"Starting NCAAB trends analysis for {len(games)} games...")

        try:
            # Step 1: Collect all unique teams from all games
            all_teams = set()
            team_pairs = []

            for game in games:
                home_team = game.get('home', {}).get('team') or game.get('home_team_name')
                away_team = game.get('away', {}).get('team') or game.get('away_team_name')
                if home_team and away_team:
                    all_teams.add(home_team)
                    all_teams.add(away_team)
                    team_pairs.append((home_team, away_team))

            if not all_teams:
                return [], "No valid teams found in games"

            print(f"Found {len(all_teams)} unique teams: {list(all_teams)}")

            # Step 2: Batch fetch all team games data
            all_team_games = cls._batch_fetch_all_team_games(all_teams, limit * 2)

            # Step 3: Batch fetch head-to-head data for all team pairs
            all_h2h_games = cls._batch_fetch_all_head_to_head_games(team_pairs, limit)

            # Step 4: Analyze trends for each game using the cached data
            results = []
            for game in games:
                home_team = game.get('home', {}).get('team') or game.get('home_team_name')
                away_team = game.get('away', {}).get('team') or game.get('away_team_name')

                if not home_team or not away_team:
                    results.append({
                        'game': game,
                        'homeTeamTrends': [],
                        'awayTeamTrends': [],
                        'headToHeadTrends': [],
                        'hasTrends': False
                    })
                    continue

                home_team_games = cls._filter_team_games(all_team_games.get(home_team, []), home_team, limit)
                away_team_games = cls._filter_team_games(all_team_games.get(away_team, []), away_team, limit)
                h2h_games = all_h2h_games.get((home_team, away_team), [])[:limit]

                home_team_trends = cls._analyze_team_trends(home_team_games, home_team, min_trend_length)
                away_team_trends = cls._analyze_team_trends(away_team_games, away_team, min_trend_length)

                # For H2H, analyze only for the home team (consistent with UI expectation)
                # Ensure team_side is set correctly for H2H games
                h2h_games_with_side = []
                for g in h2h_games:
                    g_copy = dict(g)
                    # Prefer resolved original names (added in the H2H fetch)
                    # since DB may store short nicknames (e.g. 'Hawks').
                    if g_copy.get('home_team_orig') == home_team:
                        g_copy['team_side'] = 'home'
                    elif g_copy.get('away_team_orig') == home_team:
                        g_copy['team_side'] = 'away'
                    else:
                        # Fallback: compare normalized DB names to the requested
                        # home team name, and also allow a last-word match
                        db_home_norm = cls._norm_name(g_copy.get('home_team_name'))
                        db_away_norm = cls._norm_name(g_copy.get('away_team_name'))
                        home_norm = cls._norm_name(home_team)
                        home_last = None
                        if home_norm and ' ' in home_norm:
                            home_last = home_norm.split()[-1]

                        if home_norm and (db_home_norm == home_norm or (home_last and db_home_norm == home_last)):
                            g_copy['team_side'] = 'home'
                        elif home_norm and (db_away_norm == home_norm or (home_last and db_away_norm == home_last)):
                            g_copy['team_side'] = 'away'
                        else:
                            g_copy['team_side'] = None
                    h2h_games_with_side.append(g_copy)

                head_to_head_trends = cls._analyze_team_trends(h2h_games_with_side, home_team, min_trend_length)

                has_trends = len(home_team_trends) > 0 or len(away_team_trends) > 0 or len(head_to_head_trends) > 0

                results.append({
                    'game': game,
                    'homeTeamTrends': home_team_trends,
                    'awayTeamTrends': away_team_trends,
                    'headToHeadTrends': head_to_head_trends,
                    'hasTrends': has_trends
                })

            end_time = time.time()
            print(f"NCAAB trends analysis completed in {end_time - start_time:.2f} seconds")
            return results, None

        except Exception as e:
            print(f"Error in NCAAB trends analysis: {str(e)}")
            return [], f"Error analyzing trends: {str(e)}"

    @classmethod
    def _batch_fetch_all_team_games(cls, teams: Set[str], limit: int) -> Dict[str, List[Dict]]:
        """Batch fetch games for all teams in one database query."""
        try:
            import sys
            sys.path.append('/Users/stephaniegillen/Projects/get-stam-api')
            from shared_utils import convert_team_name

            # Build a combined list of possible DB keys: converted short names,
            # original full names, and a last-word fallback (e.g. 'Hawks'). This
            # helps match rows even when naming conventions differ.
            short_names = [convert_team_name(team) for team in teams]
            combined = []
            for k in short_names + list(teams):
                if k not in combined:
                    combined.append(k)
            for team in teams:
                if isinstance(team, str) and ' ' in team:
                    last = team.split()[-1]
                    if last not in combined:
                        combined.append(last)

            conn = NCAABService._get_connection()
            if not conn:
                return {}

            placeholders = ','.join(['%s'] * len(combined))
            query = f"""
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_points, away_points, total_points, home_line, away_line,
                    home_money_line, away_money_line, total_points, total
                FROM ncaab_games
                WHERE (home_team_name IN ({placeholders}) OR away_team_name IN ({placeholders}))
                ORDER BY game_date DESC
            """
            params = combined + combined

            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                all_games = cursor.fetchall()

            team_games = {team: [] for team in teams}
            # Map DB name variants (normalized) back to the original requested
            # team name.
            def _norm(v):
                try:
                    return v.strip().lower() if v is not None else None
                except Exception:
                    return v

            original_to_db_name = {}
            for team in teams:
                original_to_db_name[ _norm(convert_team_name(team)) ] = team
                original_to_db_name[ _norm(team) ] = team
                if isinstance(team, str) and ' ' in team:
                    original_to_db_name[ _norm(team.split()[-1]) ] = team

            for game in all_games:
                game_dict = dict(game)
                db_home = _norm(game_dict.get('home_team_name'))
                db_away = _norm(game_dict.get('away_team_name'))
                if db_home in original_to_db_name:
                    original_home = original_to_db_name[db_home]
                    game_with_side = dict(game_dict)
                    game_with_side['team_side'] = 'home'
                    team_games[original_home].append(game_with_side)
                if db_away in original_to_db_name:
                    original_away = original_to_db_name[db_away]
                    game_with_side = dict(game_dict)
                    game_with_side['team_side'] = 'away'
                    team_games[original_away].append(game_with_side)

            for team in team_games:
                team_games[team] = sorted(team_games[team], key=lambda x: x['game_date'], reverse=True)[:limit]

            print(f"Batch fetched games for {len(team_games)} teams")
            return team_games

        except Exception as e:
            print(f"Error batch fetching team games: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    @classmethod
    def _batch_fetch_all_head_to_head_games(cls, team_pairs: List[Tuple[str, str]], limit: int) -> Dict[Tuple[str, str], List[Dict]]:
        """Batch fetch head-to-head games for all team pairs in one query."""
        try:
            all_teams_in_pairs = set()
            for home, away in team_pairs:
                all_teams_in_pairs.add(home)
                all_teams_in_pairs.add(away)

            team_id_map = cls._get_team_id_mapping(all_teams_in_pairs)
            conn = NCAABService._get_connection()
            if not conn:
                return {}

            h2h_conditions = []
            params = []
            valid_pairs = []
            for home_team, away_team in team_pairs:
                home_team_id = team_id_map.get(home_team)
                away_team_id = team_id_map.get(away_team)
                if home_team_id and away_team_id:
                    h2h_conditions.append("(home_team_id = %s AND away_team_id = %s) OR (home_team_id = %s AND away_team_id = %s)")
                    params.extend([home_team_id, away_team_id, away_team_id, home_team_id])
                    valid_pairs.append((home_team, away_team))

            h2h_results = {pair: [] for pair in team_pairs}
            if h2h_conditions:
                query = f"""
                    SELECT 
                        game_id, game_date, home_team_name, away_team_name, home_points, away_points,
                        total_points, home_line, away_line, home_money_line, away_money_line,
                        total_points, home_team_id, away_team_id, total
                    FROM ncaab_games
                    WHERE ({' OR '.join(h2h_conditions)})
                    ORDER BY game_date DESC
                """
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    all_h2h_games = cursor.fetchall()

                reverse_team_id_map = {v: k for k, v in team_id_map.items()}
                for game in all_h2h_games:
                    game_dict = dict(game)
                    home_team_orig = reverse_team_id_map.get(game_dict['home_team_id'])
                    away_team_orig = reverse_team_id_map.get(game_dict['away_team_id'])
                    # Attach the resolved original names so callers can reliably
                    # determine which side the requested team played on even when
                    # the DB stores short/team nicknames.
                    game_dict['home_team_orig'] = home_team_orig
                    game_dict['away_team_orig'] = away_team_orig
                    for home, away in valid_pairs:
                        if ((home_team_orig == home and away_team_orig == away) or 
                            (home_team_orig == away and away_team_orig == home)):
                            if len(h2h_results[(home, away)]) < limit:
                                h2h_results[(home, away)].append(game_dict)
                            break

            print(f"Batch fetched head-to-head games for {len(team_pairs)} team pairs in single query")
            return h2h_results

        except Exception as e:
            print(f"Error batch fetching head-to-head games: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    @classmethod
    def _get_team_id_mapping(cls, teams: Set[str]) -> Dict[str, int]:
        """Get team ID mapping for all teams in one query."""
        try:
            import sys
            sys.path.append('/Users/stephaniegillen/Projects/get-stam-api')
            from shared_utils import convert_team_name

            db_team_names = [convert_team_name(team) for team in teams]
            conn = NCAABService._get_connection()
            if not conn:
                return {}

            placeholders = ','.join(['%s'] * len(db_team_names))
            query = f"""
                SELECT team_name, team_id 
                FROM teams 
                WHERE team_name IN ({placeholders}) AND UPPER(sport) = 'NCAAB'
            """
            with conn.cursor() as cursor:
                cursor.execute(query, db_team_names)
                results = cursor.fetchall()

            db_to_original = {convert_team_name(team): team for team in teams}
            team_id_map = {}
            for db_name, team_id in results:
                if db_name in db_to_original:
                    original_name = db_to_original[db_name]
                    team_id_map[original_name] = team_id

            return team_id_map

        except Exception as e:
            print(f"Error getting team ID mapping: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    @classmethod
    def _filter_team_games(cls, games: List[Dict], team_name: str, limit: int) -> List[Dict]:
        """Filter and limit games for a specific team."""
        return games[:limit]

    @classmethod
    def _analyze_team_trends(cls, games: List[Dict], team_name: str, min_trend_length: int) -> List[Dict]:
        """Analyze trends for a team's games. Basic NCAAB logic similar to NFL service."""
        trends = []
        if len(games) < min_trend_length:
            return trends

        # Sort by date (most recent first)
        sorted_games = sorted(games, key=lambda x: x['game_date'], reverse=True)

        # Helper to calculate current streak
        def calc_streak(results: List[bool]) -> int:
            streak = 0
            for r in results:
                if r:
                    streak += 1
                else:
                    break
            return streak

        win_results = []
        loss_results = []
        cover_results = []
        no_cover_results = []
        over_results = []
        under_results = []

        for g in sorted_games:
            team_side = g.get('team_side')
            home_points = g.get('home_points')
            away_points = g.get('away_points')
            home_line = g.get('home_line')
            away_line = g.get('away_line')
            total_line = g.get('total') or g.get('total_points')
            home_team = g.get('home_team_name')
            away_team = g.get('away_team_name')

            if team_side == 'home' or home_team == team_name:
                team_points = home_points
                opp_points = away_points
                team_line = home_line
            else:
                team_points = away_points
                opp_points = home_points
                team_line = away_line

            # Win/Loss
            if team_points is not None and opp_points is not None:
                win_results.append(team_points > opp_points)
                loss_results.append(team_points < opp_points)

            # Spread
            if team_line is not None and team_points is not None and opp_points is not None:
                covered = (team_points + (team_line or 0)) > opp_points
                not_covered = (team_points + (team_line or 0)) < opp_points
                cover_results.append(covered)
                no_cover_results.append(not_covered)

            # Totals
            if home_points is not None and away_points is not None and total_line is not None:
                total = (home_points or 0) + (away_points or 0)
                over_results.append(total > total_line)
                under_results.append(total < total_line)

        current_win_streak = calc_streak(win_results)
        current_loss_streak = calc_streak(loss_results)
        current_cover_streak = calc_streak(cover_results)
        current_no_cover_streak = calc_streak(no_cover_results)
        current_over_streak = calc_streak(over_results)
        current_under_streak = calc_streak(under_results)

        if current_win_streak >= min_trend_length:
            trends.append({'type': 'win_streak', 'count': current_win_streak, 'description': f'Won {current_win_streak} straight games'})
        if current_loss_streak >= min_trend_length:
            trends.append({'type': 'loss_streak', 'count': current_loss_streak, 'description': f'Lost {current_loss_streak} straight games'})
        if current_cover_streak >= min_trend_length:
            trends.append({'type': 'cover_streak', 'count': current_cover_streak, 'description': f'Covered {current_cover_streak} straight spreads'})
        if current_no_cover_streak >= min_trend_length:
            trends.append({'type': 'no_cover_streak', 'count': current_no_cover_streak, 'description': f'Failed to cover {current_no_cover_streak} straight spreads'})
        if current_over_streak >= min_trend_length:
            trends.append({'type': 'over_streak', 'count': current_over_streak, 'description': f'Total went OVER {current_over_streak} straight games'})
        if current_under_streak >= min_trend_length:
            trends.append({'type': 'under_streak', 'count': current_under_streak, 'description': f'Total went UNDER {current_under_streak} straight games'})

        return trends
