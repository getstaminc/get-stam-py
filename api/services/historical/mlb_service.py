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
    def get_team_games_by_id(team_id: int, limit: int = 50, start_date: Optional[str] = None, 
                            end_date: Optional[str] = None, playoffs: Optional[bool] = None, 
                            venue: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific MLB team by ID."""
        try:
            conn = MLBService._get_connection()
            if not conn:
                return None, "Database connection failed"

            # Base query
            if venue == 'home':
                query = """
                    SELECT 
                        game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                        home_line, away_line, home_inning_runs, away_inning_runs,
                        home_starting_pitcher, away_starting_pitcher, playoffs,
                        start_time, total, created_date, modified_date
                    FROM mlb_games
                    WHERE home_team_id = %s
                """
                params = [team_id]
            elif venue == 'away':
                query = """
                    SELECT 
                        game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                        home_line, away_line, home_inning_runs, away_inning_runs,
                        home_starting_pitcher, away_starting_pitcher, playoffs,
                        start_time, total, created_date, modified_date
                    FROM mlb_games
                    WHERE away_team_id = %s
                """
                params = [team_id]
            else:
                query = """
                    SELECT 
                        game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                        home_line, away_line, home_inning_runs, away_inning_runs,
                        home_starting_pitcher, away_starting_pitcher, playoffs,
                        start_time, total, created_date, modified_date
                    FROM mlb_games
                    WHERE (home_team_id = %s OR away_team_id = %s)
                """
                params = [team_id, team_id]

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
                
                games_list = []
                for game in games:
                    game_dict = dict(game)
                    
                    # Parse JSON fields
                    if game_dict.get('home_inning_runs'):
                        try:
                            game_dict['home_inning_runs'] = json.loads(game_dict['home_inning_runs'])
                        except (json.JSONDecodeError, TypeError):
                            game_dict['home_inning_runs'] = []
                    
                    if game_dict.get('away_inning_runs'):
                        try:
                            game_dict['away_inning_runs'] = json.loads(game_dict['away_inning_runs'])
                        except (json.JSONDecodeError, TypeError):
                            game_dict['away_inning_runs'] = []
                    
                    games_list.append(game_dict)
                
                processed_games = MLBService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching team games by ID: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_team_games_by_name(team_name: str, limit: int = 50, start_date: Optional[str] = None,
                              end_date: Optional[str] = None, playoffs: Optional[bool] = None, 
                              venue: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific MLB team by team name."""
        try:
            from shared_utils import convert_team_name
            db_team_name = convert_team_name(team_name)
            team_id = MLBService._get_team_id_by_name(db_team_name, 'MLB')
            if not team_id:
                # Fallback to original string-based approach
                return MLBService.get_team_games(team_name, limit, start_date, end_date, playoffs, venue)
            return MLBService.get_team_games_by_id(team_id, limit, start_date, end_date, playoffs, venue)
        except Exception as e:
            return None, f"Error fetching team games by name: {str(e)}"

    @staticmethod
    def get_head_to_head_games_by_id(team_id: int, opponent_id: int, limit: int = 10, 
                                    start_date: Optional[str] = None, end_date: Optional[str] = None,
                                    venue: Optional[str] = None, perspective_team_id: Optional[int] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two MLB teams by ID."""
        try:
            conn = MLBService._get_connection()
            if not conn:
                return None, "Database connection failed"

            # Build query based on venue filtering
            if venue and perspective_team_id:
                if venue == 'home':
                    # Only games where perspective_team was home against the opponent
                    query = """
                        SELECT 
                            game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                            home_line, away_line, home_inning_runs, away_inning_runs,
                            home_starting_pitcher, away_starting_pitcher, playoffs,
                            start_time, total, created_date, modified_date
                        FROM mlb_games
                        WHERE home_team_id = %s AND away_team_id = %s
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [perspective_team_id, opponent_id if opponent_id != perspective_team_id else team_id, limit]
                elif venue == 'away':
                    # Only games where perspective_team was away against the opponent
                    query = """
                        SELECT 
                            game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                            home_line, away_line, home_inning_runs, away_inning_runs,
                            home_starting_pitcher, away_starting_pitcher, playoffs,
                            start_time, total, created_date, modified_date
                        FROM mlb_games
                        WHERE away_team_id = %s AND home_team_id = %s
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [perspective_team_id, opponent_id if opponent_id != perspective_team_id else team_id, limit]
                else:
                    # Fallback to original logic
                    query = """
                        SELECT 
                            game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                            home_line, away_line, home_inning_runs, away_inning_runs,
                            home_starting_pitcher, away_starting_pitcher, playoffs,
                            start_time, total, created_date, modified_date
                        FROM mlb_games
                        WHERE (home_team_id = %s AND away_team_id = %s) 
                           OR (home_team_id = %s AND away_team_id = %s)
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [team_id, opponent_id, opponent_id, team_id, limit]
            else:
                # Original logic without venue filtering
                query = """
                    SELECT 
                        game_id, game_date, away_team_name, home_team_name, away_runs, home_runs,
                        home_line, away_line, home_inning_runs, away_inning_runs,
                        home_starting_pitcher, away_starting_pitcher, playoffs,
                        start_time, total, created_date, modified_date
                    FROM mlb_games
                    WHERE (home_team_id = %s AND away_team_id = %s) 
                       OR (home_team_id = %s AND away_team_id = %s)
                """
                params = [team_id, opponent_id, opponent_id, team_id]

            # Add date filters
            if start_date:
                query = query.replace("ORDER BY", "AND game_date >= %s ORDER BY")
                params.insert(-1 if 'LIMIT' in query else len(params), start_date)
            
            if end_date:
                query = query.replace("ORDER BY", "AND game_date <= %s ORDER BY")
                params.insert(-1 if 'LIMIT' in query else len(params), end_date)

            if 'LIMIT' not in query:
                query += " ORDER BY game_date DESC LIMIT %s"
                params.append(limit)

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                games_list = []
                for game in games:
                    game_dict = dict(game)
                    
                    # Parse JSON fields
                    if game_dict.get('home_inning_runs'):
                        try:
                            game_dict['home_inning_runs'] = json.loads(game_dict['home_inning_runs'])
                        except (json.JSONDecodeError, TypeError):
                            game_dict['home_inning_runs'] = []
                    
                    if game_dict.get('away_inning_runs'):
                        try:
                            game_dict['away_inning_runs'] = json.loads(game_dict['away_inning_runs'])
                        except (json.JSONDecodeError, TypeError):
                            game_dict['away_inning_runs'] = []
                    
                    games_list.append(game_dict)
                
                processed_games = MLBService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching head-to-head games by ID: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_head_to_head_games_by_name(team1: str, team2: str, limit: int = 10, 
                                      start_date: Optional[str] = None, end_date: Optional[str] = None,
                                      venue: Optional[str] = None, team_perspective: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two MLB teams by team names."""
        try:
            from shared_utils import convert_team_name
            db_team1 = convert_team_name(team1)
            db_team2 = convert_team_name(team2)
            team1_id = MLBService._get_team_id_by_name(db_team1, 'MLB')
            team2_id = MLBService._get_team_id_by_name(db_team2, 'MLB')
            
            if not team1_id or not team2_id:
                # Fallback to original string-based approach
                return MLBService.get_head_to_head_games(team1, team2, limit, start_date, end_date, venue, team_perspective)
            
            # Convert team_perspective to team_id for consistency
            perspective_team_id = None
            if team_perspective:
                db_perspective_team = convert_team_name(team_perspective)
                perspective_team_id = MLBService._get_team_id_by_name(db_perspective_team, 'MLB')
                
            return MLBService.get_head_to_head_games_by_id(team1_id, team2_id, limit, start_date, end_date, venue, perspective_team_id)
        except Exception as e:
            return None, f"Error fetching head-to-head games by name: {str(e)}"

    @staticmethod
    def _get_team_id_by_name(team_name: str, sport_key: str) -> Optional[int]:
        """Helper method to get team_id by team_name for MLB."""
        try:
            conn = MLBService._get_connection()
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
                'game_date': game_date,
                'away_team': game.get('away_team_name'),
                'home_team': game.get('home_team_name'),
                'away_team_name': game.get('away_team_name'),
                'home_team_name': game.get('home_team_name'),
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
