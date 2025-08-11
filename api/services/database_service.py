import os
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from datetime import date, time, datetime
import json
from dotenv import load_dotenv

load_dotenv()

class DatabaseService:
    """Service for handling database operations for historical games"""
    
    @staticmethod
    def _serialize_datetime_objects(obj):
        """Convert datetime objects to strings for JSON serialization"""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.strftime('%H:%M:%S')
        return obj
    
    @staticmethod
    def _process_games_list(games):
        """Process games list to handle JSON serialization"""
        processed_games = []
        for game in games:
            processed_game = {}
            for key, value in game.items():
                processed_game[key] = DatabaseService._serialize_datetime_objects(value)
            processed_games.append(processed_game)
        return processed_games
    
    @staticmethod
    def _get_connection():
        """Get database connection from DATABASE_URL"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL environment variable not set")
            
            # Parse the DATABASE_URL
            parsed = urlparse(database_url)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                database=parsed.path[1:],  # Remove leading slash
                user=parsed.username,
                password=parsed.password,
                port=parsed.port or 5432
            )
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    @staticmethod
    def get_historical_games(sport_key: str, limit: int = 50) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a sport"""
        table_name = f"{sport_key}_games"
        
        query = f"""
        SELECT 
            game_id,
            game_date,
            home_team_name,
            home_team_id,
            away_team_name,
            away_team_id,
            home_points,
            away_points,
            total_points,
            home_line,
            away_line,
            home_money_line,
            away_money_line,
            start_time
        FROM {table_name}
        ORDER BY game_date DESC
        LIMIT %s
        """
        
        conn = DatabaseService._get_connection()
        if not conn:
            return None, "Database connection failed"
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (limit,))
                games = cursor.fetchall()
                
                # Convert to list of dicts and handle datetime serialization
                games_list = [dict(game) for game in games]
                processed_games = DatabaseService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Database query error: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def get_team_games(sport_key: str, team_id: int, limit: int = 10) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific team"""
        table_name = f"{sport_key}_games"
        
        query = f"""
        SELECT 
            game_id,
            game_date,
            home_team_name,
            home_team_id,
            away_team_name,
            away_team_id,
            home_points,
            away_points,
            total_points,
            home_line,
            away_line,
            home_money_line,
            away_money_line,
            start_time,
            CASE 
                WHEN home_team_id = %s THEN 'home'
                WHEN away_team_id = %s THEN 'away'
            END as team_side
        FROM {table_name}
        WHERE home_team_id = %s OR away_team_id = %s
        ORDER BY game_date DESC
        LIMIT %s
        """
        
        conn = DatabaseService._get_connection()
        if not conn:
            return None, "Database connection failed"
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (team_id, team_id, team_id, team_id, limit))
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = DatabaseService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Database query error: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def get_head_to_head_games(sport_key: str, team_id: int, opponent_id: int, limit: int = 5) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two teams"""
        table_name = f"{sport_key}_games"
        
        query = f"""
        SELECT 
            game_id,
            game_date,
            home_team_name,
            away_team_name,
            home_points,
            away_points,
            total_points,
            home_line,
            away_line,
            home_money_line,
            away_money_line,
            start_time
        FROM {table_name}
        WHERE (home_team_id = %s AND away_team_id = %s) 
           OR (home_team_id = %s AND away_team_id = %s)
        ORDER BY game_date DESC
        LIMIT %s
        """
        
        conn = DatabaseService._get_connection()
        if not conn:
            return None, "Database connection failed"
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (team_id, opponent_id, opponent_id, team_id, limit))
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = DatabaseService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Database query error: {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def get_team_games_by_name(sport_key: str, team_name: str, limit: int = 10) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific team by team name"""
        from shared_utils import convert_team_name
        
        # Convert odds API team name to database team name
        db_team_name = convert_team_name(team_name)
        
        # First get the team_id
        team_id = DatabaseService._get_team_id_by_name(db_team_name, sport_key)
        if not team_id:
            return None, f"Team '{team_name}' not found in database"
        
        # Use existing method with team_id
        return DatabaseService.get_team_games(sport_key, team_id, limit)
    
    @staticmethod
    def get_head_to_head_games_by_name(sport_key: str, home_team: str, away_team: str, limit: int = 5) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two teams by team names"""
        from shared_utils import convert_team_name
        
        # Convert odds API team names to database team names
        db_home_team = convert_team_name(home_team)
        db_away_team = convert_team_name(away_team)
        
        # Get team IDs
        home_team_id = DatabaseService._get_team_id_by_name(db_home_team, sport_key)
        away_team_id = DatabaseService._get_team_id_by_name(db_away_team, sport_key)
        
        if not home_team_id:
            return None, f"Home team '{home_team}' not found in database"
        if not away_team_id:
            return None, f"Away team '{away_team}' not found in database"
        
        # Use existing method with team_ids
        return DatabaseService.get_head_to_head_games(sport_key, home_team_id, away_team_id, limit)
    
    @staticmethod
    def _get_team_id_by_name(team_name: str, sport_key: str) -> Optional[int]:
        """Helper method to get team_id by team_name"""
        query = """
        SELECT team_id 
        FROM teams 
        WHERE team_name = %s AND sport = %s
        """
        
        conn = DatabaseService._get_connection()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (team_name, sport_key.upper()))
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            print(f"Error getting team_id: {e}")
            return None
        finally:
            conn.close()
