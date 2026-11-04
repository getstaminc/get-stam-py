# NBA Totals Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-off script that corrects `nba_games_1.total` for every row from 2020-07-01 onward, re-fetching the real pregame total from Odds API's historical odds at a snapshot close to each game's own kickoff time.

**Architecture:** Single script, `jobs/backfill_nba_totals.py`, with a `--start-date`/`--end-date` CLI (defaulting to the full 2020-07-01-to-yesterday range, overridable for cheap narrow testing). Per `game_date`: one historical `events` call to discover that day's games + their real `commence_time`s, then one historical `odds` call per unique `commence_time` (shared across games with identical start times) snapshotted ~1 hour before kickoff — mirroring the live seed jobs' established snapshot-timing convention exactly, since a blanket per-day snapshot was proven wrong during design (see spec).

**Tech Stack:** Python, `requests` (Odds API only — no ESPN), `sqlalchemy` (`create_engine`/`text`), `shared_utils.convert_team_name`, `argparse`.

**Spec:** `docs/superpowers/specs/2026-10-31-nba-totals-backfill-design.md`

## Global Constraints

- Odds API only — no ESPN calls anywhere in this script.
- Never null out or otherwise touch an existing `total` value when no match/no odds is found — only `UPDATE` a row when a real replacement value was actually found.
- Snapshot timing: fetch each unique `commence_time`'s odds at `commence_time - 1 hour`, never a single blanket snapshot per day (this was tested and shown to return drifted in-game numbers for games that had already kicked off before the snapshot).
- Match to our DB rows via `(game_date, home_team_name, away_team_name)` through `shared_utils.convert_team_name` — most rows in range have no `odds_event_id`.
- Bookmaker selection for the `totals` market: prefer DraftKings, fall back to the first bookmaker in response order that has one — same convention as `jobs/nba_odds_api_seed_yesterdays_games.py`.
- Commit after each `game_date` is fully processed (resumable/safe to re-run — re-applying the same correct value to an already-correct row is a harmless no-op).
- `DATABASE_URL` needs the `postgres://` → `postgresql://` replacement used everywhere else in `jobs/`.

---

### Task 1: Build the script and verify on a narrow 3-day test range

**Files:**
- Create: `jobs/backfill_nba_totals.py`

**Interfaces:**
- Produces: `get_day_schedule(date_str) -> list[dict]`, `get_odds_snapshot_for_commence_time(commence_time_iso) -> list[dict]`, `_market_from_preferred_bookmaker(bookmakers, market_key, preferred="draftkings")`, `parse_total(odds_game) -> float | None`, `backfill_date_range(start_date, end_date)`.

- [ ] **Step 1: Write the complete script**

