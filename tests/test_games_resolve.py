"""
Regression coverage for the /api/games/resolve/<sport>/<away>/<home>/<date>
endpoint, which the slug-based game-details URL (/game-details/:sport/:slug)
depends on to turn a matchup slug into a game_id.

The bug this guards against: GameDetails.tsx used to read game_id from the
`?game_id=` query string, which the slug route never sets - player props
silently never loaded on slug URLs. The fix made the frontend read game_id
from the fetched game object instead. These tests pin the contract that fix
depends on: the resolve response must carry a top-level `game_id`.
"""
from unittest.mock import patch

from tests.conftest import make_test_app
from api.routes.games import games_bp


def _client():
    app = make_test_app(games_bp)
    return app.test_client()


def test_resolve_matchup_returns_top_level_game_id(auth_headers):
    fake_result = {
        "game_id": "abc123eventid",
        "source": "live",
        "game": {"game_id": "abc123eventid", "home": {"team": "Athletics"}, "away": {"team": "Boston Red Sox"}},
    }
    with patch("api.routes.games.GameService.resolve_matchup", return_value=(fake_result, None)):
        resp = _client().get(
            "/api/games/resolve/mlb/boston-red-sox/athletics/2026-07-28",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["game_id"] == "abc123eventid"


def test_resolve_matchup_unknown_team_slug_returns_404(auth_headers):
    with patch("api.routes.games.GameService.get_games_for_date", return_value=({"games": []}, None)):
        resp = _client().get(
            "/api/games/resolve/mlb/not-a-real-team/athletics/2026-07-28",
            headers=auth_headers,
        )
    assert resp.status_code == 404


def test_resolve_matchup_unknown_sport_returns_404_without_fetching(auth_headers):
    with patch("api.routes.games.GameService.get_games_for_date") as mock_fetch:
        resp = _client().get(
            "/api/games/resolve/curling/a-team/b-team/2026-07-28",
            headers=auth_headers,
        )
    assert resp.status_code == 404
    mock_fetch.assert_not_called()


def _live(away, home, game_id="live1"):
    return {"game_id": game_id, "commence_time": "2026-11-05T23:00:00+00:00",
            "away": {"team": away}, "home": {"team": home}}


def test_resolve_matchup_matches_live_game_by_slug_for_teams_missing_from_list(auth_headers):
    """Most NCAAB programs (e.g. Bellarmine) aren't in SPORT_TEAMS; the live game still resolves."""
    games = {"games": [_live("Bellarmine Knights", "Indiana Hoosiers", "ev123")]}
    with patch("api.routes.games.GameService.get_games_for_date", return_value=(games, None)):
        resp = _client().get(
            "/api/games/resolve/ncaab/bellarmine-knights/indiana-hoosiers/2026-11-05",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.get_json()["game_id"] == "ev123"


def test_resolve_matchup_requires_api_key():
    resp = _client().get("/api/games/resolve/mlb/boston-red-sox/athletics/2026-07-28")
    assert resp.status_code == 401
