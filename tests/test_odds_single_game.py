"""
Regression coverage for GET /api/odds/<sport>/<game_id>.

This is the endpoint whose response feeds GameDetails.tsx's `game` prop.
fetchMLBPlayerProps/fetchPlayerProps read the odds-api event id back out via
`(game as any).game_id` to fetch player props - if this response ever stops
including `game_id` on the nested `game` object, player props break silently
on every game-details page (the exact class of bug that shipped with the
SEO slug-URL change: nothing here changed, but nothing verified the contract
either).
"""
from unittest.mock import patch

from tests.conftest import make_test_app
from api.routes.odds import odds_bp


def _client():
    app = make_test_app(odds_bp)
    return app.test_client()


def test_single_game_odds_response_includes_nested_game_id(auth_headers):
    fake_result = {
        "game": {
            "game_id": "0f350cb709d6394c946ef1df6fca40af",
            "commence_time": "2026-07-29T01:41:00+00:00",
            "home": {"team": "Athletics"},
            "away": {"team": "Boston Red Sox"},
            "totals": {},
        }
    }
    with patch("api.routes.odds.GameService.get_single_game", return_value=(fake_result, None)):
        resp = _client().get(
            "/api/odds/baseball_mlb/0f350cb709d6394c946ef1df6fca40af",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    body = resp.get_json()
    # This is exactly what GameDetails.tsx's `(game as any).game_id` depends on.
    assert body["game"]["game_id"] == "0f350cb709d6394c946ef1df6fca40af"


def test_single_game_odds_falls_back_to_db_when_live_lookup_errors(auth_headers):
    fake_db_result = {
        "game": {
            "game_id": "12345",
            "from_db": True,
            "home": {"team": "Athletics"},
            "away": {"team": "Boston Red Sox"},
        }
    }
    with patch("api.routes.odds.GameService.get_single_game", return_value=(None, "Game not found")), \
         patch("api.routes.odds.GameService.get_single_game_from_db", return_value=(fake_db_result, None)):
        resp = _client().get("/api/odds/baseball_mlb/12345", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["game"]["game_id"] == "12345"


def test_single_game_odds_404_when_not_found_anywhere(auth_headers):
    with patch("api.routes.odds.GameService.get_single_game", return_value=(None, "Game not found")), \
         patch("api.routes.odds.GameService.get_single_game_from_db", return_value=(None, "Game not found")):
        resp = _client().get("/api/odds/baseball_mlb/doesnotexist", headers=auth_headers)

    assert resp.status_code == 404