```python
#!/usr/bin/env python3
"""One-off backfill: correct nba_games_1.total for 2020-07-01 onward by
re-fetching the real pregame total from Odds API's historical odds, snapshot
~1 hour before each game's own commence_time (never a blanket per-day
snapshot -- proven to return drifted in-game numbers for games that already
tipped off). Odds API only, no ESPN. Safe to re-run; only ever UPDATEs a row
when a real matched total was found, never nulls anything out.

Usage:
    python3 jobs/backfill_nba_totals.py
    python3 jobs/backfill_nba_totals.py --start-date 2021-12-15 --end-date 2021-12-17
"""
import os
import sys
import time
import argparse
import requests
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text
import shared_utils

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

DEFAULT_START = "2020-07-01"


def get_day_schedule(date_str: str, retries=3, delay=2):
    """Historical events for date_str via a fixed daily anchor snapshot
    (18:00:00Z -- schedule data doesn't drift like odds do, so the anchor
    time only needs to be a stable point where the day's games are already
    on the schedule, not precisely timed). Returns list of
    {'id', 'commence_time', 'home_team', 'away_team'}."""
    url = "https://api.the-odds-api.com/v4/historical/sports/basketball_nba/events"
    params = {"apiKey": ODDS_API_KEY, "date": f"{date_str}T18:00:00Z"}
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json().get("data", [])
            return [
                {"id": e["id"], "commence_time": e["commence_time"],
                 "home_team": e["home_team"], "away_team": e["away_team"]}
                for e in data
            ]
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching schedule for {date_str} (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def get_odds_snapshot_for_commence_time(commence_time_iso: str, retries=3, delay=2):
    """Historical odds list at commence_time - 1 hour. Returns the raw list
    of game-odds dicts from the API (each with 'id', 'home_team',
    'away_team', 'bookmakers')."""
    commence_dt = datetime.fromisoformat(commence_time_iso.replace("Z", "+00:00"))
    snapshot_dt = commence_dt - timedelta(hours=1)
    snapshot_str = snapshot_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = "https://api.the-odds-api.com/v4/historical/sports/basketball_nba/odds"
    params = {
        "apiKey": ODDS_API_KEY, "regions": "us", "markets": "totals",
        "oddsFormat": "american", "date": snapshot_str,
    }
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching odds snapshot at {snapshot_str} (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def _market_from_preferred_bookmaker(bookmakers, market_key, preferred="draftkings"):
    preferred_bm = next((bm for bm in bookmakers if bm["key"] == preferred), None)
    if preferred_bm:
        market = next((m for m in preferred_bm.get("markets", []) if m["key"] == market_key), None)
        if market:
            return market
    for bm in bookmakers:
        market = next((m for m in bm.get("markets", []) if m["key"] == market_key), None)
        if market:
            return market
    return None


def parse_total(odds_game: dict):
    """Extract the totals market's point value, DraftKings-preferred with
    fallback. Returns None if no bookmaker has a totals market."""
    bookmakers = odds_game.get("bookmakers", [])
    if not bookmakers:
        return None
    totals = _market_from_preferred_bookmaker(bookmakers, "totals")
    if not totals:
        return None
    over = next((o for o in totals["outcomes"] if o["name"] == "Over"), None)
    return over.get("point") if over else None


def backfill_date_range(start_date: str, end_date: str):
    print(f"Starting NBA totals backfill: {start_date} to {end_date}")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    processed_days = 0
    updated = 0
    skipped_no_db_match = 0
    skipped_no_odds = 0

    current = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    try:
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            events = get_day_schedule(date_str)
            if events:
                # Group events by unique commence_time to share odds snapshots.
                by_commence_time = {}
                for e in events:
                    by_commence_time.setdefault(e["commence_time"], []).append(e)

                odds_by_event_id = {}
                for commence_time, group in by_commence_time.items():
                    snapshot_games = get_odds_snapshot_for_commence_time(commence_time)
                    for g in snapshot_games:
                        odds_by_event_id[g["id"]] = g
                    time.sleep(0.3)

                for e in events:
                    odds_game = odds_by_event_id.get(e["id"])
                    if not odds_game:
                        skipped_no_odds += 1
                        continue
                    new_total = parse_total(odds_game)
                    if new_total is None:
                        skipped_no_odds += 1
                        continue

                    db_home = shared_utils.convert_team_name(e["home_team"])
                    db_away = shared_utils.convert_team_name(e["away_team"])
                    row = conn.execute(text("""
                        SELECT game_id FROM nba_games_1
                        WHERE game_date = :game_date AND home_team_name = :home AND away_team_name = :away
                    """), {"game_date": date_str, "home": db_home, "away": db_away}).fetchone()

                    if not row:
                        skipped_no_db_match += 1
                        continue

                    conn.execute(text("""
                        UPDATE nba_games_1 SET total = :new_total WHERE game_id = :game_id
                    """), {"new_total": new_total, "game_id": row[0]})
                    updated += 1
                    print(f"  {date_str}: {db_away} @ {db_home} -> total={new_total}")

            conn.commit()
            processed_days += 1
            current += timedelta(days=1)
            time.sleep(0.3)

        print(f"\nDone. Days processed: {processed_days}")
        print(f"Rows updated: {updated}")
        print(f"Skipped (no DB match): {skipped_no_db_match}")
        print(f"Skipped (no odds found): {skipped_no_odds}")
    except Exception as e:
        print(f"Error during backfill: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(description="Backfill nba_games_1.total precision from Odds API")
    parser.add_argument("--start-date", default=DEFAULT_START, help="YYYY-MM-DD (default: 2020-07-01)")
    parser.add_argument("--end-date", default=yesterday, help="YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    backfill_date_range(args.start_date, args.end_date)
```

