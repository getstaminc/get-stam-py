"""Shared game-data fetching for a single matchup (last-5, home/away splits, H2H, trends)."""

import logging
from datetime import date

logger = logging.getLogger(__name__)


def fetch_game_data(sport, sport_key, home_team, away_team, game_date=None):
    """Fetch historical game data for a matchup. Returns (game_data_dict, odds_event_id, game_date_used, error)."""
    if sport not in ("mlb", "nhl"):
        return None, None, None, f"Sport '{sport}' not yet supported for game data fetch"

    try:
        if sport == "mlb":
            from .historical.mlb_service import MLBService as SportService
            from .historical.mlb_trends_service import MLBTrendsService as TrendsService
        else:
            from .historical.nhl_service import NHLService as SportService
            from .historical.nhl_trends_service import NHLTrendsService as TrendsService

        # Determine game date
        if game_date:
            game_date_used = game_date if isinstance(game_date, str) else str(game_date)
        else:
            game_date_used = str(date.today())

        # 1. Try to find odds_event_id from a live games lookup (best-effort)
        odds_event_id = None
        try:
            from .game_service import GameService
            result, _ = GameService.get_games_for_date(sport_key or "baseball_mlb", game_date_used)
            games_list = (result or {}).get('games', [])
            home_lower = home_team.lower()
            away_lower = away_team.lower()
            for g in games_list:
                g_home = (g.get('home', {}).get('team') or '').lower()
                g_away = (g.get('away', {}).get('team') or '').lower()
                # Match short name (e.g. "Avalanche") against full name ("Colorado Avalanche")
                if (home_lower in g_home or g_home in home_lower) and \
                   (away_lower in g_away or g_away in away_lower):
                    odds_event_id = g.get('game_id')
                    break
        except Exception as e:
            logger.warning("Could not fetch odds event_id: %s", e)

        # 2. Fetch last 5 games for each team (overall)
        home_last_5, _ = SportService.get_team_games_by_name(home_team, limit=5)
        away_last_5, _ = SportService.get_team_games_by_name(away_team, limit=5)

        # 3. Fetch last 5 home games for home team
        home_home_last_5, _ = SportService.get_team_games_by_name(home_team, limit=5, venue='home')

        # 4. Fetch last 5 away games for away team
        away_away_last_5, _ = SportService.get_team_games_by_name(away_team, limit=5, venue='away')

        # 5. Head-to-head last 5
        h2h_last_5, _ = SportService.get_head_to_head_games_by_name(home_team, away_team, limit=5)

        # 6. Trends
        trends_results, _ = TrendsService.analyze_multiple_games_trends(
            [{"home_team_name": home_team, "away_team_name": away_team}],
            limit=20
        )
        trends = trends_results[0] if trends_results else {}

        game_data = {
            "home_last_5": home_last_5 or [],
            "away_last_5": away_last_5 or [],
            "home_home_last_5": home_home_last_5 or [],
            "away_away_last_5": away_away_last_5 or [],
            "h2h_last_5": h2h_last_5 or [],
            "trends": trends,
        }

        return game_data, odds_event_id, game_date_used, None

    except Exception as e:
        logger.error("fetch_game_data error: %s", e)
        return None, None, None, str(e)
