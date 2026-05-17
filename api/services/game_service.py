"""
Game service for handling game-related business logic
"""
from datetime import datetime, date
import os
import pytz
from dateutil import parser
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

from ..external_requests.odds_api import get_odds_data
from ..utils.date_utils import (
    convert_to_eastern, 
    get_next_game_date_within_7_days, 
    filter_games_by_date,
    format_commence_time,
    is_today
)
from ..utils.odds_formatter import extract_scores, process_odds_data

eastern_tz = pytz.timezone('US/Eastern')

class GameService:
    @staticmethod
    def get_games_for_date(sport_key, current_date=None):
        """Get games for a specific date or all games"""
        selected_date_start = None
        if current_date:
            selected_date_start = eastern_tz.localize(
                datetime.strptime(current_date, '%Y-%m-%d')
            )

        scores, odds = get_odds_data(sport_key, selected_date_start)
        if scores is None or odds is None:
            return None, 'Error fetching odds data'

        filtered_scores = filter_games_by_date(scores, selected_date_start)

        next_game_date = None
        if selected_date_start and not filtered_scores:
            next_game_date = get_next_game_date_within_7_days(scores, selected_date_start)

        formatted_games = [
            GameService._format_game_data(match, odds, selected_date_start)
            for match in filtered_scores
        ]

        return {
            'games': formatted_games,
            'nextGameDate': next_game_date
        }, None

    @staticmethod
    def get_single_game(sport_key, game_id):
        """Get a single game by game_id"""
        scores, odds = get_odds_data(sport_key, None)
        if scores is None or odds is None:
            return None, 'Error fetching odds data'

        game = next((g for g in scores if g['id'] == game_id), None)
        if not game:
            return None, 'Game not found'

        formatted_game = GameService._format_game_data(game, odds)
        return {'game': formatted_game}, None

    @staticmethod
    def _format_game_data(match, odds, selected_date_start=None):
        """Format a single game's data"""
        home_team = match.get('home_team', 'N/A')
        away_team = match.get('away_team', 'N/A')

        # Extract scores
        home_score, away_score = extract_scores(match)

        # Process odds
        home_odds, away_odds, totals, draw_odds = process_odds_data(match, odds, home_team, away_team)
        # Format commence time
        commence_time_formatted = format_commence_time(match.get('commence_time'))

        # Add draw odds for soccer_epl only if present
        game_obj = {
            "game_id": match['id'],
            "commence_time": commence_time_formatted,
            "isToday": is_today(match.get('commence_time'), selected_date_start),
            "totals": totals,
            "home": {
                "team": home_team,
                "score": home_score,
                "odds": home_odds
            },
            "away": {
                "team": away_team,
                "score": away_score,
                "odds": away_odds
            }
        }
        # Only add draw if this is a soccer_epl game and draw odds exist
        if match.get('sport_key') == 'soccer_epl' and draw_odds and draw_odds.get('h2h') is not None:
            game_obj["draw"] = {"h2h": draw_odds["h2h"]}
        return game_obj

    @staticmethod
    def get_single_game_from_db(sport_key, odds_event_id):
        """Fallback for expired games: query DB by odds_event_id. MLB only."""
        if sport_key != 'baseball_mlb':
            return None, 'Not supported'
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return None, 'Database connection failed'
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                port=parsed.port or 5432
            )
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT * FROM mlb_games WHERE odds_event_id = %s LIMIT 1",
                (odds_event_id,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row:
                return None, 'Game not found'
            return {
                'game': {
                    "game_id": odds_event_id,
                    "commence_time": row['game_date'].isoformat(),
                    "isToday": False,
                    "from_db": True,
                    "home": {
                        "team": row['home_team_name'],
                        "score": row['home_runs'],
                        "odds": {
                            "h2h": row['home_money_line'],
                            "spread_point": row['home_line'],
                            "spread_price": None
                        }
                    },
                    "away": {
                        "team": row['away_team_name'],
                        "score": row['away_runs'],
                        "odds": {
                            "h2h": row['away_money_line'],
                            "spread_point": row['away_line'],
                            "spread_price": None
                        }
                    },
                    "totals": {
                        "over_point": row['total'],
                        "under_point": row['total'],
                        "over_price": None,
                        "under_price": None
                    }
                }
            }, None
        except Exception as e:
            return None, str(e)
