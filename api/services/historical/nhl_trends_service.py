
"""NHL Trends Service - Analyze historical NHL game trends."""

import os
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime
import concurrent.futures
import time

from .base_service import BaseHistoricalService
from .nhl_service import NHLService

class NHLTrendsService(BaseHistoricalService):
    @classmethod
    def _batch_fetch_all_team_games(cls, teams: Set[str], limit: int) -> Dict[str, List[Dict]]:
        """Batch fetch games for all teams in one database query."""
        try:
            from .nhl_service import NHLService
            conn = NHLService._get_connection()
            if not conn:
                return {}
            placeholders = ','.join(['%s'] * len(teams))
            query = f"""
                SELECT * FROM nhl_games
                WHERE home_team_name IN ({placeholders}) OR away_team_name IN ({placeholders})
                ORDER BY game_date DESC
            """
            params = list(teams) + list(teams)
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                all_games = cursor.fetchall()
            team_games = {team: [] for team in teams}
            for game in all_games:
                if game['home_team_name'] in team_games:
                    team_games[game['home_team_name']].append(game)
                if game['away_team_name'] in team_games:
                    team_games[game['away_team_name']].append(game)
            for team in team_games:
                team_games[team] = sorted(team_games[team], key=lambda x: x['game_date'], reverse=True)[:limit]
            return team_games
        except Exception as e:
            print(f"Error batch fetching team games: {e}")
            return {}
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    @classmethod
    def _batch_fetch_all_head_to_head_games(cls, team_pairs: List[Tuple[str, str]], limit: int) -> Dict[Tuple[str, str], List[Dict]]:
        """Batch fetch head-to-head games for all team pairs in one query."""
        try:
            from .nhl_service import NHLService
            conn = NHLService._get_connection()
            if not conn:
                return {}
            h2h_results = {pair: [] for pair in team_pairs}
            h2h_conditions = []
            params = []
            for home_team, away_team in team_pairs:
                h2h_conditions.append("(home_team_name = %s AND away_team_name = %s) OR (home_team_name = %s AND away_team_name = %s)")
                params.extend([home_team, away_team, away_team, home_team])
            if h2h_conditions:
                query = f"""
                    SELECT * FROM nhl_games
                    WHERE {' OR '.join(h2h_conditions)}
                    ORDER BY game_date DESC
                """
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    all_h2h_games = cursor.fetchall()
                for game in all_h2h_games:
                    for pair in team_pairs:
                        if ((game['home_team_name'], game['away_team_name']) == pair or
                            (game['home_team_name'], game['away_team_name']) == (pair[1], pair[0])):
                            if len(h2h_results[pair]) < limit:
                                h2h_results[pair].append(game)
            return h2h_results
        except Exception as e:
            print(f"Error batch fetching head-to-head games: {e}")
            return {}
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    @classmethod
    def _filter_team_games(cls, games: List[Dict], team_name: str, limit: int) -> List[Dict]:
        return games[:limit]

    @classmethod
    def _analyze_team_trends(cls, games: List[Dict], team_name: str, min_trend_length: int = 3) -> List[Dict]:
        if not games or len(games) < min_trend_length:
            return []
        trends = []
        sorted_games = sorted(games, key=lambda x: x['game_date'], reverse=True)
        def calculate_current_streak(results: List[bool]) -> int:
            streak = 0
            for result in results:
                if result:
                    streak += 1
                else:
                    break
            return streak
        win_results = []
        loss_results = []
        over_results = []
        under_results = []
        for game in sorted_games:
            team_data = cls._get_team_data_from_game(game, team_name)
            if team_data['team_goals'] is not None and team_data['opponent_goals'] is not None:
                if team_data['team_goals'] > team_data['opponent_goals']:
                    win_results.append(True)
                    loss_results.append(False)
                elif team_data['team_goals'] < team_data['opponent_goals']:
                    win_results.append(False)
                    loss_results.append(True)
                else:
                    win_results.append(False)
                    loss_results.append(False)
            actual_total = (game.get('home_goals') or 0) + (game.get('away_goals') or 0)
            total_line = game.get('total')
            if actual_total is not None and total_line is not None:
                if actual_total > total_line:
                    over_results.append(True)
                    under_results.append(False)
                elif actual_total < total_line:
                    over_results.append(False)
                    under_results.append(True)
                else:
                    over_results.append(False)
                    under_results.append(False)
        current_win_streak = calculate_current_streak(win_results)
        current_loss_streak = calculate_current_streak(loss_results)
        current_over_streak = calculate_current_streak(over_results)
        current_under_streak = calculate_current_streak(under_results)
        if current_win_streak >= min_trend_length:
            trends.append({'type': 'win_streak','count': current_win_streak,'description': f'Won {current_win_streak} straight games'})
        if current_loss_streak >= min_trend_length:
            trends.append({'type': 'loss_streak','count': current_loss_streak,'description': f'Lost {current_loss_streak} straight games'})
        if current_over_streak >= min_trend_length:
            trends.append({'type': 'over_streak','count': current_over_streak,'description': f'Total went OVER {current_over_streak} straight games'})
        if current_under_streak >= min_trend_length:
            trends.append({'type': 'under_streak','count': current_under_streak,'description': f'Total went UNDER {current_under_streak} straight games'})
        return trends

    @classmethod
    def _get_team_data_from_game(cls, game: Dict, team_name: str) -> Dict:
        home_team = game.get('home_team_name')
        away_team = game.get('away_team_name')
        home_goals = game.get('home_goals', 0) or 0
        away_goals = game.get('away_goals', 0) or 0
        team_side = None
        if home_team == team_name:
            team_side = 'home'
        elif away_team == team_name:
            team_side = 'away'
        if team_side == 'home':
            return {'team_goals': home_goals, 'opponent_goals': away_goals}
        elif team_side == 'away':
            return {'team_goals': away_goals, 'opponent_goals': home_goals}
        else:
            return {'team_goals': 0, 'opponent_goals': 0}
    """Service for analyzing NHL game trends from historical data using batched queries."""
    
    @classmethod
    def analyze_multiple_games_trends(cls, games: List[Dict[str, Any]], limit: int = 5, min_trend_length: int = 3) -> Tuple[Optional[List[Dict]], Optional[str]]:
        start_time = time.time()
        print(f"Starting NHL trends analysis for {len(games)} games...")
        try:
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
            all_team_games = cls._batch_fetch_all_team_games(all_teams, limit * 2)
            all_h2h_games = cls._batch_fetch_all_head_to_head_games(team_pairs, limit)
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
                head_to_head_trends = cls._analyze_team_trends(h2h_games, home_team, min_trend_length)
                has_trends = len(home_team_trends) > 0 or len(away_team_trends) > 0 or len(head_to_head_trends) > 0
                results.append({
                    'game': game,
                    'homeTeamTrends': home_team_trends,
                    'awayTeamTrends': away_team_trends,
                    'headToHeadTrends': head_to_head_trends,
                    'hasTrends': has_trends
                })
            end_time = time.time()
            print(f"NHL trends analysis completed in {end_time - start_time:.2f} seconds")
            return results, None
        except Exception as e:
            print(f"Error in NHL trends analysis: {str(e)}")
            return [], f"Error analyzing trends: {str(e)}"
    # Implement _batch_fetch_all_team_games, _batch_fetch_all_head_to_head_games, _filter_team_games, _analyze_team_trends, _get_team_data_from_game as in MLBTrendsService, but adapted for NHL fields.
