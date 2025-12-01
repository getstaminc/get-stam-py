"""NCAAB Historical Data Service."""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from psycopg2.extras import RealDictCursor
from .base_service import BaseHistoricalService


class NCAABService(BaseHistoricalService):
    """Service for handling NCAAB historical data operations"""
    
    @staticmethod
    def get_games(
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team: Optional[str] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get NCAAB historical games from database."""
        try:
            conn = NCAABService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            query = """
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_points, away_points, total_points, total, start_time, home_line, away_line,
                    home_money_line, away_money_line
                FROM ncaab_games
                WHERE 1=1
            """
            params = []
            if start_date:
                query += " AND game_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND game_date <= %s"
                params.append(end_date)
            if team:
                query += " AND (home_team_name ILIKE %s OR away_team_name ILIKE %s)"
                params.extend([f"%{team}%", f"%{team}%"])

            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)

            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                games_list = [dict(game) for game in games]
                processed_games = NCAABService._process_games_list(games_list)
                return processed_games, None
        except Exception as e:
            return None, f"Error fetching NCAAB games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_team_games_by_id(team_id: int, limit: int = 10) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific NCAAB team by ID."""
        try:
            conn = NCAABService._get_connection()
            if not conn:
                return None, "Database connection failed"

            query = """
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_points, away_points, total_points, total, start_time, home_line, away_line,
                    home_money_line, away_money_line, total,
                    CASE 
                        WHEN home_team_id = %s THEN 'home'
                        WHEN away_team_id = %s THEN 'away'
                    END as team_side
                FROM ncaab_games
                WHERE home_team_id = %s OR away_team_id = %s
                ORDER BY game_date DESC
                LIMIT %s
            """

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (team_id, team_id, team_id, team_id, limit))
                games = cursor.fetchall()
                games_list = [dict(game) for game in games]
                processed_games = NCAABService._process_games_list(games_list)
                return processed_games, None
        except Exception as e:
            return None, f"Error fetching team games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_team_games_by_name(team_name: str, limit: int = 10) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific NCAAB team by team name."""
        try:
            from shared_utils import convert_team_name
            db_team_name = convert_team_name(team_name)
            team_id = NCAABService._get_team_id_by_name(db_team_name, 'NCAAB')
            if not team_id:
                return None, f"Team '{team_name}' not found in database"
            return NCAABService.get_team_games_by_id(team_id, limit)
        except Exception as e:
            return None, f"Error fetching team games by name: {str(e)}"

    @staticmethod
    def get_head_to_head_games_by_id(team_id: int, opponent_id: int, limit: int = 5) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two NCAAB teams by ID."""
        try:
            conn = NCAABService._get_connection()
            if not conn:
                return None, "Database connection failed"

            query = """
                SELECT 
                    game_id, game_date, home_team_name, away_team_name, home_points, away_points,
                    total_points, total, start_time, home_line, away_line, home_money_line, away_money_line
                FROM ncaab_games
                WHERE (home_team_id = %s AND away_team_id = %s) 
                   OR (home_team_id = %s AND away_team_id = %s)
                ORDER BY game_date DESC
                LIMIT %s
            """

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (team_id, opponent_id, opponent_id, team_id, limit))
                games = cursor.fetchall()
                games_list = [dict(game) for game in games]
                processed_games = NCAABService._process_games_list(games_list)
                return processed_games, None
        except Exception as e:
            return None, f"Error fetching head-to-head games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_head_to_head_games_by_name(home_team: str, away_team: str, limit: int = 5) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two NCAAB teams by team names."""
        try:
            from shared_utils import convert_team_name
            db_home_team = convert_team_name(home_team)
            db_away_team = convert_team_name(away_team)
            home_team_id = NCAABService._get_team_id_by_name(db_home_team, 'NCAAB')
            away_team_id = NCAABService._get_team_id_by_name(db_away_team, 'NCAAB')
            if not home_team_id:
                return None, f"Home team '{home_team}' not found in database"
            if not away_team_id:
                return None, f"Away team '{away_team}' not found in database"
            return NCAABService.get_head_to_head_games_by_id(home_team_id, away_team_id, limit)
        except Exception as e:
            return None, f"Error fetching head-to-head games by name: {str(e)}"

    @staticmethod
    def _get_team_id_by_name(team_name: str, sport_key: str) -> Optional[int]:
        """Helper method to get team_id by team_name for NCAAB."""
        try:
            conn = NCAABService._get_connection()
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

    @staticmethod
    def _process_games_list(games_list: List[Dict]) -> List[Dict]:
        """Process a list of NCAAB games with standardized field names and datetime handling."""
        processed_games = []
        for game in games_list:
            start_time = game.get('start_time')
            if start_time:
                start_time = str(start_time)
            game_date = game.get('game_date')
            if game_date:
                game_date = str(game_date)
            processed_game = {
                'away_line': game.get('away_line'),
                'away_money_line': game.get('away_money_line'),
                'away_points': game.get('away_points'),
                'away_team_id': game.get('away_team_id'),
                'away_team_name': game.get('away_team_name'),
                'game_date': game_date,
                'game_id': game.get('game_id'),
                'home_line': game.get('home_line'),
                'home_money_line': game.get('home_money_line'),
                'home_points': game.get('home_points'),
                'home_team_id': game.get('home_team_id'),
                'home_team_name': game.get('home_team_name'),
                'start_time': start_time,
                'total': game.get('total'),
                'total_points': game.get('total_points')
            }
            processed_games.append(processed_game)
        return processed_games
