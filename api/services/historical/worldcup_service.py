"""World Cup Historical Data Service (international_soccer_games table)."""

from typing import List, Dict, Optional, Tuple
from psycopg2.extras import RealDictCursor
from .base_service import BaseHistoricalService

# Columns present in international_soccer_games
_COLS = """
    game_id, odds_id, league, game_date, home_team_id, away_team_id,
    home_team_name, away_team_name, home_goals, away_goals, total_goals,
    home_money_line, draw_money_line, away_money_line,
    home_spread, away_spread, total_over_point, total_over_price,
    total_under_point, total_under_price,
    home_first_half_goals, away_first_half_goals,
    home_second_half_goals, away_second_half_goals,
    home_overtime, away_overtime, start_time,
    created_date, modified_date
"""


class WorldcupService(BaseHistoricalService):
    """Service for World Cup historical data from international_soccer_games."""

    @staticmethod
    def get_team_games(
        team_name: str,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        venue: Optional[str] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get games for a specific World Cup team."""
        try:
            conn = WorldcupService._get_connection()
            if not conn:
                return None, "Database connection failed"

            if venue == 'home':
                query = f"""
                    SELECT {_COLS}, 'home' as venue
                    FROM international_soccer_games
                    WHERE home_team_name ILIKE %s
                """
                params = [f"%{team_name}%"]
            elif venue == 'away':
                query = f"""
                    SELECT {_COLS}, 'away' as venue
                    FROM international_soccer_games
                    WHERE away_team_name ILIKE %s
                """
                params = [f"%{team_name}%"]
            else:
                query = f"""
                    SELECT {_COLS},
                        CASE
                            WHEN home_team_name ILIKE %s THEN 'home'
                            WHEN away_team_name ILIKE %s THEN 'away'
                        END as venue
                    FROM international_soccer_games
                    WHERE (home_team_name ILIKE %s OR away_team_name ILIKE %s)
                """
                params = [f"%{team_name}%", f"%{team_name}%", f"%{team_name}%", f"%{team_name}%"]

            if start_date:
                query += " AND game_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND game_date <= %s"
                params.append(end_date)

            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = [dict(g) for g in cursor.fetchall()]
                return WorldcupService._process_games_list(games), None

        except Exception as e:
            return None, f"Error fetching team games: {str(e)}"
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
        venue: Optional[str] = None,
        team_perspective: Optional[str] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two World Cup teams."""
        try:
            conn = WorldcupService._get_connection()
            if not conn:
                return None, "Database connection failed"

            query = f"""
                SELECT {_COLS}
                FROM international_soccer_games
                WHERE (
                    (home_team_name ILIKE %s AND away_team_name ILIKE %s) OR
                    (home_team_name ILIKE %s AND away_team_name ILIKE %s)
                )
            """
            params = [f"%{team1}%", f"%{team2}%", f"%{team2}%", f"%{team1}%"]

            if venue and team_perspective:
                if venue == 'home':
                    query += " AND home_team_name ILIKE %s"
                    params.append(f"%{team_perspective}%")
                elif venue == 'away':
                    query += " AND away_team_name ILIKE %s"
                    params.append(f"%{team_perspective}%")

            if start_date:
                query += " AND game_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND game_date <= %s"
                params.append(end_date)

            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = [dict(g) for g in cursor.fetchall()]
                return WorldcupService._process_games_list(games), None

        except Exception as e:
            return None, f"Error fetching head-to-head games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_games(
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team: Optional[str] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get World Cup games, optionally filtered by date/team."""
        try:
            conn = WorldcupService._get_connection()
            if not conn:
                return None, "Database connection failed"

            query = f"SELECT {_COLS} FROM international_soccer_games WHERE 1=1"
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

            query += " ORDER BY game_date DESC, start_time DESC LIMIT %s"
            params.append(limit)

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = [dict(g) for g in cursor.fetchall()]
                return WorldcupService._process_games_list(games), None

        except Exception as e:
            return None, f"Error fetching games: {str(e)}"
        finally:
            if conn:
                conn.close()
