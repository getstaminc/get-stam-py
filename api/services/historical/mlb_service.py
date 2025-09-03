"""MLB Historical Data Service"""

from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime, date, time
from psycopg2.extras import RealDictCursor
from .base_service import BaseHistoricalService

class MLBService(BaseHistoricalService):
    """Service for handling MLB historical data operations"""
    
    @staticmethod
    def get_games(
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team: Optional[str] = None,
        playoffs: Optional[bool] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get MLB historical games from database."""
        try:
            conn = MLBService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            # Build the query
            query = """
                SELECT 
                    game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                    home_line, away_line, home_inning_runs, away_inning_runs,
                    home_starting_pitcher, away_starting_pitcher, playoffs,
                    start_time, total, created_date, modified_date
                FROM mlb_games
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
            
            if playoffs is not None:
                query += " AND playoffs = %s"
                params.append(playoffs)
            
            # Add ordering and limit
            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                # Convert to list of dicts and handle JSON parsing
                games_list = []
                for game in games:
                    game_dict = dict(game)
                    
                    # Parse home_inning_runs JSON if present
                    if game_dict.get('home_inning_runs'):
                        try:
                            game_dict['home_inning_runs'] = json.loads(game_dict['home_inning_runs'])
                        except (json.JSONDecodeError, TypeError):
                            game_dict['home_inning_runs'] = []
                    
                    # Parse away_inning_runs JSON if present
                    if game_dict.get('away_inning_runs'):
                        try:
                            game_dict['away_inning_runs'] = json.loads(game_dict['away_inning_runs'])
                        except (json.JSONDecodeError, TypeError):
                            game_dict['away_inning_runs'] = []
                    
                    games_list.append(game_dict)
                
                processed_games = MLBService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching MLB games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_game_by_id(game_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Get a specific MLB game by ID."""
        try:
            conn = MLBService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                        home_line, away_line, home_inning_runs, away_inning_runs,
                        home_starting_pitcher, away_starting_pitcher, playoffs,
                        start_time, total, created_date, modified_date
                    FROM mlb_games
                    WHERE game_id = %s
                """, (game_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None, "Game not found"
                
                game = dict(row)
                
                # Parse home_inning_runs JSON if present
                if game.get('home_inning_runs'):
                    try:
                        game['home_inning_runs'] = json.loads(game['home_inning_runs'])
                    except (json.JSONDecodeError, TypeError):
                        game['home_inning_runs'] = []
                
                processed_game = MLBService._process_games_list([game])[0]
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
        playoffs: Optional[bool] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get games for a specific MLB team."""
        try:
            conn = MLBService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            query = """
                SELECT 
                    game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                    home_line, away_line, home_inning_runs, away_inning_runs,
                    home_starting_pitcher, away_starting_pitcher, playoffs,
                    start_time, total, created_date, modified_date
                FROM mlb_games
                WHERE (home_team_name ILIKE %s OR away_team_name ILIKE %s)
            """
            
            params = [f"%{team_name}%", f"%{team_name}%"]
            
            if start_date:
                query += " AND game_date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND game_date <= %s"
                params.append(end_date)
                
            if playoffs is not None:
                query += " AND playoffs = %s"
                params.append(playoffs)
            
            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                # Convert to list of dicts and handle JSON parsing
                games_list = []
                for game in games:
                    game_dict = dict(game)
                    
                    # Parse home_inning_runs JSON if present
                    if game_dict.get('home_inning_runs'):
                        try:
                            game_dict['home_inning_runs'] = json.loads(game_dict['home_inning_runs'])
                        except (json.JSONDecodeError, TypeError):
                            game_dict['home_inning_runs'] = []
                    
                    games_list.append(game_dict)
                
                processed_games = MLBService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching team games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_teams() -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get unique MLB teams from historical games."""
        try:
            conn = MLBService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT DISTINCT team_name, COUNT(*) as games_played
                    FROM (
                        SELECT home_team_name as team_name FROM mlb_games WHERE home_team_name IS NOT NULL
                        UNION ALL
                        SELECT away_team_name as team_name FROM mlb_games WHERE away_team_name IS NOT NULL
                    ) as all_teams
                    GROUP BY team_name
                    ORDER BY games_played DESC, team_name
                """)
                
                teams = [dict(row) for row in cursor.fetchall()]
                return teams, None
                
        except Exception as e:
            return None, f"Error fetching teams: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_pitchers() -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get unique MLB pitchers from historical games."""
        try:
            conn = MLBService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT DISTINCT pitcher_name, COUNT(*) as games_pitched
                    FROM (
                        SELECT home_starting_pitcher as pitcher_name FROM mlb_games WHERE home_starting_pitcher IS NOT NULL
                        UNION ALL
                        SELECT away_starting_pitcher as pitcher_name FROM mlb_games WHERE away_starting_pitcher IS NOT NULL
                    ) as all_pitchers
                    GROUP BY pitcher_name
                    ORDER BY games_pitched DESC, pitcher_name
                """)
                
                pitchers = [dict(row) for row in cursor.fetchall()]
                return pitchers, None
                
        except Exception as e:
            return None, f"Error fetching pitchers: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_head_to_head_games(
        team1: str,
        team2: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two MLB teams."""
        try:
            conn = MLBService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            query = """
                SELECT 
                    game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                    home_line, away_line, home_inning_runs, away_inning_runs,
                    home_starting_pitcher, away_starting_pitcher, playoffs,
                    start_time, total, created_date, modified_date
                FROM mlb_games
                WHERE (
                    (home_team_name ILIKE %s AND away_team_name ILIKE %s) OR
                    (home_team_name ILIKE %s AND away_team_name ILIKE %s)
                )
            """
            
            params = [f"%{team1}%", f"%{team2}%", f"%{team2}%", f"%{team1}%"]
            
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
                games = cursor.fetchall()
                
                # Convert to list of dicts and handle JSON parsing
                games_list = []
                for game in games:
                    game_dict = dict(game)
                    
                    # Parse home_inning_runs JSON if present
                    if game_dict.get('home_inning_runs'):
                        try:
                            game_dict['home_inning_runs'] = json.loads(game_dict['home_inning_runs'])
                        except (json.JSONDecodeError, TypeError):
                            game_dict['home_inning_runs'] = []
                    
                    games_list.append(game_dict)
                
                processed_games = MLBService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching head-to-head games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def _process_games_list(games_list: List[Dict]) -> List[Dict]:
        """Process a list of MLB games with standardized field names."""
        processed_games = []
        
        for game in games_list:
            # Handle datetime/time objects for JSON serialization
            start_time = game.get('start_time')
            if start_time:
                start_time = str(start_time)
            
            created_date = game.get('created_date')
            if created_date:
                created_date = str(created_date)
                
            modified_date = game.get('modified_date')
            if modified_date:
                modified_date = str(modified_date)
            
            game_date = game.get('game_date')
            if game_date:
                game_date = str(game_date)
            
            processed_game = {
                'game_id': game.get('game_id'),
                'date': game_date,
                'away_team': game.get('away_team_name'),
                'home_team': game.get('home_team_name'),
                'away_runs': game.get('away_runs'),
                'home_runs': game.get('home_runs'),
                'home_line': game.get('home_line'),
                'away_line': game.get('away_line'),
                'home_starting_pitcher': game.get('home_starting_pitcher'),
                'away_starting_pitcher': game.get('away_starting_pitcher'),
                'playoffs': game.get('playoffs'),
                'home_innings_runs': game.get('home_inning_runs', []),
                'away_innings_runs': game.get('away_inning_runs', []),
                'start_time': start_time,
                'total': game.get('total'),
                'created_date': created_date,
                'modified_date': modified_date
            }
            processed_games.append(processed_game)
        
        return processed_games
