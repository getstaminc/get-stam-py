"""Unit coverage for AuthService.request_code's require_existing gate (real service logic,
mocked DB connection) -- the "Log In" entry point uses require_existing=True so a user who
mistypes their email doesn't get silently signed up for a fresh free account under it."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from api.services.auth_service import AuthService, CODE_MAX_AGE_SECONDS


def _mock_conn(row):
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = row
    mock_cur.__enter__.return_value = mock_cur
    mock_cur.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    return mock_conn, mock_cur


def test_require_existing_with_unknown_email_returns_account_not_found():
    mock_conn, mock_cur = _mock_conn(None)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, code, error = AuthService.request_code("nobody@example.com", require_existing=True)

    assert user is None
    assert code is None
    assert error == "account_not_found"
    # A resend-cooldown SELECT runs first, then the UPDATE -- but no INSERT should ever
    # fire when require_existing=True
    executed_sql = [c[0][0] for c in mock_cur.execute.call_args_list]
    assert any("UPDATE users" in sql for sql in executed_sql)
    assert not any("INSERT INTO users" in sql for sql in executed_sql)


def test_require_existing_with_known_email_succeeds():
    row = {"id": 1, "email": "a@example.com"}
    mock_conn, mock_cur = _mock_conn(row)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, code, error = AuthService.request_code("a@example.com", require_existing=True)

    assert error is None
    assert user["email"] == "a@example.com"
    assert code is not None and len(code) == 6


def test_signup_path_still_auto_creates_without_require_existing():
    row = {"id": 1, "email": "new@example.com"}
    mock_conn, mock_cur = _mock_conn(row)
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, code, error = AuthService.request_code("new@example.com", intent="trial")

    assert error is None
    assert user["email"] == "new@example.com"
    assert "INSERT INTO users" in mock_cur.execute.call_args[0][0]


def test_resend_within_cooldown_is_rejected():
    """A code issued seconds ago must block a fresh request for the same address, so the
    per-IP limiter can't be sidestepped with rotating IPs to mailbomb / brute-force."""
    just_issued_exp = datetime.now(timezone.utc) + timedelta(seconds=CODE_MAX_AGE_SECONDS - 5)
    mock_conn, mock_cur = _mock_conn({"login_code_expires_at": just_issued_exp})
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, code, error = AuthService.request_code("a@example.com")

    assert error == "rate_limited"
    assert user is None and code is None
    # Only the cooldown SELECT ran -- no UPDATE/INSERT
    executed_sql = [c[0][0] for c in mock_cur.execute.call_args_list]
    assert all("SELECT" in sql for sql in executed_sql)


def test_resend_after_cooldown_is_allowed():
    stale_exp = datetime.now(timezone.utc) + timedelta(seconds=CODE_MAX_AGE_SECONDS - 120)
    mock_conn, mock_cur = _mock_conn(
        {"id": 1, "email": "a@example.com", "login_code_expires_at": stale_exp}
    )
    with patch("api.services.auth_service._get_conn", return_value=mock_conn):
        user, code, error = AuthService.request_code("a@example.com", require_existing=True)

    assert error is None
    assert code is not None and len(code) == 6
