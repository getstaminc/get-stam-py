# Line Movement (Open vs. Now) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show an ESPN-style "Open vs. Now" line comparison (spread, total, moneyline) for NFL, NHL, MLB, and NCAAF games.

**Architecture:** A nightly job scans backward from kickoff using the-odds-api.com's Historical Odds API to find each new game's true opening line, caching it write-once in a new `game_opening_lines` table. The existing live-odds API/service layer batch-reads that cache and attaches it to the games it already returns; the frontend renders it as an extra "Open" line wherever current odds already render.

**Tech Stack:** Flask + psycopg2 (reads), SQLAlchemy/Alembic (migration), Python `requests` (Odds API), React + MUI (`GameOdds.tsx`), pytest, Jest/RTL (`react-scripts test`).

**Spec:** `docs/superpowers/specs/2026-10-21-line-movement-design.md`

## Global Constraints

- Sports in scope, stored verbatim as the `sport` column value (the Odds-API
  sport key `GameService` already works with — **not** the short URL key):
  `americanfootball_nfl`, `americanfootball_ncaaf`, `baseball_mlb`, `icehockey_nhl`.
  (The design spec's `nfl`/`nhl`/`mlb`/`ncaaf` shorthand refers to these same four
  sports — see Task 1 note on why the stored value differs from the spec's shorthand.)
- No mass backfill of games already sitting in `nfl_games`/`nhl_games`/`mlb_games`.
  Only upcoming games get captured, going forward from deployment.
- Capture happens **only** in the nightly job — never as a live scan triggered by a
  user request.
- `game_opening_lines` rows are write-once: `ON CONFLICT (sport, odds_event_id) DO
  NOTHING`.
- Scan windows/steps: NFL & NCAAF — 21 days back, 24-hour steps. MLB & NHL — 3 days
  back, 12-hour steps.
- Bookmaker is `draftkings` for all four sports (matches the bookmaker already used
  elsewhere in the codebase for these sports).
- The "Open" row only renders inside `GameOdds.tsx`'s existing pregame block
  (`!isGameOver && !isLive`) — no change to completed/live-game display.

---

## File Structure

- `models/game_opening_line.py` — new SQLAlchemy model (migration support only).
- `models/__init__.py` — register the new model.
- `migrations/versions/<rev>_create_game_opening_lines_table.py` — new table.
- `api/services/opening_lines_service.py` — new: read (`get_opening_lines`,
  `has_opening_line`) and write (`save_opening_line`) against `game_opening_lines`.
- `jobs/capture_opening_lines.py` — new: nightly orchestration + the backward-scan
  logic.
- `api/services/game_service.py` — modified: `get_games_for_date` and
  `get_single_game` attach `opening` to formatted games for in-scope sports.
- `getstam-react/src/types/gameTypes.ts` — modified: new `OpeningLineData` type,
  `opening?` on `GameWithDraw`.
- `getstam-react/src/components/GameOdds.tsx` — modified: render the "Open" row.
- Tests: `tests/test_opening_lines_service.py`,
  `tests/test_capture_opening_lines.py`, `tests/test_game_service_opening_lines.py`,
  `getstam-react/src/components/GameOdds.test.tsx`.

---

### Task 1: Data model — `game_opening_lines` table

**Files:**
- Create: `models/game_opening_line.py`
- Modify: `models/__init__.py`
- Create: `migrations/versions/9d14f3a7c2e8_create_game_opening_lines_table.py`
- Test: `tests/test_game_opening_line_model.py`

**Interfaces:**
- Produces: table `game_opening_lines` with columns `sport`, `odds_event_id`,
  `home_team`, `away_team`, `commence_time`, `opening_snapshot_time`,
  `home_spread_point`, `home_spread_price`, `away_spread_point`,
  `away_spread_price`, `home_moneyline`, `away_moneyline`, `total_point`,
  `over_price`, `under_price`, `created_at`. Unique constraint
  `uq_game_opening_lines_sport_event` on (`sport`, `odds_event_id`). Task 2 reads
  and writes through this schema.

**Note on `sport` values:** `GameService` (see Task 4) already receives and works
with the Odds-API sport key form — `americanfootball_nfl`, `baseball_mlb`,
`icehockey_nhl`, `americanfootball_ncaaf` — not the short `nfl`/`mlb`/`nhl`/`ncaaf`
URL keys the frontend uses before calling `/api/odds/<sportKey>`. Storing that same
long form in `game_opening_lines.sport` avoids an extra translation step (and the bugs
that come with maintaining two parallel sport-key vocabularies) between the capture
job, the read service, and `GameService`.

- [ ] **Step 1: Check the current migration head**

Run: `source venv/bin/activate && DATABASE_URL="postgresql://test:test@localhost/test" python -m alembic heads`
Expected output: `f4d2b8a61c93 (head)` — this is the `down_revision` used below. If a
different head comes back (meaning another migration landed since this plan was
written), use that revision id instead everywhere `f4d2b8a61c93` appears in this task.

- [ ] **Step 2: Write the failing test**

Create `tests/test_game_opening_line_model.py`:

```python
"""Pins the game_opening_lines schema the migration in Task 1 must produce —
no DB needed, this only inspects the SQLAlchemy model's metadata."""
from models.game_opening_line import GameOpeningLine


def test_table_name():
    assert GameOpeningLine.__tablename__ == 'game_opening_lines'


def test_unique_constraint_is_on_sport_and_event_id():
    constraint = next(
        c for c in GameOpeningLine.__table__.constraints
        if c.name == 'uq_game_opening_lines_sport_event'
    )
    assert {col.name for col in constraint.columns} == {'sport', 'odds_event_id'}


def test_has_all_expected_columns():
    column_names = {col.name for col in GameOpeningLine.__table__.columns}
    assert column_names == {
        'id', 'sport', 'odds_event_id', 'home_team', 'away_team', 'commence_time',
        'opening_snapshot_time', 'home_spread_point', 'home_spread_price',
        'away_spread_point', 'away_spread_price', 'home_moneyline', 'away_moneyline',
        'total_point', 'over_price', 'under_price', 'created_at',
    }
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_game_opening_line_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models.game_opening_line'`

- [ ] **Step 4: Write the model**

Create `models/game_opening_line.py`:

```python
from sqlalchemy import Column, Integer, String, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from .base import Base


class GameOpeningLine(Base):
    __tablename__ = 'game_opening_lines'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sport = Column(String(50), nullable=False)
    odds_event_id = Column(String(100), nullable=False)
    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)
    commence_time = Column(TIMESTAMP(timezone=True), nullable=False)
    opening_snapshot_time = Column(TIMESTAMP(timezone=True), nullable=False)
    home_spread_point = Column(Float)
    home_spread_price = Column(Integer)
    away_spread_point = Column(Float)
    away_spread_price = Column(Integer)
    home_moneyline = Column(Integer)
    away_moneyline = Column(Integer)
    total_point = Column(Float)
    over_price = Column(Integer)
    under_price = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('sport', 'odds_event_id', name='uq_game_opening_lines_sport_event'),
    )
```

- [ ] **Step 5: Register the model**

Modify `models/__init__.py` — add, in both the import list and `__all__`:

```python
from .game_opening_line import GameOpeningLine
```

Add `'GameOpeningLine'` to the `__all__` list.

- [ ] **Step 6: Run the test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_game_opening_line_model.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Write the migration**

Create `migrations/versions/9d14f3a7c2e8_create_game_opening_lines_table.py`
(replace `f4d2b8a61c93` in `down_revision` if Step 1 found a different head):

```python
"""create_game_opening_lines_table

Revision ID: 9d14f3a7c2e8
Revises: f4d2b8a61c93
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9d14f3a7c2e8'
down_revision: Union[str, None] = 'f4d2b8a61c93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'game_opening_lines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sport', sa.String(length=50), nullable=False),
        sa.Column('odds_event_id', sa.String(length=100), nullable=False),
        sa.Column('home_team', sa.String(length=100), nullable=False),
        sa.Column('away_team', sa.String(length=100), nullable=False),
        sa.Column('commence_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('opening_snapshot_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('home_spread_point', sa.Float(), nullable=True),
        sa.Column('home_spread_price', sa.Integer(), nullable=True),
        sa.Column('away_spread_point', sa.Float(), nullable=True),
        sa.Column('away_spread_price', sa.Integer(), nullable=True),
        sa.Column('home_moneyline', sa.Integer(), nullable=True),
        sa.Column('away_moneyline', sa.Integer(), nullable=True),
        sa.Column('total_point', sa.Float(), nullable=True),
        sa.Column('over_price', sa.Integer(), nullable=True),
        sa.Column('under_price', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sport', 'odds_event_id', name='uq_game_opening_lines_sport_event'),
    )


def downgrade() -> None:
    op.drop_table('game_opening_lines')
```

- [ ] **Step 8: Verify the migration is a valid head**

Run: `source venv/bin/activate && DATABASE_URL="postgresql://test:test@localhost/test" python -m alembic heads`
Expected: `9d14f3a7c2e8 (head)`

Do **not** run `alembic upgrade head` against production here — this plan doesn't
apply it to any real database. That's a deploy-time step (`alembic upgrade head`,
per this repo's existing migration workflow).

- [ ] **Step 9: Commit**

```bash
git add models/game_opening_line.py models/__init__.py \
  migrations/versions/9d14f3a7c2e8_create_game_opening_lines_table.py \
  tests/test_game_opening_line_model.py
git commit -m "Add game_opening_lines table for line-movement tracking"
```

---

### Task 2: `OpeningLinesService` — read/write layer

**Files:**
- Create: `api/services/opening_lines_service.py`
- Test: `tests/test_opening_lines_service.py`

**Interfaces:**
- Consumes: the `game_opening_lines` table from Task 1.
- Produces: `OpeningLinesService.get_opening_lines(sport: str, event_ids: list[str]) ->
  dict[str, dict]` (keyed by `odds_event_id`; values have the row's non-id columns),
  `OpeningLinesService.has_opening_line(sport: str, event_id: str) -> bool`,
  `OpeningLinesService.save_opening_line(sport: str, event_id: str, home_team: str,
  away_team: str, commence_time: datetime, opening_snapshot_time: datetime, markets:
  dict) -> None`. Task 3 (the job) calls `has_opening_line`/`save_opening_line`. Task
  4 (`GameService`) calls `get_opening_lines`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_opening_lines_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && pytest tests/test_opening_lines_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.services.opening_lines_service'`

- [ ] **Step 3: Write the implementation**

Create `api/services/opening_lines_service.py`:

```python
"""Read/write access to cached opening-line snapshots for line-movement display.
Snapshots are captured once per game by jobs/capture_opening_lines.py — this service
never calls the Odds API itself, only the database."""

import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")


def _get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


class OpeningLinesService:

    @staticmethod
    def get_opening_lines(sport, event_ids):
        """Batch-fetch opening lines for the given event ids.
        Returns {odds_event_id: row_dict} for whichever ids have a captured row."""
        event_ids = [e for e in event_ids if e]
        if not event_ids:
            return {}
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT odds_event_id, home_spread_point, home_spread_price,
                           away_spread_point, away_spread_price, home_moneyline,
                           away_moneyline, total_point, over_price, under_price,
                           opening_snapshot_time
                    FROM game_opening_lines
                    WHERE sport = %s AND odds_event_id = ANY(%s)
                    """,
                    (sport, event_ids),
                )
                rows = cur.fetchall()
        return {row["odds_event_id"]: row for row in rows}

    @staticmethod
    def has_opening_line(sport, event_id):
        """True if an opening line has already been captured for this event."""
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM game_opening_lines WHERE sport = %s AND odds_event_id = %s",
                    (sport, event_id),
                )
                return cur.fetchone() is not None

    @staticmethod
    def save_opening_line(sport, event_id, home_team, away_team, commence_time,
                           opening_snapshot_time, markets):
        """Insert a captured opening line. Write-once: does nothing if a row for
        (sport, event_id) already exists."""
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO game_opening_lines (
                        sport, odds_event_id, home_team, away_team, commence_time,
                        opening_snapshot_time, home_spread_point, home_spread_price,
                        away_spread_point, away_spread_price, home_moneyline,
                        away_moneyline, total_point, over_price, under_price
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (sport, odds_event_id) DO NOTHING
                    """,
                    (
                        sport, event_id, home_team, away_team, commence_time,
                        opening_snapshot_time,
                        markets.get("home_spread_point"), markets.get("home_spread_price"),
                        markets.get("away_spread_point"), markets.get("away_spread_price"),
                        markets.get("home_moneyline"), markets.get("away_moneyline"),
                        markets.get("total_point"), markets.get("over_price"),
                        markets.get("under_price"),
                    ),
                )
            conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_opening_lines_service.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add api/services/opening_lines_service.py tests/test_opening_lines_service.py
git commit -m "Add OpeningLinesService read/write layer for opening-line cache"
```

---

### Task 3: Nightly capture job

**Files:**
- Create: `jobs/capture_opening_lines.py`
- Test: `tests/test_capture_opening_lines.py`

**Interfaces:**
- Consumes: `get_odds_data(sport_key, date)` from `api/external_requests/odds_api.py`
  (already exists — returns `(scores, odds)`), `OpeningLinesService.has_opening_line`
  / `.save_opening_line` from Task 2.
- Produces: `parse_draftkings_markets(odds_game: dict) -> dict | None`,
  `find_opening_snapshot(event_id: str, commence_time: datetime, scan_days_back: int,
  scan_step_hours: int, fetch_historical_odds: Callable) -> tuple[dict | None, str |
  None]`, `capture_for_sport(sport_key: str, config: dict) -> int`, `main()`. Nothing
  later in this plan imports from this job — it's the end of the chain — but these
  names matter for anyone maintaining it later.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_capture_opening_lines.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && pytest tests/test_capture_opening_lines.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jobs.capture_opening_lines'`

- [ ] **Step 3: Write the implementation**

Create `jobs/capture_opening_lines.py`:

```python
"""
Nightly job: capture each new NFL/NCAAF/MLB/NHL game's opening line by scanning
backward from kickoff with the Historical Odds API, stopping at the first snapshot
where the market has posted a price. Safe to re-run — already-captured games (and
games whose market hasn't opened yet) are skipped.

Run nightly via Heroku Scheduler:
  python jobs/capture_opening_lines.py
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(override=True)

from api.external_requests.odds_api import get_odds_data
from api.services.opening_lines_service import OpeningLinesService

ODDS_API_KEY = os.getenv("ODDS_API_KEY")

# Keys are the Odds-API sport key GameService already uses — stored verbatim as
# `sport` in game_opening_lines, see Task 1's note on why.
SPORT_CONFIGS = {
    "americanfootball_nfl": {"lookahead_days": 21, "scan_days_back": 21, "scan_step_hours": 24},
    "americanfootball_ncaaf": {"lookahead_days": 21, "scan_days_back": 21, "scan_step_hours": 24},
    "baseball_mlb": {"lookahead_days": 3, "scan_days_back": 3, "scan_step_hours": 12},
    "icehockey_nhl": {"lookahead_days": 3, "scan_days_back": 3, "scan_step_hours": 12},
}


def get_upcoming_games_and_current_odds(sport_key, lookahead_days):
    """Return (upcoming_games, odds_by_event_id) for games starting in the next
    `lookahead_days`. `odds_by_event_id` only contains entries for games that
    currently have posted draftkings odds (i.e. whose market has opened)."""
    scores, odds = get_odds_data(sport_key, None)
    if scores is None:
        return [], {}

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=lookahead_days)
    upcoming = []
    for game in scores:
        if game.get("completed"):
            continue
        commence = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
        if now <= commence <= horizon:
            upcoming.append(game)

    odds_by_event_id = {o["id"]: o for o in (odds or []) if o.get("bookmakers")}
    return upcoming, odds_by_event_id


def parse_draftkings_markets(odds_game):
    """Extract spread/total/moneyline values from an odds-api game's draftkings
    bookmaker entry. Returns None if draftkings hasn't posted any markets for it."""
    if not odds_game or not odds_game.get("bookmakers"):
        return None

    draftkings = next((b for b in odds_game["bookmakers"] if b["key"] == "draftkings"), None)
    if not draftkings or not draftkings.get("markets"):
        return None

    home_team = odds_game["home_team"]
    away_team = odds_game["away_team"]
    result = {
        "home_spread_point": None, "home_spread_price": None,
        "away_spread_point": None, "away_spread_price": None,
        "home_moneyline": None, "away_moneyline": None,
        "total_point": None, "over_price": None, "under_price": None,
    }

    for market in draftkings["markets"]:
        if market["key"] == "h2h":
            for outcome in market["outcomes"]:
                if outcome["name"] == home_team:
                    result["home_moneyline"] = outcome.get("price")
                elif outcome["name"] == away_team:
                    result["away_moneyline"] = outcome.get("price")
        elif market["key"] == "spreads":
            for outcome in market["outcomes"]:
                if outcome["name"] == home_team:
                    result["home_spread_point"] = outcome.get("point")
                    result["home_spread_price"] = outcome.get("price")
                elif outcome["name"] == away_team:
                    result["away_spread_point"] = outcome.get("point")
                    result["away_spread_price"] = outcome.get("price")
        elif market["key"] == "totals":
            for outcome in market["outcomes"]:
                if outcome["name"] == "Over":
                    result["total_point"] = outcome.get("point")
                    result["over_price"] = outcome.get("price")
                elif outcome["name"] == "Under":
                    result["under_price"] = outcome.get("price")

    if all(v is None for v in result.values()):
        return None
    return result


def get_historical_odds_at_time(sport_key, snapshot_time, retries=3, delay=1):
    """Fetch a historical odds snapshot for `sport_key` at or before `snapshot_time`
    (a UTC datetime). Returns (events, actual_snapshot_timestamp)."""
    time_str = snapshot_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = (
        f"https://api.the-odds-api.com/v4/historical/sports/{sport_key}/odds/"
        f"?apiKey={ODDS_API_KEY}&regions=us&bookmakers=draftkings"
        f"&markets=h2h,spreads,totals&oddsFormat=american&date={time_str}"
    )
    for attempt in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            payload = response.json()
            return payload.get("data", []), payload.get("timestamp", time_str)
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching historical odds (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    return [], None


def find_opening_snapshot(event_id, commence_time, scan_days_back, scan_step_hours,
                           fetch_historical_odds):
    """Scan forward from (commence_time - scan_days_back) toward commence_time in
    scan_step_hours increments. Returns (markets_dict, snapshot_time) for the first
    snapshot where this event has draftkings odds — i.e. the opening line. Returns
    (None, None) if no snapshot in the window has odds for this event."""
    cursor = commence_time - timedelta(days=scan_days_back)
    while cursor < commence_time:
        data, actual_timestamp = fetch_historical_odds(cursor)
        game = next((g for g in data if g.get("id") == event_id), None)
        markets = parse_draftkings_markets(game) if game else None
        if markets:
            return markets, actual_timestamp
        cursor += timedelta(hours=scan_step_hours)
    return None, None


def capture_for_sport(sport_key, config, sleep_between_calls=0.5):
    """Capture opening lines for every not-yet-captured, already-open game in the
    given sport's lookahead window. Returns the count of games captured."""
    print(f"\n=== {sport_key} ===")
    upcoming_games, odds_by_event_id = get_upcoming_games_and_current_odds(
        sport_key, config["lookahead_days"]
    )
    print(f"{len(upcoming_games)} upcoming game(s) in the next {config['lookahead_days']} day(s)")

    captured = 0
    for game in upcoming_games:
        event_id = game["id"]

        if OpeningLinesService.has_opening_line(sport_key, event_id):
            continue
        if event_id not in odds_by_event_id:
            continue  # market hasn't opened yet — picked up on a future night

        commence_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))

        def fetch(snapshot_time, _sport_key=sport_key, _sleep=sleep_between_calls):
            time.sleep(_sleep)
            return get_historical_odds_at_time(_sport_key, snapshot_time)

        markets, snapshot_time_str = find_opening_snapshot(
            event_id, commence_time, config["scan_days_back"], config["scan_step_hours"], fetch
        )
        if not markets:
            print(f"  No historical snapshot found yet for {game['home_team']} vs {game['away_team']}")
            continue

        snapshot_time = (
            datetime.fromisoformat(snapshot_time_str.replace("Z", "+00:00"))
            if isinstance(snapshot_time_str, str) else commence_time
        )
        OpeningLinesService.save_opening_line(
            sport_key, event_id, game["home_team"], game["away_team"],
            commence_time, snapshot_time, markets,
        )
        captured += 1
        print(f"  Captured opening line: {game['home_team']} vs {game['away_team']} (opened {snapshot_time})")

    print(f"{sport_key}: captured {captured} new opening line(s)")
    return captured


def main():
    total = 0
    for sport_key, config in SPORT_CONFIGS.items():
        total += capture_for_sport(sport_key, config)
    print(f"\nDone. Captured {total} opening line(s) across all sports.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_capture_opening_lines.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add jobs/capture_opening_lines.py tests/test_capture_opening_lines.py
git commit -m "Add nightly opening-line capture job"
```

---

### Task 4: Wire `GameService` to attach opening lines

**Files:**
- Modify: `api/services/game_service.py`
- Test: `tests/test_game_service_opening_lines.py`

**Interfaces:**
- Consumes: `OpeningLinesService.get_opening_lines(sport, event_ids)` from Task 2.
- Produces: `GameService.get_games_for_date` and `GameService.get_single_game` now
  attach an `opening` key (shape below) to each formatted game, for sports in
  `OPENING_LINE_SPORTS`. This is what Task 6 (`GameOdds.tsx`) reads via
  `game.opening`.

```
opening: {
  home: { spread_point, spread_price, h2h },
  away: { spread_point, spread_price, h2h },
  totals: { over_point, over_price, under_point, under_price },
  snapshot_time: "<iso timestamp>" | None
}
```

- [ ] **Step 1: Write the failing tests**

Create `tests/test_game_service_opening_lines.py`:

```python
"""Coverage for GameService attaching cached opening-line data to formatted games —
for the sports that have it, and specifically not for the ones that don't."""
from unittest.mock import patch

from api.services.game_service import GameService


FAKE_SCORES = [
    {
        "id": "evt1",
        "sport_key": "americanfootball_nfl",
        "home_team": "Chicago Bears",
        "away_team": "New England Patriots",
        "commence_time": "2026-10-26T18:15:00Z",
        "completed": False,
        "scores": None,
    }
]
FAKE_ODDS = [{"id": "evt1", "bookmakers": []}]

FAKE_OPENING_ROW = {
    "odds_event_id": "evt1",
    "home_spread_point": -3.0,
    "home_spread_price": -105,
    "away_spread_point": 3.0,
    "away_spread_price": -118,
    "home_moneyline": -155,
    "away_moneyline": 130,
    "total_point": 47.5,
    "over_price": -110,
    "under_price": -115,
    "opening_snapshot_time": None,
}


def test_get_games_for_date_attaches_opening_line_for_nfl():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines",
               return_value={"evt1": FAKE_OPENING_ROW}) as mock_get_opening:
        result, error = GameService.get_games_for_date("americanfootball_nfl")

    assert error is None
    game = result["games"][0]
    assert game["opening"]["home"]["spread_point"] == -3.0
    assert game["opening"]["away"]["h2h"] == 130
    assert game["opening"]["totals"]["over_point"] == 47.5
    mock_get_opening.assert_called_once_with("americanfootball_nfl", ["evt1"])


def test_get_games_for_date_omits_opening_line_when_not_captured_yet():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines", return_value={}):
        result, error = GameService.get_games_for_date("americanfootball_nfl")

    assert error is None
    assert "opening" not in result["games"][0]


def test_get_games_for_date_skips_opening_line_lookup_for_unsupported_sport():
    nba_scores = [{**FAKE_SCORES[0], "sport_key": "basketball_nba"}]
    with patch("api.services.game_service.get_odds_data", return_value=(nba_scores, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines") as mock_get_opening:
        result, error = GameService.get_games_for_date("basketball_nba")

    assert error is None
    assert "opening" not in result["games"][0]
    mock_get_opening.assert_not_called()


def test_get_single_game_attaches_opening_line():
    with patch("api.services.game_service.get_odds_data", return_value=(FAKE_SCORES, FAKE_ODDS)), \
         patch("api.services.game_service.OpeningLinesService.get_opening_lines",
               return_value={"evt1": FAKE_OPENING_ROW}):
        result, error = GameService.get_single_game("americanfootball_nfl", "evt1")

    assert error is None
    assert result["game"]["opening"]["home"]["h2h"] == -155
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && pytest tests/test_game_service_opening_lines.py -v`
Expected: FAIL — `AttributeError` (no `opening` key) on the first assertion in each
test, since `GameService` doesn't attach it yet.

- [ ] **Step 3: Modify `api/services/game_service.py`**

Add this import near the top, alongside the other same-package import:

```python
from .opening_lines_service import OpeningLinesService
```

Add this module-level constant right after the imports (before `eastern_tz = ...`):

```python
# Sports that have opening-line data captured by jobs/capture_opening_lines.py.
# Values are the Odds-API sport key GameService already works with — see
# docs/superpowers/plans/2026-10-21-line-movement.md Task 1's note.
OPENING_LINE_SPORTS = {
    'americanfootball_nfl', 'americanfootball_ncaaf', 'baseball_mlb', 'icehockey_nhl',
}
```

Replace the body of `get_games_for_date` from `filtered_scores = filter_games_by_date(...)`
through the `formatted_games = [...]` block with:

```python
        filtered_scores = filter_games_by_date(scores, selected_date_start)

        next_game_date = None
        if selected_date_start and not filtered_scores:
            next_game_date = get_next_game_date_within_7_days(scores, selected_date_start)

        opening_lines = {}
        if sport_key in OPENING_LINE_SPORTS:
            opening_lines = OpeningLinesService.get_opening_lines(
                sport_key, [g['id'] for g in filtered_scores]
            )

        formatted_games = [
            GameService._format_game_data(
                match, odds, selected_date_start, opening_lines.get(match['id'])
            )
            for match in filtered_scores
        ]
```

Replace the body of `get_single_game` after the `if not game:` check with:

```python
        opening_row = None
        if sport_key in OPENING_LINE_SPORTS:
            opening_lines = OpeningLinesService.get_opening_lines(sport_key, [game_id])
            opening_row = opening_lines.get(game_id)

        formatted_game = GameService._format_game_data(game, odds, opening_row=opening_row)
        return {'game': formatted_game}, None
```

Change `_format_game_data`'s signature and the end of its body:

```python
    @staticmethod
    def _format_game_data(match, odds, selected_date_start=None, opening_row=None):
```

...(leave the existing body unchanged up through the `draw` block)...

```python
        if match.get('sport_key') == 'soccer_epl' and draw_odds and draw_odds.get('h2h') is not None:
            game_obj["draw"] = {"h2h": draw_odds["h2h"]}

        if opening_row:
            game_obj["opening"] = {
                "home": {
                    "spread_point": opening_row.get("home_spread_point"),
                    "spread_price": opening_row.get("home_spread_price"),
                    "h2h": opening_row.get("home_moneyline"),
                },
                "away": {
                    "spread_point": opening_row.get("away_spread_point"),
                    "spread_price": opening_row.get("away_spread_price"),
                    "h2h": opening_row.get("away_moneyline"),
                },
                "totals": {
                    "over_point": opening_row.get("total_point"),
                    "over_price": opening_row.get("over_price"),
                    "under_point": opening_row.get("total_point"),
                    "under_price": opening_row.get("under_price"),
                },
                "snapshot_time": (
                    opening_row["opening_snapshot_time"].isoformat()
                    if opening_row.get("opening_snapshot_time") else None
                ),
            }
        return game_obj
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_game_service_opening_lines.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full existing odds test suite to check for regressions**

Run: `source venv/bin/activate && pytest tests/test_odds_single_game.py tests/test_games_resolve.py -v`
Expected: PASS (unchanged — `_format_game_data`'s new parameter is optional and
defaults to `None`, so every existing call site behaves exactly as before)

- [ ] **Step 6: Commit**

```bash
git add api/services/game_service.py tests/test_game_service_opening_lines.py
git commit -m "Attach cached opening lines to GameService responses"
```

---

### Task 5: Frontend types

**Files:**
- Modify: `getstam-react/src/types/gameTypes.ts`

**Interfaces:**
- Produces: `OpeningLineTeamOdds`, `OpeningLineTotals`, `OpeningLineData` types;
  `GameWithDraw.opening?: OpeningLineData`. Task 6 (`GameOdds.tsx`) imports and uses
  these.

This task has no separate test — it's a type-only change, verified by Task 6's
tests and by the TypeScript compiler (CRA's `npm test`/`npm run build` both type-check).

- [ ] **Step 1: Add the new types**

Modify `getstam-react/src/types/gameTypes.ts` — insert immediately after the
`TotalsData` interface (after its closing `}`, before `export interface TeamData`):

```typescript
export interface OpeningLineTeamOdds {
  spread_point: number | null;
  spread_price: number | null;
  h2h: number | null;
}

export interface OpeningLineTotals {
  over_point: number | null;
  over_price: number | null;
  under_point: number | null;
  under_price: number | null;
}

export interface OpeningLineData {
  home: OpeningLineTeamOdds;
  away: OpeningLineTeamOdds;
  totals: OpeningLineTotals;
  snapshot_time: string | null;
}

```

- [ ] **Step 2: Add the field to `GameWithDraw`**

Modify the `GameWithDraw` interface:

```typescript
export interface GameWithDraw {
  home: TeamData;
  away: TeamData;
  totals: TotalsData;
  draw?: DrawOdds;
  opening?: OpeningLineData;
  [key: string]: any;
}
```

- [ ] **Step 3: Verify the frontend still type-checks**

Run: `cd getstam-react && CI=true npm test -- --watchAll=false 2>&1 | tail -30`
Expected: existing test suite still passes (no new failures) — this only adds
types, nothing consumes them yet.

- [ ] **Step 4: Commit**

```bash
git add getstam-react/src/types/gameTypes.ts
git commit -m "Add OpeningLineData type for line-movement display"
```

---

### Task 6: `GameOdds.tsx` — render the Open row

**Files:**
- Modify: `getstam-react/src/components/GameOdds.tsx`
- Test: `getstam-react/src/components/GameOdds.test.tsx`

**Interfaces:**
- Consumes: `GameWithDraw.opening?: OpeningLineData` from Task 5.
- Produces: nothing further downstream — this is the last task.

- [ ] **Step 1: Write the failing tests**

Create `getstam-react/src/components/GameOdds.test.tsx`:

```tsx
import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GameOdds from "./GameOdds";
import { GameWithDraw } from "../types/gameTypes";

const baseGame: GameWithDraw = {
  game_id: "evt1",
  commence_time: "2026-10-26T18:15:00Z",
  completed: false,
  home: { team: "Chicago Bears", score: null, odds: { h2h: -155, spread_point: -3, spread_price: -105 } },
  away: { team: "New England Patriots", score: null, odds: { h2h: 130, spread_point: 3, spread_price: -118 } },
  totals: { over_point: 47.5, over_price: -110, under_point: 47.5, under_price: -115 },
};

function renderGame(game: GameWithDraw) {
  return render(
    <MemoryRouter>
      <GameOdds game={game} />
    </MemoryRouter>
  );
}

describe("GameOdds opening line", () => {
  it("shows the opening line alongside current odds when present", () => {
    const game: GameWithDraw = {
      ...baseGame,
      opening: {
        home: { spread_point: -7, spread_price: -110, h2h: -280 },
        away: { spread_point: 7, spread_price: -110, h2h: 230 },
        totals: { over_point: 44.5, over_price: -110, under_point: 44.5, under_price: -110 },
        snapshot_time: "2026-10-14T12:00:00Z",
      },
    };
    renderGame(game);

    expect(screen.getByText("Open -7 (-110)")).toBeInTheDocument();
    expect(screen.getByText("Open +7 (-110)")).toBeInTheDocument();
    expect(screen.getByText("Open -280")).toBeInTheDocument();
    expect(screen.getByText("Open +230")).toBeInTheDocument();
    expect(screen.getByText("Open Over +44.5 (-110)")).toBeInTheDocument();
    expect(screen.getByText("Open Under +44.5 (-110)")).toBeInTheDocument();
  });

  it("renders current odds with no Open row when opening data is absent", () => {
    renderGame(baseGame);

    expect(screen.queryByText(/^Open/)).not.toBeInTheDocument();
    expect(screen.getByText("-3 (-105)")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd getstam-react && CI=true npm test -- GameOdds.test.tsx --watchAll=false`
Expected: FAIL — the "shows the opening line" test can't find the "Open ..." text
(it doesn't exist yet); the second test passes already (nothing to add there yet).

- [ ] **Step 3: Modify `GameOdds.tsx`**

Add these two helper functions right after the existing `formatH2H` function
(before `const statusLabel = ...`):

```tsx
  const formatOpeningSpread = (point: number | null | undefined, price: number | null | undefined) => {
    if ((point === null || point === undefined) && (price === null || price === undefined)) return null;
    return `Open ${formatOdds(point ?? null, price ?? null)}`;
  };

  const formatOpeningH2H = (h2h: number | null | undefined) => {
    if (h2h === null || h2h === undefined) return null;
    return `Open ${formatH2H(h2h)}`;
  };
```

Change the destructuring line near the top of the component to also pull `opening`:

```tsx
  const { home, away, totals, draw, opening } = game as GameWithDraw;
```

Replace the entire H2H row Box (the one containing `H2H` as its center label) with:

```tsx
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr",
              gap: 1,
              alignItems: "center",
              px: 1,
              py: 0.75,
              borderRadius: "9px",
              background: "rgba(255,255,255,0.68)",
            }}
          >
            <Box>
              <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155" }}>
                {formatH2H(home.odds?.h2h)}
              </Typography>
              {opening && formatOpeningH2H(opening.home.h2h) && (
                <Typography sx={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                  {formatOpeningH2H(opening.home.h2h)}
                </Typography>
              )}
            </Box>
            <Box sx={{ textAlign: "center" }}>
              <Typography sx={{ fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.05em", color: "#64748b", textTransform: "uppercase" }}>
                H2H
              </Typography>
              {draw?.h2h !== null && draw?.h2h !== undefined && (
                <Typography sx={{ fontSize: "0.82rem", fontWeight: 600, color: "#334155", mt: 0.15, whiteSpace: "nowrap" }}>
                  Draw {formatH2H(draw.h2h)}
                </Typography>
              )}
            </Box>
            <Box sx={{ textAlign: "right" }}>
              <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155" }}>
                {formatH2H(away.odds?.h2h)}
              </Typography>
              {opening && formatOpeningH2H(opening.away.h2h) && (
                <Typography sx={{ fontSize: "0.72rem", color: "#94a3b8", textAlign: "right" }}>
                  {formatOpeningH2H(opening.away.h2h)}
                </Typography>
              )}
            </Box>
          </Box>
```

Replace the entire Spread row Box with:

```tsx
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr",
              gap: 1,
              alignItems: "center",
              px: 1,
              py: 0.75,
              borderRadius: "9px",
              background: "rgba(255,255,255,0.68)",
            }}
          >
            <Box>
              <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155" }}>
                {formatOdds(home.odds?.spread_point ?? null, home.odds?.spread_price ?? null)}
              </Typography>
              {opening && formatOpeningSpread(opening.home.spread_point, opening.home.spread_price) && (
                <Typography sx={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                  {formatOpeningSpread(opening.home.spread_point, opening.home.spread_price)}
                </Typography>
              )}
            </Box>
            <Typography sx={{ fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.05em", color: "#64748b", textTransform: "uppercase", textAlign: "center" }}>
              Spread
            </Typography>
            <Box sx={{ textAlign: "right" }}>
              <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155" }}>
                {formatOdds(away.odds?.spread_point ?? null, away.odds?.spread_price ?? null)}
              </Typography>
              {opening && formatOpeningSpread(opening.away.spread_point, opening.away.spread_price) && (
                <Typography sx={{ fontSize: "0.72rem", color: "#94a3b8", textAlign: "right" }}>
                  {formatOpeningSpread(opening.away.spread_point, opening.away.spread_price)}
                </Typography>
              )}
            </Box>
          </Box>
```

Replace the entire Total row Box with:

```tsx
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr",
              gap: 1,
              alignItems: "center",
              px: 1,
              py: 0.75,
              borderRadius: "9px",
              background: "rgba(255,255,255,0.68)",
            }}
          >
            <Box>
              <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155" }}>
                {totals?.over_point != null
                  ? `Over ${formatOdds(totals.over_point, totals.over_price ?? null)}`
                  : "N/A"}
              </Typography>
              {opening && opening.totals.over_point != null && (
                <Typography sx={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                  {`Open Over ${formatOdds(opening.totals.over_point, opening.totals.over_price)}`}
                </Typography>
              )}
            </Box>
            <Typography sx={{ fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.05em", color: "#64748b", textTransform: "uppercase", textAlign: "center" }}>
              Total
            </Typography>
            <Box sx={{ textAlign: "right" }}>
              <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155", textAlign: "right" }}>
                {totals?.under_point != null
                  ? `Under ${formatOdds(totals.under_point, totals.under_price ?? null)}`
                  : "N/A"}
              </Typography>
              {opening && opening.totals.under_point != null && (
                <Typography sx={{ fontSize: "0.72rem", color: "#94a3b8", textAlign: "right" }}>
                  {`Open Under ${formatOdds(opening.totals.under_point, opening.totals.under_price)}`}
                </Typography>
              )}
            </Box>
          </Box>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd getstam-react && CI=true npm test -- GameOdds.test.tsx --watchAll=false`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full frontend test suite to check for regressions**

Run: `cd getstam-react && CI=true npm test -- --watchAll=false 2>&1 | tail -40`
Expected: PASS (no new failures — `GameDetails.test.tsx` renders `GameOdds` too
and doesn't pass `opening`, so it should render exactly as before)

- [ ] **Step 6: Commit**

```bash
git add getstam-react/src/components/GameOdds.tsx getstam-react/src/components/GameOdds.test.tsx
git commit -m "Render Open-vs-Now line movement in GameOdds"
```

---

## Deployment note (not a task — operational, done outside the repo)

After this merges and is deployed, add a **Heroku Scheduler** job (same place the
existing daily seed jobs are registered):

- **Command:** `python jobs/capture_opening_lines.py`
- **Frequency:** Daily
- **Suggested time:** early morning ET, after that day's `*_seed_yesterdays_games*`
  jobs would typically run and before most people are checking lines — e.g. 09:00 UTC
  (~4–5am ET) is a reasonable default; exact time isn't load-sensitive since this job
  only touches upcoming games, not yesterday's.

No code changes are required to register it — this is purely the Heroku dashboard
(or `heroku addons:open scheduler`) step.
