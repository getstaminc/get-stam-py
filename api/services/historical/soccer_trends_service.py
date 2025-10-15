"""Soccer Trends Service - Analyze historical soccer game trends."""

import os
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime
import concurrent.futures
import time
import threading

from .base_service import BaseHistoricalService
from .soccer_service import SoccerService


class SoccerTrendsService(BaseHistoricalService):
    """Service for analyzing soccer game trends from historical data using batched queries."""
    
    @classmethod
    def analyze_multiple_games_trends(
        cls,
        games: List[Dict[str, Any]],
        limit: int = 5,
        min_trend_length: int = 3,
        sport_key: str = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Analyze trends for multiple soccer games using batched database queries."""
        start_time = time.time()
        print(f"Starting soccer trends analysis for {len(games)} games...")

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

            # Map sportKey to league name
            league = None
            sport_key_to_league = {
                'soccer_epl': 'EPL',
                'soccer_uefa_champs_league': 'UCL',
                'soccer_uefa_europa_league': 'UEL',
                'soccer_uefa_conference_league': 'UECL',
                # Add more mappings as needed
            }
            if sport_key:
                league = sport_key_to_league.get(sport_key)
            all_team_games = cls._batch_fetch_all_team_games(all_teams, limit * 2, league)  # Get more data than needed

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

                # Extract team-specific games from the batch data
                home_team_games = cls._filter_team_games(all_team_games.get(home_team, []), home_team, limit)
                away_team_games = cls._filter_team_games(all_team_games.get(away_team, []), away_team, limit)
                h2h_games = all_h2h_games.get((home_team, away_team), [])[:limit]
                
                # Analyze trends using the filtered data
                home_team_trends = cls._analyze_team_trends(home_team_games, home_team, min_trend_length)
                away_team_trends = cls._analyze_team_trends(away_team_games, away_team, min_trend_length)


                # For H2H, ensure each game has correct team_side for the home team
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
            print(f"Soccer trends analysis completed in {end_time - start_time:.2f} seconds")

            return results, None

        except Exception as e:
            print(f"Error in soccer trends analysis: {str(e)}")
            return [], f"Error analyzing trends: {str(e)}"
    
    @classmethod
    def _batch_fetch_all_team_games(cls, teams: Set[str], limit: int, league: str = None) -> Dict[str, List[Dict]]:
        """Batch fetch games for all teams in one database query, filtered by league if provided."""
        try:
            import sys
            sys.path.append('/Users/stephaniegillen/Projects/get-stam-api')
            from soccer_utils import translate_soccer_team_name

            # Convert all team names to database format
            db_team_names = [translate_soccer_team_name(team) for team in teams]

            conn = SoccerService._get_connection()
            if not conn:
                return {}

            # Determine league filter
            league_filter = ""
            league_param = []
            if league:
                league_filter = " AND league = %s"
                league_param = [league]

            placeholders = ','.join(['%s'] * len(db_team_names))
            query = f"""
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_goals, away_goals, total_goals, home_spread, away_spread,
                    home_money_line, draw_money_line, away_money_line, start_time, 
                    total_over_point, total_over_price, total_under_point, total_under_price, league
                FROM soccer_games
                WHERE (home_team_name IN ({placeholders}) OR away_team_name IN ({placeholders}))
                {league_filter}
                ORDER BY game_date DESC
            """

            # Double the parameters for both home and away team checks, add league param if needed
            params = db_team_names + db_team_names + league_param

            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                all_games = cursor.fetchall()
            
            # Group games by team
            team_games = {team: [] for team in teams}
            original_to_db_name = {translate_soccer_team_name(team): team for team in teams}
            
            for game in all_games:
                game_dict = dict(game)
                
                # Check if home team is in our list
                if game_dict['home_team_name'] in original_to_db_name:
                    original_home = original_to_db_name[game_dict['home_team_name']]
                    game_with_side = dict(game_dict)
                    game_with_side['team_side'] = 'home'
                    team_games[original_home].append(game_with_side)
                
                # Check if away team is in our list  
                if game_dict['away_team_name'] in original_to_db_name:
                    original_away = original_to_db_name[game_dict['away_team_name']]
                    game_with_side = dict(game_dict)
                    game_with_side['team_side'] = 'away'
                    team_games[original_away].append(game_with_side)
            
            # Sort each team's games by date (most recent first) and apply limit
            for team in team_games:
                team_games[team] = sorted(
                    team_games[team], 
                    key=lambda x: x['game_date'], 
                    reverse=True
                )[:limit]
            
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
        """Batch fetch head-to-head games for all team pairs in one query, with debug output for mapping and query."""
        try:
            # Get team ID mapping for all teams involved
            all_teams_in_pairs = set()
            for home, away in team_pairs:
                all_teams_in_pairs.add(home)
                all_teams_in_pairs.add(away)
            
            team_id_map = cls._get_team_id_mapping(all_teams_in_pairs)
            
            conn = SoccerService._get_connection()
            if not conn:
                return {}
            
            # Build a single query for all head-to-head pairs
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
            
            h2h_results = {pair: [] for pair in team_pairs}  # Initialize all pairs
            
            if h2h_conditions:
                query = f"""
                    SELECT 
                        game_id, game_date, home_team_name, away_team_name, home_goals, away_goals,
                        total_goals, home_spread, away_spread, home_money_line, draw_money_line, away_money_line,
                        start_time, total_over_point, total_over_price, total_under_point, total_under_price,
                        home_team_id, away_team_id
                    FROM soccer_games
                    WHERE ({' OR '.join(h2h_conditions)})
                    ORDER BY game_date DESC
                """
                
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    all_h2h_games = cursor.fetchall()
                
                # Group games by team pairs
                reverse_team_id_map = {v: k for k, v in team_id_map.items()}
                
                for game in all_h2h_games:
                    game_dict = dict(game)
                    home_team_orig = reverse_team_id_map.get(game_dict['home_team_id'])
                    away_team_orig = reverse_team_id_map.get(game_dict['away_team_id'])
                    
                    # Find which pair this game belongs to
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
            from soccer_utils import translate_soccer_team_name
            
            db_team_names = [translate_soccer_team_name(team) for team in teams]
            
            conn = SoccerService._get_connection()
            if not conn:
                return {}
            
            placeholders = ','.join(['%s'] * len(db_team_names))
            query = f"""
                SELECT team_name, team_id 
                FROM teams 
                WHERE team_name IN ({placeholders}) AND UPPER(sport) = 'SOCCER'
            """
            
            with conn.cursor() as cursor:
                cursor.execute(query, db_team_names)
                results = cursor.fetchall()
            
            # Map back to original team names
            db_to_original = {translate_soccer_team_name(team): team for team in teams}
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
        """Analyze trends for a team's games. Soccer-specific implementation, now with spread analysis."""
        trends = []
        if len(games) < min_trend_length:
            return trends

        # Analyze different trend types for soccer
        win_streak = cls._analyze_win_loss_trend(games, team_name, 'win', min_trend_length)
        if win_streak:
            trends.append(win_streak)
        loss_streak = cls._analyze_win_loss_trend(games, team_name, 'loss', min_trend_length)
        if loss_streak:
            trends.append(loss_streak)
        draw_streak = cls._analyze_win_loss_trend(games, team_name, 'draw', min_trend_length)
        if draw_streak:
            trends.append(draw_streak)

        # Spread (cover/no cover) streaks
        cover_results = []
        no_cover_results = []
        for g in games:
            # Get team side and spread/score info
            team_side = g.get('team_side')
            home_goals = g.get('home_goals')
            away_goals = g.get('away_goals')
            home_spread = g.get('home_spread')
            away_spread = g.get('away_spread')
            if home_goals is None or away_goals is None:
                continue
            if team_side == 'home':
                team_score = home_goals
                opp_score = away_goals
                spread = home_spread
            else:
                team_score = away_goals
                opp_score = home_goals
                spread = away_spread
            if spread is not None:
                # Did the team cover?
                covered = (team_score + spread) > opp_score
                not_covered = (team_score + spread) < opp_score
                # Push (exact) breaks both streaks
                cover_results.append(covered)
                no_cover_results.append(not_covered)

        def calculate_current_streak(results: list) -> int:
            streak = 0
            for result in results:
                if result:
                    streak += 1
                else:
                    break
            return streak

        current_cover_streak = calculate_current_streak(cover_results)
        current_no_cover_streak = calculate_current_streak(no_cover_results)

        if current_cover_streak >= min_trend_length:
            trends.append({
                'type': 'cover_streak',
                'count': current_cover_streak,
                'description': f'Covered {current_cover_streak} straight spreads'
            })
        if current_no_cover_streak >= min_trend_length:
            trends.append({
                'type': 'no_cover_streak',
                'count': current_no_cover_streak,
                'description': f'Failed to cover {current_no_cover_streak} straight spreads'
            })

        # Over/Under trends for soccer
        over_streak = cls._analyze_over_under_trend(games, 'over', min_trend_length)
        if over_streak:
            over_streak['type'] = 'over_streak'
            over_streak['description'] = f'Total went OVER {over_streak["count"]} straight games'
            trends.append(over_streak)
        under_streak = cls._analyze_over_under_trend(games, 'under', min_trend_length)
        if under_streak:
            under_streak['type'] = 'under_streak'
            under_streak['description'] = f'Total went UNDER {under_streak["count"]} straight games'
            trends.append(under_streak)
        return trends
    
    @classmethod
    def _analyze_win_loss_trend(cls, games: List[Dict], team_name: str, trend_type: str, min_length: int) -> Optional[Dict]:
        """Analyze win/loss/draw trends for soccer."""
        streak_count = 0
        for idx, game in enumerate(games):
            home_goals = game.get('home_goals')
            away_goals = game.get('away_goals')
            team_side = game.get('team_side')
            if home_goals is None or away_goals is None:
                break
            is_win = False
            is_loss = False
            is_draw = home_goals == away_goals
            if not is_draw:
                if team_side == 'home':
                    is_win = home_goals > away_goals
                    is_loss = home_goals < away_goals
                else:
                    is_win = away_goals > home_goals
                    is_loss = away_goals < home_goals
            streak_continues = False
            if trend_type == 'win' and is_win:
                streak_continues = True
            elif trend_type == 'loss' and is_loss:
                streak_continues = True
            elif trend_type == 'draw' and is_draw:
                streak_continues = True
            
            if streak_continues:
                streak_count += 1
            else:
                break
        
        if streak_count >= min_length:
            trend_name = f"{streak_count} Game {trend_type.title()} Streak"
            return {
                'trend': trend_name,
                'count': streak_count,
                'type': trend_type,
                'description': f"{team_name} has {trend_name.lower()}"
            }
        return None
    
    @classmethod
    def _analyze_over_under_trend(cls, games: List[Dict], trend_type: str, min_length: int) -> Optional[Dict]:
        """Analyze over/under trends for soccer, with debug output for totals."""
        streak_count = 0
        for idx, game in enumerate(games):
            total_goals = game.get('total_goals')
            total_line = game.get('total_over_point', 2.5)  # Default to 2.5 for soccer
            if total_goals is None or total_line is None:
                break
            is_over = total_goals > total_line
            is_under = total_goals < total_line
            
            # Check if this game continues the streak
            streak_continues = False
            if trend_type == 'over' and is_over:
                streak_continues = True
            elif trend_type == 'under' and is_under:
                streak_continues = True
            if streak_continues:
                streak_count += 1
            else:
                break
        if streak_count >= min_length:
            trend_name = f"{streak_count} Game {trend_type.title()} Streak"
            return {
                'trend': trend_name,
                'count': streak_count,
                'type': f'total_{trend_type}',
                'description': f"Total has gone {trend_type} in {streak_count} straight games"
            }
        return None
