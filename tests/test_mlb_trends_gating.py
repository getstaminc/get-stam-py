"""Coverage for the Pro-plan gate on MLB trends' min_trend_length parameter.

Regression target: the cache key must encode the CLAMPED value, not the raw
requested one, or a free-tier request for minTrendLength=10 would populate the
shared cache under key "...:m10" with clamped (limit-5) results, which would
then be served to the next caller requesting m10 -- including a legitimate Pro
user.
"""
from unittest.mock import patch

from tests.conftest import make_test_app
from api.routes.historical.mlb_trends import mlb_trends_bp, make_mlb_trends_cache_key

GAMES = [{"home_team_name": "Pirates", "away_team_name": "Red Sox"}]
PRO_USER = {"plan": "pro", "subscription_status": "active"}
TRIALING_USER = {"plan": "pro", "subscription_status": "trialing"}
CANCELED_USER = {"plan": "pro", "subscription_status": "canceled"}


def _client():
    app = make_test_app(mlb_trends_bp)
    return app.test_client()


def test_anonymous_request_clamped_to_5(auth_headers):
    with patch("api.routes.historical.mlb_trends.get_current_user_optional", return_value=None), \
         patch("api.routes.historical.mlb_trends.MLBTrendsService.analyze_multiple_games_trends", return_value=([], None)) as mock_analyze:
        resp = _client().post(
            "/api/historical/trends/mlb",
            json={"games": GAMES, "minTrendLength": 10},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["min_trend_length"] == 5
    assert mock_analyze.call_args[0][2] == 5


def test_free_plan_user_clamped_to_5(auth_headers):
    with patch("api.routes.historical.mlb_trends.get_current_user_optional", return_value={"plan": "free", "subscription_status": None}), \
         patch("api.routes.historical.mlb_trends.MLBTrendsService.analyze_multiple_games_trends", return_value=([], None)):
        resp = _client().post(
            "/api/historical/trends/mlb",
            json={"games": GAMES, "minTrendLength": 10},
            headers={**auth_headers, "Authorization": "Bearer sometoken"},
        )
    assert resp.get_json()["meta"]["min_trend_length"] == 5


def test_canceled_pro_user_clamped_to_5(auth_headers):
    """plan='pro' alone isn't enough -- a lapsed subscription must fall back to free limits."""
    with patch("api.routes.historical.mlb_trends.get_current_user_optional", return_value=CANCELED_USER), \
         patch("api.routes.historical.mlb_trends.MLBTrendsService.analyze_multiple_games_trends", return_value=([], None)):
        resp = _client().post(
            "/api/historical/trends/mlb",
            json={"games": GAMES, "minTrendLength": 10},
            headers={**auth_headers, "Authorization": "Bearer sometoken"},
        )
    assert resp.get_json()["meta"]["min_trend_length"] == 5


def test_active_pro_user_allowed_10(auth_headers):
    with patch("api.routes.historical.mlb_trends.get_current_user_optional", return_value=PRO_USER), \
         patch("api.routes.historical.mlb_trends.MLBTrendsService.analyze_multiple_games_trends", return_value=([], None)) as mock_analyze:
        resp = _client().post(
            "/api/historical/trends/mlb",
            json={"games": GAMES, "minTrendLength": 10},
            headers={**auth_headers, "Authorization": "Bearer sometoken"},
        )
    assert resp.get_json()["meta"]["min_trend_length"] == 10
    assert mock_analyze.call_args[0][2] == 10


def test_trialing_pro_user_allowed_10(auth_headers):
    with patch("api.routes.historical.mlb_trends.get_current_user_optional", return_value=TRIALING_USER), \
         patch("api.routes.historical.mlb_trends.MLBTrendsService.analyze_multiple_games_trends", return_value=([], None)):
        resp = _client().post(
            "/api/historical/trends/mlb",
            json={"games": GAMES, "minTrendLength": 10},
            headers={**auth_headers, "Authorization": "Bearer sometoken"},
        )
    assert resp.get_json()["meta"]["min_trend_length"] == 10


def test_low_request_is_not_raised_to_the_max(auth_headers):
    """Clamping is an upper bound only -- a pro user asking for 3 should get 3, not 10."""
    with patch("api.routes.historical.mlb_trends.get_current_user_optional", return_value=PRO_USER), \
         patch("api.routes.historical.mlb_trends.MLBTrendsService.analyze_multiple_games_trends", return_value=([], None)) as mock_analyze:
        resp = _client().post(
            "/api/historical/trends/mlb",
            json={"games": GAMES, "minTrendLength": 3},
            headers={**auth_headers, "Authorization": "Bearer sometoken"},
        )
    assert resp.get_json()["meta"]["min_trend_length"] == 3
    assert mock_analyze.call_args[0][2] == 3


def test_cache_key_differs_for_free_vs_pro_on_identical_payload(auth_headers):
    app = make_test_app(mlb_trends_bp)
    body = {"games": GAMES, "minTrendLength": 10}

    with app.test_request_context("/api/historical/trends/mlb", method="POST", json=body):
        with patch("api.routes.historical.mlb_trends.get_current_user_optional", return_value=None):
            anon_key = make_mlb_trends_cache_key()

    with app.test_request_context("/api/historical/trends/mlb", method="POST", json=body):
        with patch("api.routes.historical.mlb_trends.get_current_user_optional", return_value=PRO_USER):
            pro_key = make_mlb_trends_cache_key()

    assert anon_key != pro_key
    assert anon_key.endswith(":m5")
    assert pro_key.endswith(":m10")
