"""Unit coverage for the pure parsing/scan logic in jobs/capture_opening_lines.py,
mirroring how tests/test_nhl_odds_import_parsing.py covers that job's pure parser.
Real network calls and DB access are never made here — a handful of tests below
exercise capture_for_sport's per-game orchestration (memoized snapshot fetching,
per-game failure isolation), but always with get_upcoming_games_and_current_odds,
get_historical_odds_at_time, and OpeningLinesService mocked out."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from jobs.capture_opening_lines import (
    parse_draftkings_markets,
    find_opening_snapshot,
    capture_for_sport,
)


FIXTURE_ODDS_GAME = {
    "id": "evt1",
    "home_team": "Chicago Bears",
    "away_team": "New England Patriots",
    "bookmakers": [
        {
            "key": "draftkings",
            "markets": [
                {"key": "h2h", "outcomes": [
                    {"name": "Chicago Bears", "price": -155},
                    {"name": "New England Patriots", "price": 130},
                ]},
                {"key": "spreads", "outcomes": [
                    {"name": "Chicago Bears", "point": -3.0, "price": -105},
                    {"name": "New England Patriots", "point": 3.0, "price": -118},
                ]},
                {"key": "totals", "outcomes": [
                    {"name": "Over", "point": 47.5, "price": -110},
                    {"name": "Under", "point": 47.5, "price": -115},
                ]},
            ],
        }
    ],
}


def test_parse_draftkings_markets_extracts_spread_total_moneyline():
    markets = parse_draftkings_markets(FIXTURE_ODDS_GAME)
    assert markets["home_spread_point"] == -3.0
    assert markets["home_spread_price"] == -105
    assert markets["away_spread_point"] == 3.0
    assert markets["away_moneyline"] == 130
    assert markets["home_moneyline"] == -155
    assert markets["total_point"] == 47.5
    assert markets["over_price"] == -110
    assert markets["under_price"] == -115


def test_parse_draftkings_markets_returns_none_without_draftkings():
    game = {"id": "evt1", "home_team": "A", "away_team": "B",
             "bookmakers": [{"key": "fanduel", "markets": []}]}
    assert parse_draftkings_markets(game) is None


def test_parse_draftkings_markets_returns_none_with_no_bookmakers():
    assert parse_draftkings_markets({"id": "evt1", "bookmakers": []}) is None


def test_find_opening_snapshot_returns_first_snapshot_with_odds():
    commence_time = datetime(2026, 10, 26, 18, 15, tzinfo=timezone.utc)
    calls = []

    def fake_fetch(snapshot_time):
        calls.append(snapshot_time)
        if len(calls) < 3:  # market only actually opens on the 3rd scanned snapshot
            return [], None
        return [FIXTURE_ODDS_GAME], "2026-10-14T12:00:00Z"

    markets, snapshot_time = find_opening_snapshot(
        "evt1", commence_time, scan_days_back=21, scan_step_hours=24,
        fetch_historical_odds=fake_fetch,
    )

    assert markets["home_spread_point"] == -3.0
    assert snapshot_time == "2026-10-14T12:00:00Z"
    assert len(calls) == 3
    assert calls[0] == commence_time - timedelta(days=21)
    assert calls[1] == commence_time - timedelta(days=20)
    assert calls[2] == commence_time - timedelta(days=19)


def test_find_opening_snapshot_returns_none_when_never_found():
    commence_time = datetime(2026, 10, 26, 18, 15, tzinfo=timezone.utc)

    markets, snapshot_time = find_opening_snapshot(
        "evt1", commence_time, scan_days_back=3, scan_step_hours=24,
        fetch_historical_odds=lambda snapshot_time: ([], None),
    )

    assert markets is None
    assert snapshot_time is None


def test_find_opening_snapshot_ignores_events_with_different_id():
    commence_time = datetime(2026, 10, 26, 18, 15, tzinfo=timezone.utc)

    def fake_fetch(snapshot_time):
        return [{**FIXTURE_ODDS_GAME, "id": "some_other_event"}], "2026-10-14T12:00:00Z"

    markets, snapshot_time = find_opening_snapshot(
        "evt1", commence_time, scan_days_back=3, scan_step_hours=24,
        fetch_historical_odds=fake_fetch,
    )

    assert markets is None
    assert snapshot_time is None


def test_find_opening_snapshot_never_scans_past_now():
    """A game that just entered the lookahead window has a scan grid running almost
    entirely through the future. The scan must never request a timestamp later than
    `now` — the Historical Odds API can clamp a future-dated request to its latest
    (i.e. current) snapshot, which would otherwise be mistaken for the opening line
    and, since opening lines are write-once, could never be corrected."""
    now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    commence_time = now + timedelta(hours=2)  # kickoff is imminent
    calls = []

    def fake_fetch(snapshot_time):
        calls.append(snapshot_time)
        return [], None  # market never posts in this scenario

    markets, snapshot_time = find_opening_snapshot(
        "evt1", commence_time, scan_days_back=21, scan_step_hours=24,
        fetch_historical_odds=fake_fetch, now=now,
    )

    assert markets is None
    assert calls, "expected the scan to run at least one (past) grid point"
    assert all(c < now for c in calls)
    assert commence_time not in calls


def test_find_opening_snapshot_unclamped_when_commence_time_already_past():
    """When commence_time is already in the past (the normal case for most games),
    clamping to `now` must not change behavior from the original unclamped scan."""
    now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    commence_time = datetime(2026, 10, 14, 18, 15, tzinfo=timezone.utc)  # well before now
    calls = []

    def fake_fetch(snapshot_time):
        calls.append(snapshot_time)
        if len(calls) < 3:
            return [], None
        return [FIXTURE_ODDS_GAME], "2026-10-02T12:00:00Z"

    markets, snapshot_time = find_opening_snapshot(
        "evt1", commence_time, scan_days_back=21, scan_step_hours=24,
        fetch_historical_odds=fake_fetch, now=now,
    )

    assert markets["home_spread_point"] == -3.0
    assert len(calls) == 3


FIXTURE_ODDS_GAME_2 = {
    "id": "evt2",
    "home_team": "Dallas Cowboys",
    "away_team": "Green Bay Packers",
    "bookmakers": [
        {
            "key": "draftkings",
            "markets": [
                {"key": "h2h", "outcomes": [
                    {"name": "Dallas Cowboys", "price": -120},
                    {"name": "Green Bay Packers", "price": 110},
                ]},
                {"key": "spreads", "outcomes": [
                    {"name": "Dallas Cowboys", "point": -1.5, "price": -110},
                    {"name": "Green Bay Packers", "point": 1.5, "price": -110},
                ]},
                {"key": "totals", "outcomes": [
                    {"name": "Over", "point": 44.5, "price": -105},
                    {"name": "Under", "point": 44.5, "price": -115},
                ]},
            ],
        }
    ],
}


def test_capture_for_sport_memoizes_identical_snapshot_requests_across_games():
    """Two games sharing an identical commence_time (e.g. the Sunday 1pm NFL slate)
    have identical scan grids. Without memoization, each game independently re-fetches
    every scan point -> 2x the calls. With a cache shared across the sport's games,
    the second game's scan should hit the cache for every point the first game
    already fetched, so the underlying fetch function is called once per unique
    (sport_key, snapshot_time), not once per (game, snapshot_time)."""
    commence_time_str = "2020-01-10T18:15:00Z"
    commence_time = datetime(2020, 1, 10, 18, 15, tzinfo=timezone.utc)
    opening_cursor = commence_time - timedelta(days=1)  # the 3rd of 3 scan points

    game1 = {"id": "evt1", "home_team": "Chicago Bears", "away_team": "New England Patriots",
             "commence_time": commence_time_str, "completed": False}
    game2 = {"id": "evt2", "home_team": "Dallas Cowboys", "away_team": "Green Bay Packers",
             "commence_time": commence_time_str, "completed": False}

    call_log = []

    def fake_get_historical_odds_at_time(sport_key, snapshot_time):
        call_log.append(snapshot_time)
        if snapshot_time == opening_cursor:
            return [FIXTURE_ODDS_GAME, FIXTURE_ODDS_GAME_2], "2020-01-09T18:15:00Z"
        return [], None

    config = {"lookahead_days": 21, "scan_days_back": 3, "scan_step_hours": 24}

    with patch("jobs.capture_opening_lines.get_upcoming_games_and_current_odds",
               return_value=([game1, game2], {"evt1": FIXTURE_ODDS_GAME, "evt2": FIXTURE_ODDS_GAME_2})), \
         patch("jobs.capture_opening_lines.OpeningLinesService.has_opening_line", return_value=False), \
         patch("jobs.capture_opening_lines.OpeningLinesService.save_opening_line") as mock_save, \
         patch("jobs.capture_opening_lines.get_historical_odds_at_time",
               side_effect=fake_get_historical_odds_at_time):
        captured = capture_for_sport("americanfootball_nfl", config, sleep_between_calls=0)

    assert captured == 2
    assert mock_save.call_count == 2
    # 3 unique timestamps total, shared across both games — not 6 (3 per game).
    assert len(call_log) == 3


def test_capture_for_sport_continues_after_per_game_error():
    """One malformed game / unexpected error must not abort the whole batch — every
    other game in the sport's list should still be attempted."""
    commence_time_str = "2020-01-10T18:15:00Z"

    game1 = {"id": "evt1", "home_team": "A", "away_team": "B",
             "commence_time": commence_time_str, "completed": False}
    game2 = {"id": "evt2", "home_team": "C", "away_team": "D",
             "commence_time": commence_time_str, "completed": False}

    config = {"lookahead_days": 21, "scan_days_back": 3, "scan_step_hours": 24}

    has_call_log = []

    def fake_has_opening_line(sport_key, event_id):
        has_call_log.append(event_id)
        if event_id == "evt1":
            raise RuntimeError("boom")
        return False

    with patch("jobs.capture_opening_lines.get_upcoming_games_and_current_odds",
               return_value=([game1, game2], {"evt1": {}, "evt2": {}})), \
         patch("jobs.capture_opening_lines.OpeningLinesService.has_opening_line",
               side_effect=fake_has_opening_line), \
         patch("jobs.capture_opening_lines.OpeningLinesService.save_opening_line") as mock_save, \
         patch("jobs.capture_opening_lines.get_historical_odds_at_time",
               return_value=([], None)):
        captured = capture_for_sport("americanfootball_nfl", config, sleep_between_calls=0)

    # evt1 raised inside has_opening_line and was skipped; evt2 was still attempted
    # (it finds no historical snapshot here, so nothing gets captured for it either).
    assert has_call_log == ["evt1", "evt2"]
    assert captured == 0
    mock_save.assert_not_called()


def test_main_attempts_every_sport_even_when_one_fails_and_exits_nonzero():
    """main() must not let one sport's failure stop the remaining sports from
    running, and must surface a non-zero exit code so Heroku Scheduler can see a
    partial failure."""
    import jobs.capture_opening_lines as job_module

    def fake_capture_for_sport(sport_key, config):
        if sport_key == "americanfootball_nfl":
            raise RuntimeError("boom")
        return 0

    with patch.object(job_module, "capture_for_sport", side_effect=fake_capture_for_sport) as mock_capture, \
         patch.object(job_module, "sys") as mock_sys:
        job_module.main()

    assert mock_capture.call_count == len(job_module.SPORT_CONFIGS)
    mock_sys.exit.assert_called_once_with(1)
