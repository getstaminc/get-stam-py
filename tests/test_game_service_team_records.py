"""Coverage for GameService attaching NFL team win-loss records to formatted
games — batch-fetched once per request, scoped to NFL only."""
from unittest.mock import patch

from api.services.game_service import GameService


FAKE_SCORES = [
    {
        "id": "evt1",
        "sport_key": "americanfootball_nfl",
        "home_team": "New Orleans Saints",
        "away_team": "Pittsburgh Steelers",
        "commence_time": "2026-10-22T23:05:00Z",
        "completed": False,
        "scores": None,
    }
]
FAKE_ODDS = [{"id": "evt1", "bookmakers": []}]

FAKE_RECORDS = {
    "Saints": {"wins": 4, "losses": 2, "ties": 0},
    "Steelers": {"wins": 3, "losses": 3, "ties": 1},
}


def test_get_games_for_date_attaches_team_records_for_nfl():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines", return_value={}), \
         patch("api.services.historical.nfl_service.NFLService.get_team_records",
               return_value=FAKE_RECORDS) as mock_get_records:
        result, error = GameService.get_games_for_date("americanfootball_nfl")

    assert error is None
    game = result["games"][0]
    assert game["home"]["record"] == {"wins": 4, "losses": 2, "ties": 0}
    assert game["away"]["record"] == {"wins": 3, "losses": 3, "ties": 1}
    # batched once, not once per team/game
    mock_get_records.assert_called_once()
    called_names = set(mock_get_records.call_args[0][0])
    assert called_names == {"Saints", "Steelers"}


def test_get_games_for_date_omits_record_when_team_has_no_games_yet():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines", return_value={}), \
         patch("api.services.historical.nfl_service.NFLService.get_team_records", return_value={}):
        result, error = GameService.get_games_for_date("americanfootball_nfl")

    assert error is None
    game = result["games"][0]
    assert "record" not in game["home"]
    assert "record" not in game["away"]


def test_get_games_for_date_skips_team_record_lookup_for_unsupported_sport():
    nba_scores = [{**FAKE_SCORES[0], "sport_key": "basketball_nba"}]
    with patch("api.services.game_service.get_odds_data", return_value=(nba_scores, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines", return_value={}), \
         patch("api.services.historical.nfl_service.NFLService.get_team_records") as mock_get_records:
        result, error = GameService.get_games_for_date("basketball_nba")

    assert error is None
    assert "record" not in result["games"][0]["home"]
    mock_get_records.assert_not_called()


def test_get_single_game_attaches_team_records_for_nfl():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines", return_value={}), \
         patch("api.services.historical.nfl_service.NFLService.get_team_records",
               return_value=FAKE_RECORDS):
        result, error = GameService.get_single_game("americanfootball_nfl", "evt1")

    assert error is None
    game = result["game"]
    assert game["home"]["record"] == {"wins": 4, "losses": 2, "ties": 0}
    assert game["away"]["record"] == {"wins": 3, "losses": 3, "ties": 1}


def test_get_games_for_date_tolerates_team_records_db_error():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines", return_value={}), \
         patch("api.services.historical.nfl_service.NFLService.get_team_records",
               side_effect=Exception("db down")):
        result, error = GameService.get_games_for_date("americanfootball_nfl")

    assert error is None
    assert "record" not in result["games"][0]["home"]
