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
            "completed": match.get('completed', False),
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
    def _get_matchup_db_service(sport_key):
        """Lazily import the per-sport historical service (avoids importing all 6 at
        module load time) and return (ServiceClass, away_score_field, home_score_field)."""
        if sport_key == 'baseball_mlb':
            from .historical.mlb_service import MLBService
            return MLBService, 'away_runs', 'home_runs'
        if sport_key == 'basketball_nba':
            from .historical.nba_service import NBAService
            return NBAService, 'away_points', 'home_points'
        if sport_key == 'americanfootball_nfl':
            from .historical.nfl_service import NFLService
            return NFLService, 'away_points', 'home_points'
        if sport_key == 'icehockey_nhl':
            from .historical.nhl_service import NHLService
            return NHLService, 'away_goals', 'home_goals'
        if sport_key == 'americanfootball_ncaaf':
            from .historical.ncaaf_service import NCAAFService
            return NCAAFService, 'away_points', 'home_points'
        if sport_key == 'basketball_ncaab':
            from .historical.ncaab_service import NCAABService
            return NCAABService, 'away_points', 'home_points'
        return None, None, None

    @staticmethod
    def resolve_matchup(sport_key, away_odds_name, home_odds_name, date_str, occurrence=1):
        """Resolve (sport, away team, home team, ET date, occurrence) -> game identity.
        Tries live Odds API data first, then falls back to the sport's historical DB table
        (for games that have aged out of the Odds API's lookback window).
        Returns ({"game_id":..., "source": "live"|"db", "game": {...}}, None) or (None, error)."""
        # Live path: reuse the existing today/date games flow, filter by team names.
        result, err = GameService.get_games_for_date(sport_key, date_str)
        if not err and result:
            matches = [
                g for g in result['games']
                if g['away']['team'] == away_odds_name and g['home']['team'] == home_odds_name
            ]
            matches.sort(key=lambda g: g.get('commence_time') or '')
            if len(matches) >= occurrence:
                game = matches[occurrence - 1]
                return {"game_id": game['game_id'], "source": "live", "game": game}, None

        # DB fallback: exact match by team names + date against the sport's historical table.
        # The *_games tables store short/abbreviated names (e.g. "Yankees", "IND"), not the
        # full Odds-API names used everywhere else in this flow — convert before querying.
        service_cls, away_score_field, home_score_field = GameService._get_matchup_db_service(sport_key)
        if not service_cls:
            return None, 'Sport not supported'

        from shared_utils import convert_team_name, convert_team_name_ncaab
        if sport_key == 'basketball_ncaab':
            db_home_name = convert_team_name_ncaab(home_odds_name)
            db_away_name = convert_team_name_ncaab(away_odds_name)
        else:
            db_home_name = convert_team_name(home_odds_name)
            db_away_name = convert_team_name(away_odds_name)

        games, db_err = service_cls.get_games_by_matchup(db_home_name, db_away_name, date_str)
        if db_err or not games or len(games) < occurrence:
            return None, 'Game not found'

        row = games[occurrence - 1]
        # Stringify to match the top-level "game_id" below (str(row.get('game_id')))
        # and the live-path shape, where both fields carry the identical value —
        # the frontend compares this nested id against the top-level one with ===.
        db_game_id = str(row.get('game_id'))
        formatted_game = {
            "game_id": db_game_id,
            "commence_time": row.get('game_date'),
            "isToday": False,
            "completed": True,
            "from_db": True,
            "home": {
                # Use the full Odds-API name passed in, not the DB's short name, so this
                # matches the shape/values of the live-path response.
                "team": home_odds_name,
                "score": row.get(home_score_field),
                "odds": {
                    "h2h": row.get('home_money_line'),
                    "spread_point": row.get('home_line'),
                    "spread_price": None,
                },
            },
            "away": {
                "team": away_odds_name,
                "score": row.get(away_score_field),
                "odds": {
                    "h2h": row.get('away_money_line'),
                    "spread_point": row.get('away_line'),
                    "spread_price": None,
                },
            },
            "totals": {
                "over_point": row.get('total'),
                "under_point": row.get('total'),
                "over_price": None,
                "under_price": None,
            },
        }
        return {"game_id": db_game_id, "source": "db", "game": formatted_game}, None

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
