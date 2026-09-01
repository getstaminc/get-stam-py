"""Coverage for BillingService.handle_webhook_event's idempotency guard.

Stripe delivers webhooks at-least-once, so the same event id can arrive twice
even after a 200 was already returned. The guard is a plain
"INSERT ... ON CONFLICT (id) DO NOTHING" against processed_stripe_events;
0 rows affected means "already processed" and the update must be skipped.
"""
from unittest.mock import MagicMock, patch

from api.services.billing_service import BillingService

CHECKOUT_EVENT = {
    "id": "evt_1",
    "type": "checkout.session.completed",
    "created": 1000,
    "data": {"object": {"client_reference_id": "1", "customer": "cus_1", "subscription": "sub_1"}},
}


def _mock_conn(rowcount):
    """A MagicMock standing in for `with _get_conn() as conn: with conn.cursor() as cur:`."""
    mock_cur = MagicMock()
    mock_cur.rowcount = rowcount
    mock_cur.__enter__.return_value = mock_cur
    mock_cur.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    return mock_conn, mock_cur


def test_new_event_runs_idempotency_insert_and_update():
    mock_conn, mock_cur = _mock_conn(rowcount=1)  # fresh insert -> 1 row affected
    fake_subscription = {"status": "trialing", "trial_end": 2000}
    with patch("api.services.billing_service._get_conn", return_value=mock_conn), \
         patch("api.services.billing_service.stripe.Subscription.retrieve", return_value=fake_subscription) as mock_retrieve:
        ok, err = BillingService.handle_webhook_event(CHECKOUT_EVENT)

    assert ok is True
    assert err is None
    mock_retrieve.assert_called_once_with("sub_1")
    # INSERT (idempotency) + UPDATE (apply the event) = 2 statements
    assert mock_cur.execute.call_count == 2
    # subscription_status/trial_ends_at come from the retrieved subscription, not a placeholder
    update_args = mock_cur.execute.call_args_list[1][0][1]
    assert "trialing" in update_args


def test_subscription_retrieve_failure_falls_back_to_active():
    mock_conn, mock_cur = _mock_conn(rowcount=1)
    with patch("api.services.billing_service._get_conn", return_value=mock_conn), \
         patch("api.services.billing_service.stripe.Subscription.retrieve", side_effect=Exception("network error")):
        ok, err = BillingService.handle_webhook_event(CHECKOUT_EVENT)

    assert ok is True
    assert err is None
    update_args = mock_cur.execute.call_args_list[1][0][1]
    assert "active" in update_args


def test_duplicate_event_skips_the_update():
    mock_conn, mock_cur = _mock_conn(rowcount=0)  # ON CONFLICT DO NOTHING -> 0 rows, a replay
    with patch("api.services.billing_service._get_conn", return_value=mock_conn):
        ok, err = BillingService.handle_webhook_event(CHECKOUT_EVENT)

    assert ok is True
    assert err is None
    # Only the idempotency INSERT ran -- the replay must not touch the users row
    assert mock_cur.execute.call_count == 1


def test_db_error_returns_false_with_error():
    mock_conn, mock_cur = _mock_conn(rowcount=1)
    mock_cur.execute.side_effect = Exception("connection lost")
    with patch("api.services.billing_service._get_conn", return_value=mock_conn):
        ok, err = BillingService.handle_webhook_event(CHECKOUT_EVENT)

    assert ok is False
    assert err
