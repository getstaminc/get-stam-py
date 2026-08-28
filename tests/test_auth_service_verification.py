"""Unit coverage for AuthService's login-code verification (real service logic, mocked DB
connection -- not just route-level mocking of AuthService itself)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from api.services.auth_service import AuthService, _hash_code


def _mock_conn(select_row, update_row=None):
    """Standing in for `with _get_conn() as conn: with conn.cursor() as cur:`. The first
    fetchone() (the SELECT) returns select_row; a subsequent fetchone() (the UPDATE ...
    RETURNING on success) returns update_row."""
    mock_cur = MagicMock()
    mock_cur.fetchone.side_effect = [select_row, update_row] if update_row is not None else [select_row]
    mock_cur.__enter__.return_value = mock_cur
    mock_cur.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    return mock_conn, mock_cur


def _row(code="123456", attempts=0, expires_in=timedelta(minutes=5), email_verified_at=None):
    return {
        "id": 1,
        "email": "a@example.com",
        "login_code_hash": _hash_code(code),
        "login_code_expires_at": datetime.now(timezone.utc) + expires_in,
        "login_code_attempts": attempts,
        "email_verified_at": email_verified_at,
    }


def test_verify_code_wrong_code_increments_attempts_and_fails():
    row = _row()
    mock_conn, mock_cur = _mock_conn(row)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, error, is_first = AuthService.verify_code("a@example.com", "000000")

    assert user is None
    assert error == "invalid_code"
    assert is_first is False
    mock_cur.execute.assert_any_call(
        "UPDATE users SET login_code_attempts = login_code_attempts + 1 WHERE id = %s", (1,)
    )


def test_verify_code_expired_returns_error():
    row = _row(expires_in=timedelta(minutes=-1))
    mock_conn, _ = _mock_conn(row)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, error, is_first = AuthService.verify_code("a@example.com", "123456")

    assert user is None
    assert error == "expired_code"
    assert is_first is False


def test_verify_code_too_many_attempts_returns_error():
    row = _row(attempts=5)
    mock_conn, _ = _mock_conn(row)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, error, is_first = AuthService.verify_code("a@example.com", "123456")

    assert user is None
    assert error == "too_many_attempts"
    assert is_first is False


def test_verify_code_success_first_time_reports_first_verification():
    row = _row(email_verified_at=None)
    updated = {**row, "login_code_hash": None, "login_code_expires_at": None, "login_code_attempts": 0,
               "email_verified_at": "2026-08-25T00:00:00+00:00"}
    mock_conn, _ = _mock_conn(row, update_row=updated)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, error, is_first = AuthService.verify_code("a@example.com", "123456")

    assert error is None
    assert user["email"] == "a@example.com"
    assert is_first is True


def test_verify_code_success_returning_user_is_not_first_verification():
    row = _row(email_verified_at="2026-08-01T00:00:00+00:00")
    updated = {**row, "login_code_hash": None, "login_code_expires_at": None, "login_code_attempts": 0}
    mock_conn, _ = _mock_conn(row, update_row=updated)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, error, is_first = AuthService.verify_code("a@example.com", "123456")

    assert error is None
    assert is_first is False


def test_verify_code_unknown_email_returns_invalid_code():
    mock_conn, _ = _mock_conn(None)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, error, is_first = AuthService.verify_code("unknown@example.com", "123456")

    assert user is None
    assert error == "invalid_code"
    assert is_first is False
