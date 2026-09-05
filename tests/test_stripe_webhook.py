"""Coverage for the /api/webhooks/stripe route (signature verification + dispatch).

No X-API-KEY here by design -- Stripe calls this endpoint directly and can't
attach our frontend secret, so it's verified via Stripe-Signature instead
(mirrors the youtube webhook precedent).
"""
from unittest.mock import patch

import stripe

from tests.conftest import make_test_app
from api.routes.webhooks.stripe_webhook import stripe_webhook_bp


def _client():
    app = make_test_app(stripe_webhook_bp)
    return app.test_client()


def test_bad_signature_returns_400_and_skips_processing():
    with patch(
        "api.routes.webhooks.stripe_webhook.stripe.Webhook.construct_event",
        side_effect=stripe.error.SignatureVerificationError("bad sig", "sig_header"),
    ), patch("api.routes.webhooks.stripe_webhook.BillingService.handle_webhook_event") as mock_handle:
        resp = _client().post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "bad"})

    assert resp.status_code == 400
    mock_handle.assert_not_called()


def test_valid_event_is_dispatched_exactly_once():
    fake_event = {"id": "evt_1", "type": "checkout.session.completed", "created": 123, "data": {"object": {}}}
    with patch("api.routes.webhooks.stripe_webhook.stripe.Webhook.construct_event", return_value=fake_event), \
         patch("api.routes.webhooks.stripe_webhook.BillingService.handle_webhook_event", return_value=(True, None)) as mock_handle:
        resp = _client().post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "good"})

    assert resp.status_code == 200
    mock_handle.assert_called_once_with(fake_event)


def test_handler_failure_returns_500():
    fake_event = {"id": "evt_1", "type": "checkout.session.completed", "created": 123, "data": {"object": {}}}
    with patch("api.routes.webhooks.stripe_webhook.stripe.Webhook.construct_event", return_value=fake_event), \
         patch("api.routes.webhooks.stripe_webhook.BillingService.handle_webhook_event", return_value=(False, "db error")):
        resp = _client().post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "good"})

    assert resp.status_code == 500