- [ ] **Step 2: Run a narrow 3-day test against real data**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/nba-totals-backfill && ./venv/bin/python jobs/backfill_nba_totals.py --start-date 2021-12-15 --end-date 2021-12-17`

(If `./venv`/`.env` don't exist in this worktree, symlink them from the main checkout first.)

Expected: console output showing each game's old→new-implied total as it's updated, ending with a summary (`Days processed: 3`, some `Rows updated`, low/zero `Skipped` counts), no unhandled exception.

Verify directly against the DB afterward:
```bash
./venv/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
with engine.connect() as conn:
    rows = conn.execute(text(\"SELECT game_id, game_date, home_team_name, away_team_name, home_points, away_points, total FROM nba_games_1 WHERE game_date BETWEEN '2021-12-15' AND '2021-12-17' ORDER BY game_date\")).fetchall()
    for r in rows:
        print(r)
"
```
Confirm: `total` values are now half-point-precision floats (e.g. `214.5`, not `215.0`) for at least some rows — if every single row in this 3-day sample is still a whole number, that's a sign something didn't actually update; investigate before moving to Task 2. Spot-check at least one value against what the design spec's own research already confirmed live (the Pacers @ Bucks game on 2021-12-15/16 should land at `214.5` — DraftKings' snapshot ~1hr before that game's tip, already verified during design).

- [ ] **Step 3: Commit**

```bash
git add jobs/backfill_nba_totals.py
git commit -m "feat: add NBA totals backfill script, verified on a 3-day test range"
```

---

### Task 2: Run the full backfill and verify the result

**Files:** none created/modified — this task only executes Task 1's script.

**Interfaces:** none — consumes `backfill_date_range` as a black box via the CLI.

- [ ] **Step 1: Run the full backfill**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/nba-totals-backfill && ./venv/bin/python jobs/backfill_nba_totals.py`

This covers 2020-07-01 through yesterday (~1,315 days, up to ~9,300 API calls) — expect this to take a meaningful amount of wall-clock time (likely 20+ minutes given the politeness delays and per-call network latency). Run it in the background if your environment supports that, and check on it periodically rather than blocking on it; it is resumable (commits per day) so an interruption isn't destructive, but re-starting from the same `--start-date` will simply redo already-correct days harmlessly rather than skipping them — if a faster resume is wanted after an interruption, pass `--start-date` as the day after the last one printed in the output.

Expected: no unhandled exception, a final summary line with `Days processed: ~1315`, `Rows updated` in the thousands, and `Skipped` counts that are a small fraction of the total (large skip counts would indicate something is systematically wrong — e.g., team-name matching broadly failing — and should be investigated rather than accepted).

- [ ] **Step 2: Verify the before/after impact directly**

Run:
```bash
./venv/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
with engine.connect() as conn:
    r = conn.execute(text('''
        SELECT COUNT(*) FILTER (WHERE game_date >= '2020-07-01' AND home_points + away_points = total),
               COUNT(*) FILTER (WHERE game_date >= '2020-07-01' AND total != ROUND(total))
        FROM nba_games_1
    ''')).fetchone()
    print('remaining exact-match push rows (was 204 before backfill):', r[0])
    print('rows now holding a genuine half-point value:', r[1])
"
```
Expected: the first number should have dropped substantially from the known baseline of 204 (some residual is acceptable — a handful of games may have genuinely closed exactly on a whole number, or Odds API may lack coverage for a few specific games); the second number should be in the thousands, confirming real half-point precision was actually written for a large share of the backfilled rows, not just a no-op re-write of the same whole numbers.

- [ ] **Step 3: Commit the final state note**

No code changes in this task — append a short note to the plan's own ledger/report (handled by the execution process, not a git commit) summarizing the before/after counts from Step 2.

---

## Self-Review Notes

- **Spec coverage:** per-game snapshot timing (not blanket per-day) → `get_odds_snapshot_for_commence_time`'s `commence_time - 1 hour` calculation, grouped by unique `commence_time` in `backfill_date_range`. Lenient update policy (never null, only update on a real match) → the `skipped_no_db_match`/`skipped_no_odds` branches never call `UPDATE`. DraftKings-preferred bookmaker selection → `_market_from_preferred_bookmaker`, identical logic to the live seed job. Resumable/idempotent → per-day commit + safe re-run semantics. Scope (2020-07-01 to yesterday, all rows not just the 204) → `DEFAULT_START` and the unconditional `UPDATE` (not gated on the exact-match check).
- **Placeholder scan:** no TBD/TODO; every step has runnable code or a concrete command with a stated expected result.
- **Type consistency:** `get_day_schedule` and `get_odds_snapshot_for_commence_time` both return lists of dicts with an `'id'` key, consumed consistently in `backfill_date_range`'s `odds_by_event_id` lookup. `parse_total` returns `float | None`, checked with `is None` (not truthiness, since `0.0` would be a legitimate — if extremely unusual — total).
