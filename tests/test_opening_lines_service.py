"""Coverage for OpeningLinesService — the read/write layer for cached opening-line
snapshots. DB access is mocked throughout; this never touches a real database."""
from unittest.mock import MagicMock, patch

from api.services.opening_lines_service import OpeningLinesService


def _mock_conn(fetchall_return=None, fetchone_return=None):
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = fetchall_return or []
    mock_cur.fetchone.return_value = fetchone_return
    mock_cur.__enter__.return_value = mock_cur
    mock_cur.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    return mock_conn, mock_cur


def test_get_opening_lines_returns_empty_dict_for_no_event_ids():
    assert OpeningLinesService.get_opening_lines("americanfootball_nfl", []) == {}


def test_get_opening_lines_keys_results_by_event_id():
    rows = [
        {"odds_event_id": "evt1", "home_spread_point": -3.0},
        {"odds_event_id": "evt2", "home_spread_point": 7.0},
    ]
    mock_conn, mock_cur = _mock_conn(fetchall_return=rows)

    with patch("api.services.opening_lines_service._get_conn", return_value=mock_conn):
        result = OpeningLinesService.get_opening_lines("americanfootball_nfl", ["evt1", "evt2"])

    assert result["evt1"]["home_spread_point"] == -3.0
    assert result["evt2"]["home_spread_point"] == 7.0
    query_args = mock_cur.execute.call_args[0][1]
    assert query_args == ("americanfootball_nfl", ["evt1", "evt2"])


def test_has_opening_line_true_when_row_exists():
    mock_conn, _ = _mock_conn(fetchone_return={"exists": 1})
    with patch("api.services.opening_lines_service._get_conn", return_value=mock_conn):
        assert OpeningLinesService.has_opening_line("baseball_mlb", "evt1") is True


def test_has_opening_line_false_when_no_row():
    mock_conn, _ = _mock_conn(fetchone_return=None)
    with patch("api.services.opening_lines_service._get_conn", return_value=mock_conn):
        assert OpeningLinesService.has_opening_line("baseball_mlb", "evt1") is False


def test_save_opening_line_inserts_with_on_conflict_do_nothing():
    mock_conn, mock_cur = _mock_conn()
    with patch("api.services.opening_lines_service._get_conn", return_value=mock_conn):
        OpeningLinesService.save_opening_line(
            "americanfootball_nfl", "evt1", "Chicago Bears", "New England Patriots",
            "2026-10-26T18:15:00Z", "2026-10-14T12:00:00Z",
            {"home_spread_point": -3.0, "home_spread_price": -105, "away_spread_point": 3.0,
             "away_spread_price": -118, "home_moneyline": -155, "away_moneyline": 130,
             "total_point": 47.5, "over_price": -110, "under_price": -115},
        )

    sql, params = mock_cur.execute.call_args[0]
    assert "ON CONFLICT (sport, odds_event_id) DO NOTHING" in sql
    assert params[0] == "americanfootball_nfl"
    assert params[1] == "evt1"
    mock_conn.commit.assert_called_once()
