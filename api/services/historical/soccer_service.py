"""Soccer Historical Data Service."""

from typing import List, Dict, Optional, Tuple
from psycopg2.extras import RealDictCursor
from .base_service import BaseHistoricalService

class SoccerService(BaseHistoricalService):
    """Service for handling Soccer historical data operations"""
    
    @staticmethod
    def get_games(
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team: Optional[str] = None,
        league: Optional[str] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get soccer historical games from database."""
        try:
            conn = SoccerService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            query = """
                SELECT 
                    game_id, odds_id, league, game_date, home_team_id, away_team_id,
                    home_team_name, away_team_name, home_goals, away_goals, total_goals,
                    home_money_line, draw_money_line, away_money_line,
                    home_spread, away_spread, total_over_point, total_over_price,
                    total_under_point, total_under_price,
                    home_first_half_goals, away_first_half_goals,
                    home_second_half_goals, away_second_half_goals,
                    home_overtime, away_overtime, start_time,
                    created_date, modified_date
                FROM soccer_games
                WHERE 1=1
            """
            
            params = []
            
            # Add filters
            if start_date:
                query += " AND game_date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND game_date <= %s"
                params.append(end_date)
            
            if team:
                query += " AND (home_team_name ILIKE %s OR away_team_name ILIKE %s)"
                params.extend([f"%{team}%", f"%{team}%"])
            
            if league:
                query += " AND league ILIKE %s"
                params.append(f"%{league}%")
            
            # Order by date (most recent first) and limit
            query += " ORDER BY game_date DESC, start_time DESC LIMIT %s"
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = SoccerService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching soccer games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_game_by_id(game_id: int) -> Tuple[Optional[Dict], Optional[str]]:
        """Get a specific soccer game by ID."""
        try:
            conn = SoccerService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        game_id, odds_id, league, game_date, home_team_id, away_team_id,
                        home_team_name, away_team_name, home_goals, away_goals, total_goals,
                        home_money_line, draw_money_line, away_money_line,
                        home_spread, away_spread, total_over_point, total_over_price,
                        total_under_point, total_under_price,
                        home_first_half_goals, away_first_half_goals,
                        home_second_half_goals, away_second_half_goals,
                        home_overtime, away_overtime, start_time,
                        created_date, modified_date
                    FROM soccer_games 
                    WHERE game_id = %s
                """, (game_id,))
                
                row = cursor.fetchone()
                
                if not row:
                    return None, "Game not found"
                
                game = dict(row)
                processed_game = SoccerService._process_games_list([game])[0]
                return processed_game, None
                
        except Exception as e:
            return None, f"Error fetching game: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_team_games(
        team_name: str,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        league: Optional[str] = None,
        venue: Optional[str] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get games for a specific soccer team."""
        try:
            conn = SoccerService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            # Base query with venue filtering
            if venue == 'home':
                query = """
                    SELECT 
                        game_id, odds_id, league, game_date, home_team_id, away_team_id,
                        home_team_name, away_team_name, home_goals, away_goals, total_goals,
                        home_money_line, draw_money_line, away_money_line,
                        home_spread, away_spread, total_over_point, total_over_price,
                        total_under_point, total_under_price,
                        home_first_half_goals, away_first_half_goals,
                        home_second_half_goals, away_second_half_goals,
                        home_overtime, away_overtime, start_time,
                        created_date, modified_date,
                        'home' as venue
                    FROM soccer_games
                    WHERE home_team_name ILIKE %s
                """
                params = [f"%{team_name}%"]
            elif venue == 'away':
                query = """
                    SELECT 
                        game_id, odds_id, league, game_date, home_team_id, away_team_id,
                        home_team_name, away_team_name, home_goals, away_goals, total_goals,
                        home_money_line, draw_money_line, away_money_line,
                        home_spread, away_spread, total_over_point, total_over_price,
                        total_under_point, total_under_price,
                        home_first_half_goals, away_first_half_goals,
                        home_second_half_goals, away_second_half_goals,
                        home_overtime, away_overtime, start_time,
                        created_date, modified_date,
                        'away' as venue
                    FROM soccer_games
                    WHERE away_team_name ILIKE %s
                """
                params = [f"%{team_name}%"]
            else:
                query = """
                    SELECT 
                        game_id, odds_id, league, game_date, home_team_id, away_team_id,
                        home_team_name, away_team_name, home_goals, away_goals, total_goals,
                        home_money_line, draw_money_line, away_money_line,
                        home_spread, away_spread, total_over_point, total_over_price,
                        total_under_point, total_under_price,
                        home_first_half_goals, away_first_half_goals,
                        home_second_half_goals, away_second_half_goals,
                        home_overtime, away_overtime, start_time,
                        created_date, modified_date,
                        CASE 
                            WHEN home_team_name ILIKE %s THEN 'home'
                            WHEN away_team_name ILIKE %s THEN 'away'
                        END as venue
                    FROM soccer_games
                    WHERE (home_team_name ILIKE %s OR away_team_name ILIKE %s)
                """
                params = [f"%{team_name}%", f"%{team_name}%", f"%{team_name}%", f"%{team_name}%"]
            
            if start_date:
                query += " AND game_date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND game_date <= %s"
                params.append(end_date)
            
            if league:
                query += " AND league ILIKE %s"
                params.append(f"%{league}%")
            
            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = SoccerService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching team games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_leagues() -> Tuple[Optional[List[str]], Optional[str]]:
        """Get available soccer leagues."""
        try:
            conn = SoccerService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT league FROM soccer_games ORDER BY league")
                leagues = [row[0] for row in cursor.fetchall()]
                return leagues, None
                
        except Exception as e:
            return None, f"Error fetching leagues: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_head_to_head_games(
        team1: str,
        team2: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        league: Optional[str] = None,
        venue: Optional[str] = None,
        team_perspective: Optional[str] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two soccer teams."""
        try:
            conn = SoccerService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            query = """
                SELECT 
                    game_id, odds_id, league, game_date, home_team_id, away_team_id,
                    home_team_name, away_team_name, home_goals, away_goals, total_goals,
                    home_money_line, draw_money_line, away_money_line,
                    home_spread, away_spread, total_over_point, total_over_price,
                    total_under_point, total_under_price,
                    home_first_half_goals, away_first_half_goals,
                    home_second_half_goals, away_second_half_goals,
                    home_overtime, away_overtime, start_time,
                    created_date, modified_date
                FROM soccer_games
                WHERE (
                    (home_team_name ILIKE %s AND away_team_name ILIKE %s) OR
                    (home_team_name ILIKE %s AND away_team_name ILIKE %s)
                )
            """
            
            params = [f"%{team1}%", f"%{team2}%", f"%{team2}%", f"%{team1}%"]
            
            # Add venue filtering if specified
            if venue and team_perspective:
                if venue == 'home':
                    # Only games where team_perspective was home
                    query += " AND home_team_name ILIKE %s"
                    params.append(f"%{team_perspective}%")
                elif venue == 'away':
                    # Only games where team_perspective was away
                    query += " AND away_team_name ILIKE %s"
                    params.append(f"%{team_perspective}%")
            
            if start_date:
                query += " AND game_date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND game_date <= %s"
                params.append(end_date)
            
            if league:
                query += " AND league ILIKE %s"
                params.append(f"%{league}%")
            
            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = SoccerService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching head-to-head games: {str(e)}"
        finally:
            if conn:
                conn.close()
