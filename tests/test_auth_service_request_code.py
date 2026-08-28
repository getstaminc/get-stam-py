"""Unit coverage for AuthService.request_code's require_existing gate (real service logic,
mocked DB connection) -- the "Log In" entry point uses require_existing=True so a user who
mistypes their email doesn't get silently signed up for a fresh free account under it."""
from unittest.mock import MagicMock, patch

from api.services.auth_service import AuthService


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
    # Only the UPDATE ran -- no INSERT should ever fire when require_existing=True
    assert mock_cur.execute.call_count == 1
    assert "UPDATE users" in mock_cur.execute.call_args[0][0]


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
