"""The Pro gate on min trend length applies to every sport's trends endpoint, not just MLB.

MLB's detailed coverage (trialing/canceled plans, cache key) lives in
test_mlb_trends_gating.py; this checks each other route is wired to the shared gate.
"""
from unittest.mock import patch

import pytest

from tests.conftest import make_test_app
from api.routes.historical.nba_trends import nba_trends_bp
from api.routes.historical.nfl_trends import nfl_trends_bp
from api.routes.historical.nhl_trends import nhl_trends_bp
from api.routes.historical.ncaaf_trends import ncaaf_trends_bp
from api.routes.historical.ncaab_trends import ncaab_trends_bp
from api.routes.historical.soccer_trends import soccer_trends_bp

GAMES = [{"game_id": "abc", "home_team_name": "A", "away_team_name": "B"}]
PRO_USER = {"plan": "pro", "subscription_status": "active"}

# (blueprint, url, service analyze target, free-tier cap)
ROUTES = [
    (nba_trends_bp, "/api/historical/trends/nba", "api.routes.historical.nba_trends.NBATrendsService.analyze_multiple_games_trends", 5),
    (nfl_trends_bp, "/api/historical/trends/nfl", "api.routes.historical.nfl_trends.NFLTrendsService.analyze_multiple_games_trends", 5),
    (nhl_trends_bp, "/api/historical/trends/nhl", "api.routes.historical.nhl_trends.NHLTrendsService.analyze_multiple_games_trends", 5),
    (ncaaf_trends_bp, "/api/historical/trends/ncaaf", "api.routes.historical.ncaaf_trends.NCAAFTrendsService.analyze_multiple_games_trends", 7),
    (ncaab_trends_bp, "/api/historical/trends/ncaab", "api.routes.historical.ncaab_trends.NCAABTrendsService.analyze_multiple_games_trends", 7),
    (soccer_trends_bp, "/api/historical/trends/soccer", "api.routes.historical.soccer_trends.SoccerTrendsService.analyze_multiple_games_trends", 5),
    (soccer_trends_bp, "/api/historical/trends/soccer/epl", "api.routes.historical.soccer_trends.SoccerTrendsService.analyze_multiple_games_trends", 5),
]


def _post(bp, url, user, min_len, auth_headers, analyze_target):
    with patch("api.routes.historical.trend_length_gate.get_current_user_optional", return_value=user), \
         patch(analyze_target, return_value=([], None)) as mock_analyze:
        resp = make_test_app(bp).test_client().post(
            url, json={"games": GAMES, "minTrendLength": min_len}, headers=auth_headers,
        )
    return resp, mock_analyze


@pytest.mark.parametrize("bp,url,analyze_target,free_cap", ROUTES)
def test_free_user_clamped_to_free_cap(bp, url, analyze_target, free_cap, auth_headers):
    """5+ for most sports; college gets 7+ free (only 10+ is Pro)."""
    resp, mock_analyze = _post(bp, url, None, 10, auth_headers, analyze_target)
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["min_trend_length"] == free_cap
    assert mock_analyze.call_args[0][2] == free_cap


@pytest.mark.parametrize("bp,url,analyze_target,free_cap", ROUTES)
def test_pro_user_allowed_10(bp, url, analyze_target, free_cap, auth_headers):
    resp, mock_analyze = _post(bp, url, PRO_USER, 10, auth_headers, analyze_target)
    assert resp.get_json()["meta"]["min_trend_length"] == 10
    assert mock_analyze.call_args[0][2] == 10


@pytest.mark.parametrize("bp,url,analyze_target,free_cap", ROUTES)
def test_free_user_below_cap_unchanged(bp, url, analyze_target, free_cap, auth_headers):
    resp, mock_analyze = _post(bp, url, None, 3, auth_headers, analyze_target)
    assert resp.get_json()["meta"]["min_trend_length"] == 3
    assert mock_analyze.call_args[0][2] == 3


@pytest.mark.parametrize("bp,url,analyze_target", [r[:3] for r in ROUTES if r[3] == 7])
def test_college_free_user_gets_7_unclamped(bp, url, analyze_target, auth_headers):
    """The home page requests 7+ for college without a login — it must not be clamped."""
    resp, mock_analyze = _post(bp, url, None, 7, auth_headers, analyze_target)
    assert resp.get_json()["meta"]["min_trend_length"] == 7
    assert mock_analyze.call_args[0][2] == 7
