"""Base historical data service with common database functionality."""

import os
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from datetime import date, time, datetime
import json
from dotenv import load_dotenv

load_dotenv()

class BaseHistoricalService:
    """Base service for handling historical sports data operations"""
    
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
                processed_game[key] = BaseHistoricalService._serialize_datetime_objects(value)
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
