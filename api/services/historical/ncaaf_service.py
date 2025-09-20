"""NCAAF Historical Data Service."""

from typing import List, Dict, Optional, Tuple
from psycopg2.extras import RealDictCursor
from .base_service import BaseHistoricalService

class NCAAFService(BaseHistoricalService):
    """Service for handling NCAAF historical data operations"""
    
    @staticmethod
    def get_games(limit: int = 50, start_date: str = None, end_date: str = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get NCAAF historical games from database, optionally filtered by date."""
        try:
            conn = NCAAFService._get_connection()
            if not conn:
                return None, "Database connection failed"

            query = """
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_points, away_points, total_points, home_line, away_line,
                    home_money_line, away_money_line, start_time, total
                FROM ncaaf_games
            """
            params = []
            where_clauses = []
            if start_date:
                where_clauses.append("game_date >= %s")
                params.append(start_date)
            if end_date:
                where_clauses.append("game_date <= %s")
                params.append(end_date)
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, tuple(params))
                games = cursor.fetchall()

                games_list = [dict(game) for game in games]
                processed_games = NCAAFService._process_games_list(games_list)
                return processed_games, None

        except Exception as e:
            return None, f"Error fetching NCAAF games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_team_games_by_id(team_id: int, limit: int = 10) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific NCAAF team by ID."""
        try:
            conn = NCAAFService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            query = """
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_points, away_points, total_points, home_line, away_line,
                    home_money_line, away_money_line, start_time, total,
                    CASE 
                        WHEN home_team_id = %s THEN 'home'
                        WHEN away_team_id = %s THEN 'away'
                    END as team_side
                FROM ncaaf_games
                WHERE home_team_id = %s OR away_team_id = %s
                ORDER BY game_date DESC
                LIMIT %s
            """
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (team_id, team_id, team_id, team_id, limit))
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = NCAAFService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching team games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_team_games_by_name(team_name: str, limit: int = 10) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific NCAAF team by team name."""
        try:
            from shared_utils import convert_team_name
            
            # Convert odds API team name to database team name
            db_team_name = convert_team_name(team_name)
            
            # First get the team_id
            team_id = NCAAFService._get_team_id_by_name(db_team_name, 'NCAAF')
            if not team_id:
                return None, f"Team '{team_name}' not found in database"
            
            # Use existing method with team_id
            return NCAAFService.get_team_games_by_id(team_id, limit)
            
        except Exception as e:
            return None, f"Error fetching team games by name: {str(e)}"

    @staticmethod
    def get_head_to_head_games_by_id(team_id: int, opponent_id: int, limit: int = 5) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two NCAAF teams by ID."""
        try:
            conn = NCAAFService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            query = """
                SELECT 
                    game_id, game_date, home_team_name, away_team_name, home_points, away_points,
                    total_points, home_line, away_line, home_money_line, away_money_line,
                    start_time, total
                FROM ncaaf_games
                WHERE (home_team_id = %s AND away_team_id = %s) 
                   OR (home_team_id = %s AND away_team_id = %s)
                ORDER BY game_date DESC
                LIMIT %s
            """
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (team_id, opponent_id, opponent_id, team_id, limit))
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = NCAAFService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching head-to-head games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_head_to_head_games_by_name(home_team: str, away_team: str, limit: int = 5) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two NCAAF teams by team names."""
        try:
            from shared_utils import convert_team_name
            
            # Convert odds API team names to database team names
            db_home_team = convert_team_name(home_team)
            db_away_team = convert_team_name(away_team)
            
            # Get team IDs
            home_team_id = NCAAFService._get_team_id_by_name(db_home_team, 'NCAAF')
            away_team_id = NCAAFService._get_team_id_by_name(db_away_team, 'NCAAF')
            
            if not home_team_id:
                return None, f"Home team '{home_team}' not found in database"
            if not away_team_id:
                return None, f"Away team '{away_team}' not found in database"
            
            # Use existing method with team_ids
            return NCAAFService.get_head_to_head_games_by_id(home_team_id, away_team_id, limit)
            
        except Exception as e:
            return None, f"Error fetching head-to-head games by name: {str(e)}"

    @staticmethod
    def _get_team_id_by_name(team_name: str, sport_key: str) -> Optional[int]:
        """Helper method to get team_id by team_name for NCAAF."""
        try:
            conn = NCAAFService._get_connection()
            if not conn:
                return None
            
            query = """
                SELECT team_id 
                FROM teams 
                WHERE team_name = %s AND sport = %s
            """
            
            with conn.cursor() as cursor:
                cursor.execute(query, (team_name, sport_key.upper()))
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            print(f"Error getting team_id: {e}")
            return None
        finally:
            if conn:
                conn.close()
