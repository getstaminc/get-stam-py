"""NFL Historical Data Service."""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, time
from psycopg2.extras import RealDictCursor
from .base_service import BaseHistoricalService

class NFLService(BaseHistoricalService):
    """Service for handling NFL historical data operations"""
    
    @staticmethod
    def get_games(
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team: Optional[str] = None,
        playoffs: Optional[bool] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get NFL historical games from database."""
        try:
            conn = NFLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            # Build the query
            query = """
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_points, away_points, total_points, home_line, away_line,
                    home_money_line, away_money_line, start_time, total
                FROM nfl_games
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
                # NFL might have a playoffs column or we can infer from date/season
                # For now, let's skip this filter if the column doesn't exist
                pass
            
            # Add ordering and limit
            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = NFLService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching NFL games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_team_games_by_id(team_id: int, limit: int = 10, venue: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific NFL team by ID."""
        try:
            conn = NFLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            # Base query
            query = """
                SELECT 
                    game_id, game_date, home_team_name, home_team_id, away_team_name, away_team_id,
                    home_points, away_points, total_points, home_line, away_line,
                    home_money_line, away_money_line, start_time, total,
                    CASE 
                        WHEN home_team_id = %s THEN 'home'
                        WHEN away_team_id = %s THEN 'away'
                    END as team_side
                FROM nfl_games
                WHERE 
            """
            
            params = [team_id, team_id]
            
            # Add venue filtering
            if venue == 'home':
                query += "home_team_id = %s"
                params.append(team_id)
            elif venue == 'away':
                query += "away_team_id = %s"
                params.append(team_id)
            else:
                # Default: both home and away games
                query += "(home_team_id = %s OR away_team_id = %s)"
                params.extend([team_id, team_id])
                
            query += " ORDER BY game_date DESC LIMIT %s"
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = NFLService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching team games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_team_games_by_name(team_name: str, limit: int = 10, venue: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get historical games for a specific NFL team by team name."""
        try:
            from shared_utils import convert_team_name
            
            # Convert odds API team name to database team name
            db_team_name = convert_team_name(team_name)
            
            # First get the team_id
            team_id = NFLService._get_team_id_by_name(db_team_name, 'NFL')
            if not team_id:
                return None, f"Team '{team_name}' not found in database"
            
            # Use existing method with team_id
            return NFLService.get_team_games_by_id(team_id, limit, venue)
            
        except Exception as e:
            return None, f"Error fetching team games by name: {str(e)}"

    @staticmethod
    def get_head_to_head_games_by_id(team_id: int, opponent_id: int, limit: int = 5, venue: Optional[str] = None, perspective_team_id: Optional[int] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two NFL teams by ID."""
        try:
            conn = NFLService._get_connection()
            if not conn:
                return None, "Database connection failed"
            
            # Build query based on venue filtering
            if venue and perspective_team_id:
                if venue == 'home':
                    # Only games where perspective_team was home against the opponent
                    query = """
                        SELECT 
                            game_id, game_date, home_team_name, away_team_name, home_points, away_points,
                            total_points, home_line, away_line, home_money_line, away_money_line,
                            start_time, total, home_team_id, away_team_id
                        FROM nfl_games
                        WHERE home_team_id = %s AND away_team_id = %s
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [perspective_team_id, opponent_id if opponent_id != perspective_team_id else team_id, limit]
                elif venue == 'away':
                    # Only games where perspective_team was away against the opponent
                    query = """
                        SELECT 
                            game_id, game_date, home_team_name, away_team_name, home_points, away_points,
                            total_points, home_line, away_line, home_money_line, away_money_line,
                            start_time, total, home_team_id, away_team_id
                        FROM nfl_games
                        WHERE away_team_id = %s AND home_team_id = %s
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [perspective_team_id, opponent_id if opponent_id != perspective_team_id else team_id, limit]
                else:
                    # Fallback to original logic
                    query = """
                        SELECT 
                            game_id, game_date, home_team_name, away_team_name, home_points, away_points,
                            total_points, home_line, away_line, home_money_line, away_money_line,
                            start_time, total, home_team_id, away_team_id
                        FROM nfl_games
                        WHERE (home_team_id = %s AND away_team_id = %s) 
                           OR (home_team_id = %s AND away_team_id = %s)
                        ORDER BY game_date DESC LIMIT %s
                    """
                    params = [team_id, opponent_id, opponent_id, team_id, limit]
            else:
                # Original logic without venue filtering
                query = """
                    SELECT 
                        game_id, game_date, home_team_name, away_team_name, home_points, away_points,
                        total_points, home_line, away_line, home_money_line, away_money_line,
                        start_time, total, home_team_id, away_team_id
                    FROM nfl_games
                    WHERE (home_team_id = %s AND away_team_id = %s) 
                       OR (home_team_id = %s AND away_team_id = %s)
                    ORDER BY game_date DESC LIMIT %s
                """
                params = [team_id, opponent_id, opponent_id, team_id, limit]
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                games = cursor.fetchall()
                
                games_list = [dict(game) for game in games]
                processed_games = NFLService._process_games_list(games_list)
                return processed_games, None
                
        except Exception as e:
            return None, f"Error fetching head-to-head games: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_head_to_head_games_by_name(home_team: str, away_team: str, limit: int = 5, venue: Optional[str] = None, team_perspective: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get head-to-head games between two NFL teams by team names."""
        try:
            from shared_utils import convert_team_name
            
            # Convert odds API team names to database team names
            db_home_team = convert_team_name(home_team)
            db_away_team = convert_team_name(away_team)
            
            # Get team IDs
            home_team_id = NFLService._get_team_id_by_name(db_home_team, 'NFL')
            away_team_id = NFLService._get_team_id_by_name(db_away_team, 'NFL')
            
            if not home_team_id:
                return None, f"Home team '{home_team}' not found in database"
            if not away_team_id:
                return None, f"Away team '{away_team}' not found in database"
            
            # Convert team_perspective to team_id for consistency
            perspective_team_id = None
            if team_perspective:
                db_perspective_team = convert_team_name(team_perspective)
                perspective_team_id = NFLService._get_team_id_by_name(db_perspective_team, 'NFL')
            
            # Use existing method with team_ids
            return NFLService.get_head_to_head_games_by_id(home_team_id, away_team_id, limit, venue, perspective_team_id)
            
        except Exception as e:
            return None, f"Error fetching head-to-head games by name: {str(e)}"

    @staticmethod
    def _get_team_id_by_name(team_name: str, sport_key: str) -> Optional[int]:
        """Helper method to get team_id by team_name for NFL."""
        try:
            conn = NFLService._get_connection()
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
        """Process a list of NFL games with standardized field names and datetime handling."""
        processed_games = []
        
        for game in games_list:
            # Handle datetime/time objects for JSON serialization
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
