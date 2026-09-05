"""Coverage for AccessCodeService.redeem -- comp codes that grant Pro access without Stripe."""
from unittest.mock import MagicMock, patch

from api.services.access_code_service import AccessCodeService


def _mock_conn(fetchone_side_effect, rowcount):
    """A MagicMock standing in for `with _get_conn() as conn: with conn.cursor() as cur:`."""
    mock_cur = MagicMock()
    mock_cur.fetchone.side_effect = fetchone_side_effect
    mock_cur.rowcount = rowcount
    mock_cur.__enter__.return_value = mock_cur
    mock_cur.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    return mock_conn, mock_cur


def test_redeem_success_grants_pro():
    user_row = {"access_code_id": None}
    access_code_row = {"id": 10, "expires_at": None, "max_redemptions": None}
    updated_user = {"id": 1, "plan": "pro", "subscription_status": "comped", "access_code_id": 10}
    mock_conn, mock_cur = _mock_conn([user_row, access_code_row, updated_user], rowcount=1)

    with patch("api.services.access_code_service._get_conn", return_value=mock_conn):
        user, error = AccessCodeService.redeem(1, "beta2026")  # lowercase input, should normalize

    assert error is None
    assert user["plan"] == "pro"
    assert user["subscription_status"] == "comped"
    # code was normalized to uppercase before the lookup query
    lookup_call = mock_cur.execute.call_args_list[1]
    assert lookup_call[0][1] == ("BETA2026",)


def test_redeem_rejects_already_redeemed_user():
    user_row = {"access_code_id": 5}  # already redeemed a code
    mock_conn, mock_cur = _mock_conn([user_row], rowcount=1)

    with patch("api.services.access_code_service._get_conn", return_value=mock_conn):
        user, error = AccessCodeService.redeem(1, "BETA2026")

    assert user is None
    assert error == "already_redeemed"
    # must not have gone looking for the code, let alone updated anything
    assert mock_cur.execute.call_count == 1


def test_redeem_rejects_unknown_code():
    user_row = {"access_code_id": None}
    mock_conn, mock_cur = _mock_conn([user_row, None], rowcount=1)

    with patch("api.services.access_code_service._get_conn", return_value=mock_conn):
        user, error = AccessCodeService.redeem(1, "NOTREAL")

    assert user is None
    assert error == "invalid_code"


def test_redeem_rejects_expired_code():
    from datetime import datetime, timedelta
    user_row = {"access_code_id": None}
    access_code_row = {"id": 10, "expires_at": datetime.utcnow() - timedelta(days=1), "max_redemptions": None}
    mock_conn, mock_cur = _mock_conn([user_row, access_code_row], rowcount=1)

    with patch("api.services.access_code_service._get_conn", return_value=mock_conn):
        user, error = AccessCodeService.redeem(1, "OLDCODE")

    assert user is None
    assert error == "expired_code"


def test_redeem_at_capacity_is_race_safe():
    """The redemption-count bump is a conditional UPDATE (WHERE redemption_count < max_redemptions),
    so a full code reports 0 rows affected even if the earlier SELECT looked like it had room --
    this is what prevents two concurrent redemptions from both slipping through."""
    user_row = {"access_code_id": None}
    access_code_row = {"id": 10, "expires_at": None, "max_redemptions": 5}
    mock_conn, mock_cur = _mock_conn([user_row, access_code_row], rowcount=0)  # UPDATE affected 0 rows

    with patch("api.services.access_code_service._get_conn", return_value=mock_conn):
        user, error = AccessCodeService.redeem(1, "FULLCODE")

    assert user is None
    assert error == "code_fully_redeemed"
    # never reached the users UPDATE
    assert mock_cur.execute.call_count == 3
