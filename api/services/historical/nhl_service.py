
"""NHL Historical Data Service."""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, time
from psycopg2.extras import RealDictCursor
from .base_service import BaseHistoricalService

class NHLService(BaseHistoricalService):

    @staticmethod
    def get_team_games(team_name: str, limit: int = 50, start_date: Optional[str] = None, end_date: Optional[str] = None, playoffs: Optional[bool] = None, venue: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get games for a specific NHL team, with optional filters."""
        # Use get_team_games_by_name, and filter by date/playoffs if provided
        games, error = NHLService.get_team_games_by_name(team_name, limit, venue)
        if error or not games:
            return games, error
        # Filter in Python if needed (since get_team_games_by_name doesn't filter by date/playoffs)
        if start_date:
            games = [g for g in games if str(g.get('game_date', '')) >= start_date]
        if end_date:
            games = [g for g in games if str(g.get('game_date', '')) <= end_date]
        if playoffs is not None:
            games = [g for g in games if g.get('playoffs') == playoffs]
        return games, None

    @staticmethod
    def get_head_to_head_games(team1: str, team2: str, limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None, venue: Optional[str] = None, team_perspective: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two NHL teams, with optional filters."""
        games, error = NHLService.get_head_to_head_games_by_name(team1, team2, limit, venue, team_perspective)
        if error or not games:
            return games, error
        # Filter in Python if needed
        if start_date:
            games = [g for g in games if str(g.get('game_date', '')) >= start_date]
        if end_date:
            games = [g for g in games if str(g.get('game_date', '')) <= end_date]
        return games, None
    """Service for handling NHL historical data operations"""

    @staticmethod
    def get_games(
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team: Optional[str] = None,
        playoffs: Optional[bool] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get NHL historical games from database, always returning game_date as YYYY-MM-DD."""
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"

            query = """
                SELECT * FROM nhl_games WHERE 1=1
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
            if playoffs is not None:
                query += " AND playoffs = %s"
                params.append(playoffs)
            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
            # Ensure game_date is always a string (should be YYYY-MM-DD from DB)
            for g in games:
                if 'game_date' in g and g['game_date']:
                    g['game_date'] = str(g['game_date'])
            return games, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_game_by_id(game_id: int) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            query = "SELECT * FROM nhl_games WHERE game_id = %s"
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (game_id,))
                game = cursor.fetchone()
            if not game:
                return None, "Game not found"
            return game, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_team_games_by_id(team_id: int, limit: int = 50, venue: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            # Base query
            if venue == 'home':
                query = "SELECT * FROM nhl_games WHERE home_team_id = %s ORDER BY game_date DESC LIMIT %s"
                params = [team_id, limit]
            elif venue == 'away':
                query = "SELECT * FROM nhl_games WHERE away_team_id = %s ORDER BY game_date DESC LIMIT %s"
                params = [team_id, limit]
            else:
                # Default: both home and away games
                query = "SELECT * FROM nhl_games WHERE home_team_id = %s OR away_team_id = %s ORDER BY game_date DESC LIMIT %s"
                params = [team_id, team_id, limit]
                
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
            return games, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_team_games_by_name(team_name: str, limit: int = 50, venue: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            if venue == 'home':
                query = "SELECT * FROM nhl_games WHERE home_team_name ILIKE %s ORDER BY game_date DESC LIMIT %s"
                params = (f"%{team_name}%", limit)
            elif venue == 'away':
                query = "SELECT * FROM nhl_games WHERE away_team_name ILIKE %s ORDER BY game_date DESC LIMIT %s"
                params = (f"%{team_name}%", limit)
            else:
                query = "SELECT * FROM nhl_games WHERE home_team_name ILIKE %s OR away_team_name ILIKE %s ORDER BY game_date DESC LIMIT %s"
                params = (f"%{team_name}%", f"%{team_name}%", limit)
                
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
            # Ensure game_date is always a string (should be YYYY-MM-DD from DB)
            for g in games:
                if 'game_date' in g and g['game_date']:
                    g['game_date'] = str(g['game_date'])
            return games, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_head_to_head_games_by_id(team_id: int, opponent_id: int, limit: int = 10, venue: Optional[str] = None, perspective_team_id: Optional[int] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            # Build query based on venue filtering
            if venue and perspective_team_id:
                if venue == 'home':
                    # Only games where perspective_team was home against the opponent
                    query = """
                        SELECT * FROM nhl_games 
                        WHERE home_team_id = %s AND away_team_id = %s 
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [perspective_team_id, opponent_id if opponent_id != perspective_team_id else team_id, limit]
                elif venue == 'away':
                    # Only games where perspective_team was away against the opponent
                    query = """
                        SELECT * FROM nhl_games 
                        WHERE away_team_id = %s AND home_team_id = %s 
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [perspective_team_id, opponent_id if opponent_id != perspective_team_id else team_id, limit]
                else:
                    # Fallback to original logic
                    query = """
                        SELECT * FROM nhl_games 
                        WHERE (home_team_id = %s AND away_team_id = %s) 
                           OR (home_team_id = %s AND away_team_id = %s) 
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [team_id, opponent_id, opponent_id, team_id, limit]
            else:
                # Original logic without venue filtering
                query = """
                    SELECT * FROM nhl_games 
                    WHERE (home_team_id = %s AND away_team_id = %s) 
                       OR (home_team_id = %s AND away_team_id = %s) 
                    ORDER BY game_date DESC LIMIT %s
                """
                params = [team_id, opponent_id, opponent_id, team_id, limit]
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
            return games, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_head_to_head_games_by_name(home_team: str, away_team: str, limit: int = 10, venue: Optional[str] = None, team_perspective: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            # Convert team names using shared_utils
            from shared_utils import convert_team_name
            db_home_team = convert_team_name(home_team)
            db_away_team = convert_team_name(away_team)
            
            # Convert team_perspective as well
            db_team_perspective = None
            if team_perspective:
                db_team_perspective = convert_team_name(team_perspective)
            
            # Build query based on venue filtering
            if venue and db_team_perspective:
                if venue == 'home':
                    # Only games where team_perspective was home against the other team
                    other_team = db_away_team if db_team_perspective.lower() in db_home_team.lower() else db_home_team
                    query = """
                        SELECT * FROM nhl_games 
                        WHERE home_team_name ILIKE %s AND away_team_name ILIKE %s
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [f"%{db_team_perspective}%", f"%{other_team}%", limit]
                elif venue == 'away':
                    # Only games where team_perspective was away against the other team
                    other_team = db_home_team if db_team_perspective.lower() in db_away_team.lower() else db_away_team
                    query = """
                        SELECT * FROM nhl_games 
                        WHERE away_team_name ILIKE %s AND home_team_name ILIKE %s
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [f"%{db_team_perspective}%", f"%{other_team}%", limit]
                else:
                    # Fallback to original logic
                    query = """
                        SELECT * FROM nhl_games 
                        WHERE (home_team_name ILIKE %s AND away_team_name ILIKE %s) 
                           OR (home_team_name ILIKE %s AND away_team_name ILIKE %s)
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [f"%{db_home_team}%", f"%{db_away_team}%", f"%{db_away_team}%", f"%{db_home_team}%", limit]
            else:
                # Original logic without venue filtering
                query = """
                    SELECT * FROM nhl_games 
                    WHERE (home_team_name ILIKE %s AND away_team_name ILIKE %s) 
                       OR (home_team_name ILIKE %s AND away_team_name ILIKE %s)
                    ORDER BY game_date DESC LIMIT %s
                """
                params = [f"%{db_home_team}%", f"%{db_away_team}%", f"%{db_away_team}%", f"%{db_home_team}%", limit]
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
            # Ensure game_date is always a string (should be YYYY-MM-DD from DB)
            for g in games:
                if 'game_date' in g and g['game_date']:
                    g['game_date'] = str(g['game_date'])
            return games, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_goalies() -> Tuple[Optional[List[str]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            query = "SELECT DISTINCT home_starting_goalie FROM nhl_games WHERE home_starting_goalie IS NOT NULL UNION SELECT DISTINCT away_starting_goalie FROM nhl_games WHERE away_starting_goalie IS NOT NULL"
            with conn.cursor() as cursor:
                cursor.execute(query)
                goalies = [row[0] for row in cursor.fetchall()]
            return goalies, None
        except Exception as e:
            return None, str(e)
