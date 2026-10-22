"""Coverage for NFLService.get_team_records — the batch win/loss/tie computation
backing the team record shown under each team name in GameOdds."""
from datetime import date
from unittest.mock import MagicMock, patch

from api.services.historical.nfl_service import NFLService


def _mock_conn(fetchall_return=None):
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = fetchall_return or []
    mock_cur.__enter__.return_value = mock_cur
    mock_cur.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    return mock_conn, mock_cur


def test_get_team_records_returns_empty_dict_for_no_team_names():
    assert NFLService.get_team_records([]) == {}


def test_get_team_records_maps_wins_losses_ties_by_team():
    rows = [
        {"team": "Saints", "wins": 4, "losses": 2, "ties": 0},
        {"team": "Steelers", "wins": 3, "losses": 3, "ties": 1},
    ]
    mock_conn, mock_cur = _mock_conn(fetchall_return=rows)

    with patch.object(NFLService, "_get_connection", return_value=mock_conn):
        result = NFLService.get_team_records(["Saints", "Steelers"])

    assert result["Saints"] == {"wins": 4, "losses": 2, "ties": 0}
    assert result["Steelers"] == {"wins": 3, "losses": 3, "ties": 1}


def test_get_team_records_omits_teams_with_no_games_this_season():
    mock_conn, mock_cur = _mock_conn(fetchall_return=[{"team": "Saints", "wins": 1, "losses": 0, "ties": 0}])

    with patch.object(NFLService, "_get_connection", return_value=mock_conn):
        result = NFLService.get_team_records(["Saints", "Panthers"])

    assert "Saints" in result
    assert "Panthers" not in result


def test_get_team_records_queries_both_home_and_away_with_season_bounds():
    mock_conn, mock_cur = _mock_conn(fetchall_return=[])
    season_start = date(2026, 8, 1)
    as_of_date = date(2026, 10, 22)

    with patch.object(NFLService, "_get_connection", return_value=mock_conn):
        NFLService.get_team_records(["Saints"], season_start=season_start, as_of_date=as_of_date)

    sql, params = mock_cur.execute.call_args[0]
    assert "home_team_name" in sql and "away_team_name" in sql
    # team list passed twice (once for the home-side leg, once for the away-side leg),
    # with the same season bounds applied to both.
    assert params == (["Saints"], season_start, as_of_date, ["Saints"], season_start, as_of_date)


def test_get_team_records_defaults_season_start_to_august_of_the_current_nfl_season():
    mock_conn, mock_cur = _mock_conn(fetchall_return=[])

    with patch.object(NFLService, "_get_connection", return_value=mock_conn), \
         patch("api.services.historical.nfl_service.date") as mock_date:
        mock_date.today.return_value = date(2026, 10, 22)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        NFLService.get_team_records(["Saints"])

    _, params = mock_cur.execute.call_args[0]
    assert params[1] == date(2026, 8, 1)


def test_get_team_records_uses_prior_august_for_early_season_dates():
    """A January date (still mid-season from the previous August) should use
    last year's August 1, not the current calendar year's."""
    mock_conn, mock_cur = _mock_conn(fetchall_return=[])

    with patch.object(NFLService, "_get_connection", return_value=mock_conn), \
         patch("api.services.historical.nfl_service.date") as mock_date:
        mock_date.today.return_value = date(2027, 1, 15)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        NFLService.get_team_records(["Saints"])

    _, params = mock_cur.execute.call_args[0]
    assert params[1] == date(2026, 8, 1)
