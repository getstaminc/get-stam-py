
"""NHL Historical Data Service."""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, time
from psycopg2.extras import RealDictCursor
from .base_service import BaseHistoricalService

class NHLService(BaseHistoricalService):

    @staticmethod
    def get_team_games(team_name: str, limit: int = 50, start_date: Optional[str] = None, end_date: Optional[str] = None, playoffs: Optional[bool] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get games for a specific NHL team, with optional filters."""
        # Use get_team_games_by_name, and filter by date/playoffs if provided
        games, error = NHLService.get_team_games_by_name(team_name, limit)
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
    def get_head_to_head_games(team1: str, team2: str, limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two NHL teams, with optional filters."""
        games, error = NHLService.get_head_to_head_games_by_name(team1, team2, limit)
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
    def get_team_games_by_id(team_id: int, limit: int = 50) -> Tuple[Optional[List[Dict]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            query = "SELECT * FROM nhl_games WHERE home_team_id = %s OR away_team_id = %s ORDER BY game_date DESC LIMIT %s"
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (team_id, team_id, limit))
                games = cursor.fetchall()
            return games, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_team_games_by_name(team_name: str, limit: int = 50) -> Tuple[Optional[List[Dict]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            query = "SELECT * FROM nhl_games WHERE home_team_name ILIKE %s OR away_team_name ILIKE %s ORDER BY game_date DESC LIMIT %s"
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (f"%{team_name}%", f"%{team_name}%", limit))
                games = cursor.fetchall()
            # Ensure game_date is always a string (should be YYYY-MM-DD from DB)
            for g in games:
                if 'game_date' in g and g['game_date']:
                    g['game_date'] = str(g['game_date'])
            return games, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_head_to_head_games_by_id(team_id: int, opponent_id: int, limit: int = 10) -> Tuple[Optional[List[Dict]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            query = "SELECT * FROM nhl_games WHERE (home_team_id = %s AND away_team_id = %s) OR (home_team_id = %s AND away_team_id = %s) ORDER BY game_date DESC LIMIT %s"
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (team_id, opponent_id, opponent_id, team_id, limit))
                games = cursor.fetchall()
            return games, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_head_to_head_games_by_name(home_team: str, away_team: str, limit: int = 10) -> Tuple[Optional[List[Dict]], Optional[str]]:
        try:
            conn = NHLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            query = "SELECT * FROM nhl_games WHERE (home_team_name ILIKE %s AND away_team_name ILIKE %s) OR (home_team_name ILIKE %s AND away_team_name ILIKE %s) ORDER BY game_date DESC LIMIT %s"
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (f"%{home_team}%", f"%{away_team}%", f"%{away_team}%", f"%{home_team}%", limit))
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
