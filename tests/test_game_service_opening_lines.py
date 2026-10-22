"""Coverage for GameService attaching cached opening-line data to formatted games —
for the sports that have it, and specifically not for the ones that don't."""
from unittest.mock import patch

from api.services.game_service import GameService


FAKE_SCORES = [
    {
        "id": "evt1",
        "sport_key": "americanfootball_nfl",
        "home_team": "Chicago Bears",
        "away_team": "New England Patriots",
        "commence_time": "2026-10-26T18:15:00Z",
        "completed": False,
        "scores": None,
    }
]
FAKE_ODDS = [{"id": "evt1", "bookmakers": []}]

FAKE_OPENING_ROW = {
    "odds_event_id": "evt1",
    "home_spread_point": -3.0,
    "home_spread_price": -105,
    "away_spread_point": 3.0,
    "away_spread_price": -118,
    "home_moneyline": -155,
    "away_moneyline": 130,
    "total_point": 47.5,
    "over_price": -110,
    "under_price": -115,
    "opening_snapshot_time": None,
}


def test_get_games_for_date_attaches_opening_line_for_nfl():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines",
               return_value={"evt1": FAKE_OPENING_ROW}) as mock_get_opening:
        result, error = GameService.get_games_for_date("americanfootball_nfl")

    assert error is None
    game = result["games"][0]
    assert game["opening"]["home"]["spread_point"] == -3.0
    assert game["opening"]["away"]["h2h"] == 130
    assert game["opening"]["totals"]["over_point"] == 47.5
    mock_get_opening.assert_called_once_with("americanfootball_nfl", ["evt1"])


def test_get_games_for_date_omits_opening_line_when_not_captured_yet():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines", return_value={}):
        result, error = GameService.get_games_for_date("americanfootball_nfl")

    assert error is None
    assert "opening" not in result["games"][0]


def test_get_games_for_date_skips_opening_line_lookup_for_unsupported_sport():
    nba_scores = [{**FAKE_SCORES[0], "sport_key": "basketball_nba"}]
    with patch("api.services.game_service.get_odds_data", return_value=(nba_scores, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines") as mock_get_opening:
        result, error = GameService.get_games_for_date("basketball_nba")

    assert error is None
    assert "opening" not in result["games"][0]
    mock_get_opening.assert_not_called()


def test_get_single_game_attaches_opening_line():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines",
               return_value={"evt1": FAKE_OPENING_ROW}):
        result, error = GameService.get_single_game("americanfootball_nfl", "evt1")

    assert error is None
    assert result["game"]["opening"]["home"]["h2h"] == -155


def test_get_games_for_date_tolerates_opening_lines_db_error():
    """A DB failure fetching opening lines (unreachable Postgres, missing migration,
    etc.) must not 500 the whole odds endpoint — it should degrade to no opening
    line data, same as 'not captured yet'."""
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines",
               side_effect=Exception("db unreachable")):
        result, error = GameService.get_games_for_date("americanfootball_nfl")

    assert error is None
    assert result["games"][0]["game_id"] == "evt1"
    assert "opening" not in result["games"][0]


def test_get_single_game_tolerates_opening_lines_db_error():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines",
               side_effect=Exception("db unreachable")):
        result, error = GameService.get_single_game("americanfootball_nfl", "evt1")

    assert error is None
    assert result["game"]["game_id"] == "evt1"
    assert "opening" not in result["game"]
