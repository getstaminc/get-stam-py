"""Coverage for /api/billing/* -- checkout/portal session creation and code redemption."""
from unittest.mock import patch

from tests.conftest import make_test_app
from api.routes.billing import billing_bp

FAKE_USER = {
    "id": 1,
    "email": "a@example.com",
    "timezone": "America/New_York",
    "theme_preference": "light",
    "plan": "free",
    "subscription_status": None,
    "trial_ends_at": None,
    "email_verified_at": "2026-08-16T00:00:00+00:00",
}


def _client():
    app = make_test_app(billing_bp)
    return app.test_client()


def test_checkout_session_requires_bearer_token(auth_headers):
    resp = _client().post("/api/billing/checkout-session", headers=auth_headers)
    assert resp.status_code == 401


def test_checkout_session_defaults_to_trial(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_token", return_value=FAKE_USER), \
         patch("api.services.billing_service.BillingService.create_checkout_session", return_value=("https://stripe.test/session", None)) as mock_create:
        resp = _client().post(
            "/api/billing/checkout-session",
            json={},
            headers={**auth_headers, "Authorization": "Bearer tok"},
        )
    assert resp.status_code == 200
    mock_create.assert_called_once_with(FAKE_USER, start_trial=True)


def test_checkout_session_can_skip_trial(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_token", return_value=FAKE_USER), \
         patch("api.services.billing_service.BillingService.create_checkout_session", return_value=("https://stripe.test/session", None)) as mock_create:
        resp = _client().post(
            "/api/billing/checkout-session",
            json={"trial": False},
            headers={**auth_headers, "Authorization": "Bearer tok"},
        )
    assert resp.status_code == 200
    mock_create.assert_called_once_with(FAKE_USER, start_trial=False)


def test_redeem_code_success(auth_headers):
    updated_user = {**FAKE_USER, "plan": "pro", "subscription_status": "comped"}
    with patch("api.services.auth_service.AuthService.verify_token", return_value=FAKE_USER), \
         patch("api.services.access_code_service.AccessCodeService.redeem", return_value=(updated_user, None)):
        resp = _client().post(
            "/api/billing/redeem-code",
            json={"code": "BETA2026"},
            headers={**auth_headers, "Authorization": "Bearer tok"},
        )
    assert resp.status_code == 200
    assert resp.get_json()["user"]["plan"] == "pro"


def test_redeem_code_already_redeemed_returns_409(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_token", return_value=FAKE_USER), \
         patch("api.services.access_code_service.AccessCodeService.redeem", return_value=(None, "already_redeemed")):
        resp = _client().post(
            "/api/billing/redeem-code",
            json={"code": "BETA2026"},
            headers={**auth_headers, "Authorization": "Bearer tok"},
        )
    assert resp.status_code == 409


def test_redeem_code_invalid_returns_400(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_token", return_value=FAKE_USER), \
         patch("api.services.access_code_service.AccessCodeService.redeem", return_value=(None, "invalid_code")):
        resp = _client().post(
            "/api/billing/redeem-code",
            json={"code": "NOTREAL"},
            headers={**auth_headers, "Authorization": "Bearer tok"},
        )
    assert resp.status_code == 400
