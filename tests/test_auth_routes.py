"""Coverage for /api/auth/* — passwordless request-code/verify-code and the bearer-token-gated /me routes."""
from unittest.mock import patch

from tests.conftest import make_test_app
from api.routes.auth import auth_bp


def _client():
    app = make_test_app(auth_bp)
    return app.test_client()


def _fake_user(**overrides):
    user = {
        "id": 1,
        "email": "a@example.com",
        "timezone": "America/New_York",
        "theme_preference": "light",
        "plan": "free",
        "subscription_status": None,
        "trial_ends_at": None,
        "token_version": 0,
        "email_verified_at": "2026-08-16T00:00:00+00:00",
    }
    user.update(overrides)
    return user


def test_request_code_success_sends_email(auth_headers):
    with patch("api.services.auth_service.AuthService.request_code", return_value=(_fake_user(), "123456", None)), \
         patch("api.routes.auth.EmailService.send_digest_to_one", return_value=(True, None)) as mock_send:
        resp = _client().post("/api/auth/request-code", json={"email": "a@example.com"}, headers=auth_headers)

    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "123456" in mock_send.call_args[0][2]  # code is in the email HTML


def test_request_code_passes_intent_through_to_service(auth_headers):
    with patch("api.services.auth_service.AuthService.request_code", return_value=(_fake_user(), "123456", None)) as mock_request, \
         patch("api.routes.auth.EmailService.send_digest_to_one", return_value=(True, None)):
        resp = _client().post(
            "/api/auth/request-code",
            json={"email": "a@example.com", "intent": "trial"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    mock_request.assert_called_once_with("a@example.com", intent="trial", require_existing=False)


def test_request_code_invalid_email_returns_400(auth_headers):
    with patch("api.services.auth_service.AuthService.request_code", return_value=(None, None, "invalid_email")):
        resp = _client().post("/api/auth/request-code", json={"email": "not-an-email"}, headers=auth_headers)
    assert resp.status_code == 400


def test_request_code_require_existing_passes_flag_through(auth_headers):
    with patch("api.services.auth_service.AuthService.request_code", return_value=(_fake_user(), "123456", None)) as mock_request, \
         patch("api.routes.auth.EmailService.send_digest_to_one", return_value=(True, None)):
        resp = _client().post(
            "/api/auth/request-code",
            json={"email": "a@example.com", "require_existing": True},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    mock_request.assert_called_once_with("a@example.com", intent=None, require_existing=True)


def test_request_code_account_not_found_returns_404(auth_headers):
    with patch("api.services.auth_service.AuthService.request_code", return_value=(None, None, "account_not_found")), \
         patch("api.routes.auth.EmailService.send_digest_to_one") as mock_send:
        resp = _client().post(
            "/api/auth/request-code",
            json={"email": "unknown@example.com", "require_existing": True},
            headers=auth_headers,
        )
    assert resp.status_code == 404
    mock_send.assert_not_called()


def test_request_code_requires_api_key():
    resp = _client().post("/api/auth/request-code", json={"email": "a@example.com"})
    assert resp.status_code == 401


def test_verify_code_invalid_code_returns_400(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_code", return_value=(None, "invalid_code", False)):
        resp = _client().post("/api/auth/verify-code", json={"email": "a@example.com", "code": "000000"}, headers=auth_headers)
    assert resp.status_code == 400


def test_verify_code_too_many_attempts_returns_429(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_code", return_value=(None, "too_many_attempts", False)):
        resp = _client().post("/api/auth/verify-code", json={"email": "a@example.com", "code": "000000"}, headers=auth_headers)
    assert resp.status_code == 429


def test_verify_code_success_logs_the_user_in(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_code", return_value=(_fake_user(), None, False)), \
         patch("api.services.auth_service.AuthService.issue_token", return_value="tok123"):
        resp = _client().post("/api/auth/verify-code", json={"email": "a@example.com", "code": "123456"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["token"] == "tok123"
    assert body["user"]["email_verified"] is True
    assert "checkout_url" not in body


def test_verify_code_first_verification_with_trial_intent_returns_checkout_url(auth_headers):
    trial_user = _fake_user(signup_intent="trial")
    with patch("api.services.auth_service.AuthService.verify_code", return_value=(trial_user, None, True)), \
         patch("api.services.auth_service.AuthService.issue_token", return_value="tok123"), \
         patch("api.services.billing_service.BillingService.create_checkout_session", return_value=("https://checkout.stripe.com/fake", None)) as mock_checkout:
        resp = _client().post("/api/auth/verify-code", json={"email": "a@example.com", "code": "123456"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["checkout_url"] == "https://checkout.stripe.com/fake"
    mock_checkout.assert_called_once_with(trial_user, start_trial=True)


def test_verify_code_returning_user_with_trial_intent_skips_checkout(auth_headers):
    """is_first_verification=False means this is a returning login, not a fresh signup --
    even if signup_intent happens to still say 'trial', don't re-trigger checkout."""
    trial_user = _fake_user(signup_intent="trial")
    with patch("api.services.auth_service.AuthService.verify_code", return_value=(trial_user, None, False)), \
         patch("api.services.auth_service.AuthService.issue_token", return_value="tok123"), \
         patch("api.services.billing_service.BillingService.create_checkout_session") as mock_checkout:
        resp = _client().post("/api/auth/verify-code", json={"email": "a@example.com", "code": "123456"}, headers=auth_headers)
    assert resp.status_code == 200
    assert "checkout_url" not in resp.get_json()
    mock_checkout.assert_not_called()


def test_verify_code_trial_intent_checkout_failure_is_non_fatal(auth_headers):
    """Checkout creation failing shouldn't break verification -- they're still logged in,
    just land on the site instead of Checkout."""
    trial_user = _fake_user(signup_intent="trial")
    with patch("api.services.auth_service.AuthService.verify_code", return_value=(trial_user, None, True)), \
         patch("api.services.auth_service.AuthService.issue_token", return_value="tok123"), \
         patch("api.services.billing_service.BillingService.create_checkout_session", return_value=(None, "stripe error")):
        resp = _client().post("/api/auth/verify-code", json={"email": "a@example.com", "code": "123456"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["token"] == "tok123"
    assert "checkout_url" not in body


def test_me_requires_bearer_token(auth_headers):
    resp = _client().get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 401


def test_me_rejects_invalid_token(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_token", return_value=None):
        resp = _client().get("/api/auth/me", headers={**auth_headers, "Authorization": "Bearer badtoken"})
    assert resp.status_code == 401


def test_me_returns_user_for_valid_token(auth_headers):
    with patch("api.services.auth_service.AuthService.verify_token", return_value=_fake_user()):
        resp = _client().get("/api/auth/me", headers={**auth_headers, "Authorization": "Bearer goodtoken"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "a@example.com"


def test_update_me_patches_profile(auth_headers):
    updated = _fake_user(theme_preference="dark")
    with patch("api.services.auth_service.AuthService.verify_token", return_value=_fake_user()), \
         patch("api.services.auth_service.AuthService.update_profile", return_value=(updated, None)):
        resp = _client().patch(
            "/api/auth/me",
            json={"theme_preference": "dark"},
            headers={**auth_headers, "Authorization": "Bearer goodtoken"},
        )
    assert resp.status_code == 200
    assert resp.get_json()["user"]["theme_preference"] == "dark"
