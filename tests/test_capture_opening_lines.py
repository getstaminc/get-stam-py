"""Unit coverage for the pure parsing/scan logic in jobs/capture_opening_lines.py.
Network calls and the live-odds/DB-backed orchestration (capture_for_sport) are
intentionally not covered here — only the deterministic logic that decides what
counts as an opening line, mirroring how tests/test_nhl_odds_import_parsing.py only
covers that job's pure parser, not its HTTP/DB orchestration."""
from datetime import datetime, timedelta, timezone

from jobs.capture_opening_lines import parse_draftkings_markets, find_opening_snapshot


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
