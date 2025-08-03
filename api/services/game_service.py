"""
Game service for handling game-related business logic
"""
from datetime import datetime, date
import pytz
from dateutil import parser

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
        home_odds, away_odds, totals = process_odds_data(match, odds, home_team, away_team)

        # Format commence time
        commence_time_formatted = format_commence_time(match.get('commence_time'))

        return {
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
