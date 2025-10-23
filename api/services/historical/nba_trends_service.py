"""NBA Trends Service - Analyze historical NBA game trends."""

import os
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime
import time

from .base_service import BaseHistoricalService
from .nba_service import NBAService


class NBATrendsService(BaseHistoricalService):
    """Service for analyzing NBA game trends from historical data using batched queries."""
    
    @classmethod
    def analyze_multiple_games_trends(
        cls,
        games: List[Dict[str, Any]],
        limit: int = 5,
        min_trend_length: int = 3
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Analyze trends for multiple NBA games using batched database queries."""
        start_time = time.time()
        print(f"Starting NBA trends analysis for {len(games)} games...")

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
                    if g_copy.get('home_team_name') == home_team:
                        g_copy['team_side'] = 'home'
                    elif g_copy.get('away_team_name') == home_team:
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
            print(f"NBA trends analysis completed in {end_time - start_time:.2f} seconds")
            return results, None

        except Exception as e:
            print(f"Error in NBA trends analysis: {str(e)}")
            return [], f"Error analyzing trends: {str(e)}"

    @classmethod
    def _batch_fetch_all_team_games(cls, teams: Set[str], limit: int) -> Dict[str, List[Dict]]:
        """Batch fetch games for all teams in one database query."""
        try:
            import sys
            sys.path.append('/Users/stephaniegillen/Projects/get-stam-api')
            from shared_utils import convert_team_name

            db_team_names = [convert_team_name(team) for team in teams]
            conn = NBAService._get_connection()
            if not conn:
                return {}

            placeholders = ','.join(['%s'] * len(db_team_names))
            query = f"""
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_points, away_points, total_points, home_line, away_line,
                    home_money_line, away_money_line, total_points
                FROM nba_games
                WHERE (home_team_name IN ({placeholders}) OR away_team_name IN ({placeholders}))
                ORDER BY game_date DESC
            """
            params = db_team_names + db_team_names

            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                all_games = cursor.fetchall()

            team_games = {team: [] for team in teams}
            original_to_db_name = {convert_team_name(team): team for team in teams}

            for game in all_games:
                game_dict = dict(game)
                if game_dict['home_team_name'] in original_to_db_name:
                    original_home = original_to_db_name[game_dict['home_team_name']]
                    game_with_side = dict(game_dict)
                    game_with_side['team_side'] = 'home'
                    team_games[original_home].append(game_with_side)
                if game_dict['away_team_name'] in original_to_db_name:
                    original_away = original_to_db_name[game_dict['away_team_name']]
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
            conn = NBAService._get_connection()
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
                        total_points, home_team_id, away_team_id
                    FROM nba_games
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
            conn = NBAService._get_connection()
            if not conn:
                return {}

            placeholders = ','.join(['%s'] * len(db_team_names))
            query = f"""
                SELECT team_name, team_id 
                FROM teams 
                WHERE team_name IN ({placeholders}) AND UPPER(sport) = 'NBA'
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
        """Analyze trends for a team's games. Basic NBA logic similar to NFL service."""
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
