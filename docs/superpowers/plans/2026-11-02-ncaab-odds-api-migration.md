# NCAAB Odds-API-and-ESPN Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `odds_event_id` column to `ncaab_games`, fix the pre-existing NCAAB team-name mapping bugs in `shared_utils.py`'s `convert_team_name_ncaab`, then build two new scheduled jobs — `jobs/ncaab_odds_api_seed_yesterdays_games.py` (Odds API + ESPN, primary; also populates the previously-unused half/OT scoring columns) and `jobs/ncaab_sdql_fallback_fill.py` (SDQL, fills only what's still NULL) — replacing the single SDQL-only `jobs/ncaab_seed_yesterdays_games.py`.

**Architecture:** One migration, one shared-file name-mapping fix, two new job files, one deletion. Job 1 drives off ESPN's `groups=50` (Division I) scoreboard — unlike NCAAF, a single group is enough here; no second broad group is needed since D-II/D-III/NAIA games are expected to come from SDQL only. Job 1 enriches with Odds API where available and uses our existing `teams` table as the scope filter. Job 2 reuses the current job's proven SDQL-fetching logic unchanged, but fills gaps via `COALESCE` instead of inserting fresh rows, and — learning directly from a real bug found in NCAAF's job 2 — dedupes SDQL's per-team mirrored rows and checks for existing rows in both home/away orientations from its very first version, not as a later fix.

**Tech Stack:** Python, `requests` (Odds API + ESPN + SDQL), `sqlalchemy` (`create_engine`/`text`), `shared_utils.convert_team_name_ncaab`/`convert_to_eastern`, `alembic`.

**Spec:** `docs/superpowers/specs/2026-11-02-ncaab-odds-api-migration-design.md`

## Global Constraints

- Job 1 (Odds API+ESPN) never drops a game over missing odds or failed enrichment — same lenient policy as NFL/NBA/NCAAF.
- Job 2 (SDQL) never overwrites a non-NULL value on an existing row — it only fills gaps, via `COALESCE(existing, new)` on every column it touches.
- Job 2 must dedupe SDQL's results by `(date, frozenset({home_team_id, away_team_id}))` BEFORE processing, and its existing-row check must test BOTH orientations — `(home=:a AND away=:b)` and `(home=:b AND away=:a)` — treating an exact-orientation match as fill-target and a reversed-orientation match as already-present (skip, no fill). SDQL emits one row per team for neutral-site games with home/away reversed between them; failing to guard this created real production duplicates during the NCAAF migration (confirmed: 3 duplicate rows for 3 real neutral-site games) — this must be built correctly from the start here, not discovered again.
- Job 1's scope filter is our existing `teams WHERE sport='NCAAB'` roster via `convert_team_name_ncaab` — not ESPN's `groups` semantics. A team that doesn't resolve to an existing roster row is silently skipped.
- `game_site` is derived from ESPN's `neutralSite` flag in job 1 as `"neutral" if neutral_site else "home"` — never a bare conditional that can evaluate to `None` (`ncaab_games.game_site` is `NOT NULL`, confirmed via `information_schema.columns`; a `None` here would crash the whole run since all games in one run share one transaction — this exact bug class was already found and fixed once during the NFL migration). Job 2 uses `game.get('site') or 'home'` on its fresh-insert path for the same reason.
- `odds_event_id` is only ever set by job 1 — job 2 never sets it (SDQL has no equivalent id).
- `home_quarter_scores`/`away_quarter_scores` are JSON-typed columns — must be `json.dumps()`'d before binding.
- College basketball has 2 regulation periods (halves), not 4 quarters — `home/away_first_half_points` and `home/away_second_half_points` are DIRECT index lookups on each team's own ESPN `linescores` (`linescores[0]`, `linescores[1]`), never a sum of pairs (the pattern used for the 4-quarter sports). `home/away_overtime_points` is `linescores[2]` if present, else `None`.
- SDQL's NCAABB query has no quarter/half-score fields at all (confirmed by reading the current `jobs/ncaab_seed_yesterdays_games.py` query string) — job 2 never touches `home/away_quarter_scores`/half/OT columns; they stay NULL if job 1's ESPN enrichment also missed them.
- Numeric fields from SDQL (money lines, `line`/`o:line`, `total`) must be guarded with `isinstance(x, (int, float))` before binding — SDQL sometimes returns non-numeric sentinels or floats where an int is expected (confirmed bug class from the NCAAF migration).
- `DATABASE_URL` needs the `postgres://` → `postgresql://` replacement used everywhere else in `jobs/`.
- Odds API sport key for this sport is `basketball_ncaab` (confirmed in `api/external_requests/odds_api.py:16`).

---

### Task 1: Add `odds_event_id` migration for `ncaab_games`

**Files:**
- Create: `migrations/versions/<new_revision>_add_odds_event_id_to_ncaab_games.py`

**Interfaces:**
- Produces: a new nullable `odds_event_id` column + unique constraint `uq_ncaab_games_odds_event_id` on `ncaab_games`, consumed by Task 3's job.

- [ ] **Step 1: Generate and fill in the migration**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/ncaab-odds-api-migration && ./venv/bin/python -m alembic revision -m "add_odds_event_id_to_ncaab_games"`

Replace the generated file's docstring and `upgrade`/`downgrade` functions with:

```python
"""add_odds_event_id_to_ncaab_games

Mirrors fd711e7e2b11 (nba_games_1), a7c2e9f4b1d3 (nfl_games), and
11c35d14cecd (ncaaf_games) - lays the groundwork for seeding ncaab_games
from the Odds API scores endpoint instead of SportsDatabase/SDQL.
"""


def upgrade() -> None:
    op.add_column('ncaab_games', sa.Column('odds_event_id', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_ncaab_games_odds_event_id', 'ncaab_games', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_ncaab_games_odds_event_id', 'ncaab_games', type_='unique')
    op.drop_column('ncaab_games', 'odds_event_id')
```

Leave the generated `revision`/`down_revision`/`branch_labels`/`depends_on` assignments and imports exactly as alembic generated them — only replace the docstring and the two function bodies.

- [ ] **Step 2: Apply and verify**

Run: `./venv/bin/python -m alembic upgrade head`

Verify:
```bash
./venv/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
with engine.connect() as conn:
    row = conn.execute(text(\"SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'ncaab_games' AND column_name = 'odds_event_id'\")).fetchone()
    print('column:', row)
    idx = conn.execute(text(\"SELECT indexname FROM pg_indexes WHERE tablename = 'ncaab_games' AND indexname LIKE '%odds_event_id%'\")).fetchall()
    print('constraint/index:', idx)
"
```
Expected: `column: ('odds_event_id', 'YES')` and a non-empty constraint/index list.

- [ ] **Step 3: Commit**

```bash
git add migrations/versions/<the new migration file>
git commit -m "feat: add odds_event_id column to ncaab_games"
```

---

### Task 2: Fix NCAAB team-name mapping bugs in `shared_utils.py`

**Files:**
- Modify: `shared_utils.py` (the `convert_team_name_ncaab` function, starting around line 11)

**Interfaces:**
- Produces: corrected/added entries in `convert_team_name_ncaab`'s dict, consumed by Task 3's job. Also used by live code (`api/services/game_service.py`, `api/services/historical/ncaab_service.py`, `api/services/historical/ncaab_trends_service.py`) — fixes here improve those paths too, not just the new job.

- [ ] **Step 1: Re-run the reconciliation script to get the current real mismatch list**

Repo state may have shifted since this plan was written — re-derive the list fresh rather than trusting the brief's copy of it. Run:
```bash
cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/ncaab-odds-api-migration
./venv/bin/python3 -c "
import os, sys, requests
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import shared_utils
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
with engine.connect() as conn:
    db_teams = set(r[0] for r in conn.execute(text(\"SELECT team_name FROM teams WHERE sport = 'NCAAB'\")).fetchall())

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
# Pick several real in-season dates spread across the season so results don't
# depend on which teams happened to play on a single day.
dates = ['20260110', '20260117', '20260124', '20260131', '20260207']
all_names = set()
for d in dates:
    r = requests.get('https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard',
                      headers=UA, params={'dates': d, 'limit': 400, 'groups': 50}, timeout=20)
    for e in r.json().get('events', []):
        if e.get('status', {}).get('type', {}).get('name') != 'STATUS_FINAL':
            continue
        for c in e['competitions'][0]['competitors']:
            all_names.add(c['team']['displayName'])

matched, unmatched = 0, []
for name in sorted(all_names):
    short = shared_utils.convert_team_name_ncaab(name)
    if short in db_teams:
        matched += 1
    else:
        unmatched.append((name, short))
print(f'Matched: {matched}  Unmatched: {len(unmatched)}')
for name, short in unmatched:
    print(f\"  '{name}' -> '{short}'\")
"
```

- [ ] **Step 2: Fix the genuine mapping bugs**

For each unmatched name, decide: is this a team we already track under a different spelling (fix the dict), or a genuinely out-of-scope non-D-I school (leave it unmatched — do not add an entry for it). The following mismatches were confirmed real during design research on a 2026-01-15 sample and should be treated as a starting point — re-verify each against the current file and the current script output before editing, since both may have shifted:

- Teams whose ESPN `displayName` uses an abbreviated state suffix ("St") where the dict expects the full word "State", or vice versa — e.g. Arkansas State, Washington State, Cleveland State, Youngstown State. For each, run `SELECT team_name FROM teams WHERE sport='NCAAB' AND team_name ILIKE '%<short code guess>%'` to find the stored short code, then add the ESPN-spelled variant as an alias alongside (not replacing) any existing entry.
- `Green Bay Phoenix` — check whether the dict has an older mascot/name for this school (same Wisconsin-Green Bay program) and add this as an alias.
- `Northeastern Huskies` — check for a possible collision/confusion with UConn's "Huskies" mascot in the existing dict; add a distinct, correctly-scoped entry if missing.
- `Queens University Royals`, `Oakland Golden Grizzlies`, `The Citadel Bulldogs`, `St. Thomas (MN) Tommies`, `South Dakota Coyotes`, `Tenn-Martin Skyhawks` (ESPN may show `UT Martin` instead — check both), `SIU-Edwardsville Cougars`, `Tarleton State Texans`, `Florida Atlantic Owls` — for each, run `SELECT team_id, team_name FROM teams WHERE sport='NCAAB' AND team_name ILIKE '%<guess>%'` to find the actual stored short code, then add the ESPN-spelled full name as a new dict entry (or alias alongside an existing differently-spelled one — never rename/remove an existing key, since other code like `api/services/historical/ncaab_service.py` may depend on it; this exact rename-vs-alias mistake was made once during the NCAAF migration and had to be reverted).

For every other name in the Step 1 output not listed above: investigate briefly (is it a Division II/III/NAIA/small-conference school not in our 1,135-team roster?) — if so, leave it alone, don't add a mapping. Do not spend more than a glance per entry; the goal is catching real misses, not auditing every small school.

- [ ] **Step 3: Re-run the Step 1 script and verify the fixes landed**

Re-run the exact script from Step 1. Expected: the `Matched` count increases by roughly the number of real fixes applied in Step 2 (don't expect an exact match to any specific number — re-derive and sanity-check, don't force a target). Spot-check that the entries you fixed no longer appear in the `Unmatched` list, and that what remains unmatched still looks like genuine small-school/non-D-I noise (eyeball a handful of names), not more real teams.

- [ ] **Step 4: Run the full test suite**

Run: `./venv/bin/python -m pytest tests/ -q`
Expected: the current baseline pass count at run time, zero new failures — this is a shared file used across every sport, so a regression here would show up broadly.

- [ ] **Step 5: Commit**

```bash
git add shared_utils.py
git commit -m "fix: correct NCAAB team-name mappings in convert_team_name_ncaab for ESPN's current naming"
```

---

### Task 3: Build and verify `jobs/ncaab_odds_api_seed_yesterdays_games.py`

**Files:**
- Create: `jobs/ncaab_odds_api_seed_yesterdays_games.py`

**Interfaces:**
- Consumes: `ncaab_games.odds_event_id` (Task 1), corrected `shared_utils.convert_team_name_ncaab` (Task 2).
- Produces: `get_completed_ncaab_games_for_date`, `get_historical_odds_for_date`, `get_espn_games_for_date`, `_market_from_preferred_bookmaker`, `parse_odds_data`, `seed_yesterdays_ncaab_games`.

- [ ] **Step 1: Write the complete job file**

```python
#!/usr/bin/env python3
"""Seed yesterday's NCAAB games from ESPN (schedule discovery + score/
enrichment fallback) and Odds API (score + lines where available).

ESPN drives discovery via groups=50 (Division I) -- unlike NCAAF, a single
group is sufficient here; Division II/III/NAIA games are expected to come
from the SDQL fallback job only, not from any ESPN group. A game is only
processed if BOTH teams resolve, via convert_team_name_ncaab, to an
existing row in `teams WHERE sport='NCAAB'` -- our own roster is the scope
filter, not ESPN's group semantics.

Odds API enriches with real lines where it has the game (strong D-I
coverage, confirmed during design: an exact 49/49 game-count match on a
real mid-season date); ESPN's own competitor.score is the fallback final
score for games Odds API doesn't track. A second, later-scheduled job
(jobs/ncaab_sdql_fallback_fill.py) fills remaining gaps from SDQL -- this
job never calls SDQL.

Also populates home/away_quarter_scores, home/away_first_half_points,
home/away_second_half_points, and home/away_overtime_points from ESPN's
linescores -- columns that exist in the schema but were never populated by
the old SDQL-only job (SDQL's NCAABB query has no quarter/half-score
field). College basketball has 2 regulation periods (halves), not 4
quarters: first/second-half points are DIRECT index lookups
(linescores[0], linescores[1]), never a sum of pairs like the 4-quarter
sports. Overtime is linescores[2] if present.
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text
import shared_utils

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ESPN_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_completed_ncaab_games_for_date(target_date_str: str, retries=3, delay=2):
    """Odds API current (non-historical) scores for the last 3 days,
    filtered to games whose Eastern-converted commence date matches
    target_date_str. Returns the raw list of Odds API game dicts."""
    url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/scores/"
    params = {"apiKey": ODDS_API_KEY, "daysFrom": 3, "dateFormat": "iso"}
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            games = response.json()
            matched = []
            for game in games:
                if not game.get("completed") or not game.get("scores"):
                    continue
                commence_utc = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
                commence_et = shared_utils.convert_to_eastern(commence_utc)
                if str(commence_et.date()) == target_date_str:
                    matched.append(game)
            return matched
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Odds API scores (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def get_historical_odds_for_date(date_str: str, retries=3, delay=2):
    """Historical h2h/spreads/totals odds for a date. No bookmakers filter --
    parse_odds_data picks per-market."""
    url = "https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
    params = {
        "apiKey": ODDS_API_KEY, "regions": "us",
        "markets": "h2h,spreads,totals", "oddsFormat": "american",
        "date": f"{date_str}T00:00:00Z",
    }
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Odds API odds (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def get_espn_games_for_date(date_str: str, retries=3, delay=2):
    """ESPN scoreboard for date_str, groups=50 (Division I only). Returns
    raw event dicts (STATUS_FINAL only)."""
    date_compact = date_str.replace("-", "")
    for i in range(retries):
        try:
            resp = requests.get(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
                params={"dates": date_compact, "limit": 400, "groups": 50},
                headers=ESPN_HEADERS, timeout=30,
            )
            resp.raise_for_status()
            events = resp.json().get("events", [])
            break
        except requests.exceptions.RequestException as e:
            print(f"  ESPN scoreboard fetch failed (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                events = []
    return [
        e for e in events
        if e.get("status", {}).get("type", {}).get("name") == "STATUS_FINAL"
    ]


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


def parse_odds_data(odds_game: dict) -> dict:
    """Extract moneyline, spread, and total -- each market independently
    sourced, DraftKings-preferred with fallback."""
    result = {
        "home_money_line": None, "away_money_line": None,
        "home_line": None, "away_line": None, "total": None,
    }
    bookmakers = odds_game.get("bookmakers", [])
    if not bookmakers:
        return result

    home_team = odds_game["home_team"]
    away_team = odds_game["away_team"]

    h2h = _market_from_preferred_bookmaker(bookmakers, "h2h")
    if h2h:
        for outcome in h2h["outcomes"]:
            if outcome["name"] == home_team:
                result["home_money_line"] = outcome["price"]
            elif outcome["name"] == away_team:
                result["away_money_line"] = outcome["price"]

    spreads = _market_from_preferred_bookmaker(bookmakers, "spreads")
    if spreads:
        for outcome in spreads["outcomes"]:
            if outcome["name"] == home_team:
                result["home_line"] = outcome.get("point")
            elif outcome["name"] == away_team:
                result["away_line"] = outcome.get("point")

    totals = _market_from_preferred_bookmaker(bookmakers, "totals")
    if totals:
        over = next((o for o in totals["outcomes"] if o["name"] == "Over"), None)
        if over:
            result["total"] = over.get("point")

    return result


def seed_yesterdays_ncaab_games():
    print("Starting NCAAB game seeding (ESPN discovery + Odds API enrichment)...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

        espn_events = get_espn_games_for_date(yesterday)
        if not espn_events:
            print(f"No completed NCAAB games found on ESPN for {yesterday}")
            return

        odds_games = get_completed_ncaab_games_for_date(yesterday)
        odds_lookup_by_teams = {}
        for g in odds_games:
            db_h = shared_utils.convert_team_name_ncaab(g["home_team"])
            db_a = shared_utils.convert_team_name_ncaab(g["away_team"])
            odds_lookup_by_teams[(db_h, db_a)] = g

        odds_data = get_historical_odds_for_date(yesterday)
        odds_info_by_event_id = {g["id"]: g for g in odds_data}

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAB'")).mappings()
        }

        inserted = 0
        for event in espn_events:
            comp = event["competitions"][0]
            home_c = next((c for c in comp["competitors"] if c.get("homeAway") == "home"), {})
            away_c = next((c for c in comp["competitors"] if c.get("homeAway") == "away"), {})
            espn_home_name = home_c.get("team", {}).get("displayName", "")
            espn_away_name = away_c.get("team", {}).get("displayName", "")

            db_home = shared_utils.convert_team_name_ncaab(espn_home_name)
            db_away = shared_utils.convert_team_name_ncaab(espn_away_name)
            home_team_id = teams_dict.get(db_home)
            away_team_id = teams_dict.get(db_away)
            if home_team_id is None or away_team_id is None:
                continue  # out of our tracked scope -- silently skip

            odds_game = odds_lookup_by_teams.get((db_home, db_away))
            odds_event_id = odds_game["id"] if odds_game else None

            if odds_game:
                home_points = away_points = None
                for score in odds_game["scores"]:
                    name = shared_utils.convert_team_name_ncaab(score["name"])
                    if name == db_home:
                        home_points = int(score["score"])
                    elif name == db_away:
                        away_points = int(score["score"])
            else:
                home_points = int(home_c.get("score", 0)) if home_c.get("score") is not None else None
                away_points = int(away_c.get("score", 0)) if away_c.get("score") is not None else None

            if home_points is None or away_points is None:
                print(f"Skipping {espn_away_name} @ {espn_home_name} - no score from either source")
                continue

            existing = conn.execute(text("""
                SELECT 1 FROM ncaab_games
                WHERE odds_event_id = :odds_event_id
                   OR (game_date = :game_date AND home_team_id = :home_team_id AND away_team_id = :away_team_id)
            """), {
                "odds_event_id": odds_event_id, "game_date": yesterday,
                "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()
            if existing:
                print(f"Already seeded: {db_away} @ {db_home} on {yesterday}")
                continue

            odds_info = parse_odds_data(odds_info_by_event_id.get(odds_event_id, {})) if odds_event_id else {
                "home_money_line": None, "away_money_line": None,
                "home_line": None, "away_line": None, "total": None,
            }

            season_type = event.get("season", {}).get("type")
            playoffs = (season_type == 3) if season_type is not None else None
            neutral_site = comp.get("neutralSite")
            # ncaab_games.game_site is NOT NULL (confirmed via information_schema) -- both
            # False and an unknown/missing neutralSite must map to 'home', never None.
            # Writing SQL NULL here would crash the whole run (all games share one
            # transaction) on any event missing this field.
            game_site = "neutral" if neutral_site else "home"

            # College basketball has 2 regulation periods (halves), not 4 quarters.
            # linescores[0]/[1] ARE the first/second half directly -- no summing,
            # unlike the 4-quarter sports. linescores[2]+ is overtime.
            home_ls = home_c.get("linescores", [])
            away_ls = away_c.get("linescores", [])
            home_qs = [int(ls.get("displayValue", 0)) for ls in home_ls] or None
            away_qs = [int(ls.get("displayValue", 0)) for ls in away_ls] or None
            if home_qs and away_qs and len(home_qs) >= 2 and len(away_qs) >= 2:
                home_first_half, home_second_half = home_qs[0], home_qs[1]
                away_first_half, away_second_half = away_qs[0], away_qs[1]
                home_overtime = home_qs[2] if len(home_qs) > 2 else None
                away_overtime = away_qs[2] if len(away_qs) > 2 else None
            else:
                home_first_half = home_second_half = home_overtime = None
                away_first_half = away_second_half = away_overtime = None

            commence_time = event.get("date")
            start_time = None
            if commence_time:
                try:
                    commence_dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                    start_time = shared_utils.convert_to_eastern(commence_dt).time()
                except Exception:
                    start_time = None

            print(f"Inserting: {db_away} {away_points} @ {db_home} {home_points} on {yesterday}")

            conn.execute(text("""
                INSERT INTO ncaab_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_points, away_points, total_points, total_margin, home_line, away_line,
                    home_quarter_scores, away_quarter_scores, home_first_half_points, away_first_half_points,
                    home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                    home_money_line, away_money_line, playoffs, start_time, total, odds_event_id
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                    :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                    :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points,
                    :home_money_line, :away_money_line, :playoffs, :start_time, :total, :odds_event_id
                )
            """), {
                "game_date": yesterday, "game_site": game_site,
                "home_team_id": home_team_id, "away_team_id": away_team_id,
                "home_team_name": db_home, "away_team_name": db_away,
                "home_points": home_points, "away_points": away_points,
                "total_points": home_points + away_points, "total_margin": home_points - away_points,
                "home_line": odds_info["home_line"], "away_line": odds_info["away_line"],
                "home_quarter_scores": json.dumps(home_qs) if home_qs is not None else None,
                "away_quarter_scores": json.dumps(away_qs) if away_qs is not None else None,
                "home_first_half_points": home_first_half, "away_first_half_points": away_first_half,
                "home_second_half_points": home_second_half, "away_second_half_points": away_second_half,
                "home_overtime_points": home_overtime, "away_overtime_points": away_overtime,
                "home_money_line": odds_info["home_money_line"], "away_money_line": odds_info["away_money_line"],
                "playoffs": playoffs, "start_time": start_time,
                "total": odds_info["total"], "odds_event_id": odds_event_id,
            })
            inserted += 1

        conn.commit()
        print(f"Seeded {inserted} NCAAB game(s) for {yesterday}")
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_ncaab_games()
```

- [ ] **Step 2: Run it against real data and sanity-check**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/ncaab-odds-api-migration && ./venv/bin/python jobs/ncaab_odds_api_seed_yesterdays_games.py`

(Symlink `./venv`/`.env` from the main checkout first if they don't exist in this worktree.)

Expected: a mix of `Inserting:`/`Already seeded:`/skip lines, ending with `Seeded N NCAAB game(s) for <date>`, no unhandled exception. If "yesterday" has zero games (off-season or a date with no games), temporarily hardcode a known in-season date with real games for a one-off manual verification run, then revert the hardcode before committing — same approach used for NFL/NBA/NCAAF's verification.

For at least one inserted game with `odds_event_id` set, confirm `home_line`/`away_line` look like real spread numbers, not moneyline-sized numbers, and confirm `home_first_half_points + home_second_half_points` (plus `home_overtime_points` if present) sums to `home_points` for that game (verifies the half-vs-quarter indexing is correct, not off-by-one). For at least one inserted game with `odds_event_id` NULL, confirm the score and half-points are still populated via ESPN, and that `home_line`/`away_line`/`total`/money-lines are NULL (expected — job 2 fills these later) rather than the job having skipped the game entirely.

- [ ] **Step 3: Commit**

```bash
git add jobs/ncaab_odds_api_seed_yesterdays_games.py
git commit -m "feat: add NCAAB games seed job sourced from ESPN + Odds API"
```

---

### Task 4: Build and verify `jobs/ncaab_sdql_fallback_fill.py`

**Files:**
- Create: `jobs/ncaab_sdql_fallback_fill.py`

**Interfaces:**
- Consumes: rows already inserted by Task 3's job for the same date (if job 1 hasn't run yet for a given date, this job's `COALESCE`-based fill simply has nothing to fill and the row-doesn't-exist INSERT path handles it instead).
- Produces: `get_yesterdays_sdql_games`, `fill_yesterdays_ncaab_games_from_sdql`.

- [ ] **Step 1: Write the complete script**

This reuses the current `jobs/ncaab_seed_yesterdays_games.py`'s SDQL-fetching logic essentially unchanged (same query, same parsing) — the persistence step changes from "insert, skip if a duplicate exists" to "update only-if-NULL via COALESCE, insert only if the row doesn't exist at all" — and, critically, adds the in-memory dedupe and both-orientations existing-row check from the start (NCAAF's job 2 initially lacked this and created real production duplicates for neutral-site games; it must not be repeated here).

```python
#!/usr/bin/env python3
"""Fallback fill for NCAAB games: fetches yesterday's games from SDQL (the
same query the old jobs/ncaab_seed_yesterdays_games.py used) and fills in
ONLY whatever is still NULL on the matching ncaab_games row -- never
overwrites a value jobs/ncaab_odds_api_seed_yesterdays_games.py already
supplied. If a game is missing entirely (rare -- ESPN's Division I
scoreboard should have caught nearly everything SDQL finds for D-I; non-D-I
games depend on this job for everything), inserts it fresh from SDQL with
odds_event_id left NULL.

SDQL's NCAABB query has no quarter/half-score field at all -- this job
never touches home/away_quarter_scores or the half/OT point columns; those
stay NULL if job 1's ESPN enrichment also missed them.

SDQL emits one row per team for neutral-site games, with home/away
reversed between the two rows for the same real game (both pass the
`site IN ('home','neutral')` filter). This job dedupes those in memory
before processing, and its existing-row check tests BOTH orientations --
an exact-orientation match is a fill target, a reversed-orientation match
means the game is already represented and this row is skipped entirely
(no fill, to avoid needing to swap home/away values). Without this guard,
every neutral-site game would get a second, duplicate row -- confirmed as
a real production bug during the NCAAF migration.

Scheduled to run AFTER jobs/ncaab_odds_api_seed_yesterdays_games.py, later
in the day (SDQL's data becomes reliably available later than Odds API's).
"""
import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'


def get_yesterdays_sdql_games(retries=3, delay=1):
    """Same SDQL query the old job used -- unchanged."""
    sdql_url = "https://s3.sportsdatabase.com/NCAABB/query"
    today = datetime.today().strftime('%Y%m%d')
    two_days_ago = (datetime.today() - timedelta(days=2)).strftime('%Y%m%d')
    sdql_query = (
        f"date,site,team,o:team,points,o:points,total,margin,line,o:line,"
        f"playoffs,money line,o:money line,_t,start time"
        f"@(site='home' or site='neutral') and date<{today} and date>={two_days_ago}"
    )
    headers = {'user': SDQL_USERNAME, 'token': SDQL_TOKEN}
    data = {'sdql': sdql_query}

    for i in range(retries):
        try:
            response = requests.get(sdql_url, headers=headers, params=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result.get('headers') and result.get('groups'):
                headers_list = result['headers']
                rows = result['groups'][0]['columns']
                formatted = [dict(zip(headers_list, row)) for row in zip(*rows)]
                for game in formatted:
                    game['date'] = datetime.strptime(str(game['date']), '%Y%m%d').strftime('%Y-%m-%d')
                return formatted
            return []
        except requests.exceptions.RequestException as e:
            print(f"SDQL request failed (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
        except ValueError as e:
            print(f"Error parsing SDQL response: {e}")
            return []
    return []


def fill_yesterdays_ncaab_games_from_sdql():
    print("Starting NCAAB SDQL fallback fill...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        games = get_yesterdays_sdql_games()
        print(f"Fetched {len(games)} SDQL games to use as fallback data")

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAB'")).mappings()
        }

        # Resolve team ids and dedupe SDQL's per-team mirrored rows for
        # neutral-site games BEFORE processing -- same (date, frozenset of
        # team ids) key used for NCAAF's equivalent fix.
        resolved = {}
        for game in games:
            if game.get('points') is None or game.get('o:points') is None:
                continue
            home_team_id = teams_dict.get(game['team'])
            away_team_id = teams_dict.get(game['o:team'])
            if home_team_id is None or away_team_id is None:
                continue
            key = (game['date'], frozenset({home_team_id, away_team_id}))
            resolved.setdefault(key, []).append((game, home_team_id, away_team_id))

        filled = 0
        inserted = 0
        skipped_duplicate = 0
        for (_, _), candidates in resolved.items():
            game, home_team_id, away_team_id = candidates[0]

            def to_number(value):
                return value if isinstance(value, (int, float)) else None

            total_value = to_number(game.get('total'))
            home_line = to_number(game.get('line'))
            away_line = to_number(game.get('o:line'))
            home_money = to_number(game.get('money line'))
            away_money = to_number(game.get('o:money line'))

            params = {
                "game_date": game['date'], "game_site": game.get('site') or 'home',
                "home_team_id": home_team_id, "away_team_id": away_team_id,
                "home_team_name": game['team'], "away_team_name": game['o:team'],
                "home_points": game['points'], "away_points": game['o:points'],
                "total_points": game['points'] + game['o:points'], "total_margin": game.get('margin'),
                "home_line": home_line, "away_line": away_line,
                "home_money_line": home_money, "away_money_line": away_money,
                "playoffs": bool(game.get('playoffs', 0)), "total": total_value,
            }

            exact = conn.execute(text("""
                SELECT game_id FROM ncaab_games
                WHERE game_date = :game_date AND home_team_id = :home_team_id AND away_team_id = :away_team_id
            """), {
                "game_date": game['date'], "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()

            if exact:
                conn.execute(text("""
                    UPDATE ncaab_games SET
                        game_site = COALESCE(game_site, :game_site),
                        home_points = COALESCE(home_points, :home_points),
                        away_points = COALESCE(away_points, :away_points),
                        total_points = COALESCE(total_points, :total_points),
                        total_margin = COALESCE(total_margin, :total_margin),
                        home_line = COALESCE(home_line, :home_line),
                        away_line = COALESCE(away_line, :away_line),
                        home_money_line = COALESCE(home_money_line, :home_money_line),
                        away_money_line = COALESCE(away_money_line, :away_money_line),
                        playoffs = COALESCE(playoffs, :playoffs),
                        total = COALESCE(total, :total)
                    WHERE game_id = :game_id
                """), {**params, "game_id": exact[0]})
                filled += 1
                continue

            reversed_match = conn.execute(text("""
                SELECT 1 FROM ncaab_games
                WHERE game_date = :game_date AND home_team_id = :away_team_id AND away_team_id = :home_team_id
            """), {
                "game_date": game['date'], "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()
            if reversed_match:
                # Already represented (job 1, or SDQL's own mirrored row for this
                # neutral-site game via a different (date, team-pair) candidate)
                # under the opposite home/away orientation -- skip entirely rather
                # than inserting a second, duplicate row for the same real game.
                skipped_duplicate += 1
                continue

            conn.execute(text("""
                INSERT INTO ncaab_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_points, away_points, total_points, total_margin, home_line, away_line,
                    home_money_line, away_money_line, playoffs, total
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                    :home_money_line, :away_money_line, :playoffs, :total
                )
            """), params)
            inserted += 1

        conn.commit()
        print(f"Done. Rows filled (existing, NULL-only): {filled}. Rows inserted fresh: {inserted}. "
              f"Duplicate neutral-site rows skipped: {skipped_duplicate}.")
    except Exception as e:
        print(f"Error during SDQL fallback fill: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    fill_yesterdays_ncaab_games_from_sdql()
```

- [ ] **Step 2: Run it against real data and verify the fill + dedupe behavior**

Run: `./venv/bin/python jobs/ncaab_sdql_fallback_fill.py`

Expected: console output ending with `Done. Rows filled (existing, NULL-only): N. Rows inserted fresh: M. Duplicate neutral-site rows skipped: K.`, no unhandled exception.

Verify the COALESCE behavior directly: pick one row that Task 3's job inserted with `home_line`/`total` NULL (a game Odds API didn't track), confirm this job filled those columns with real SDQL values. Then verify non-destructiveness: pick a row that Task 3's job inserted WITH a real `home_line` already set, re-run this fallback job, and confirm that value is unchanged afterward (COALESCE should have left it alone) — this is the single most important behavior to verify given the "never overwrite" constraint.

Separately, verify the dedupe/orientation guard specifically: query SDQL (or inspect the fetched `games` list by adding a temporary print) for any neutral-site game on the fetched date range, confirm it appears as two mirrored rows in the raw SDQL response, and confirm the final `ncaab_games` table has exactly one row for that matchup/date afterward, not two. If no neutral-site game happens to fall in the current 2-day window, this check can be deferred to the first time one naturally occurs post-deploy — note this in the task report rather than blocking on it.

```bash
./venv/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
with engine.connect() as conn:
    rows = conn.execute(text(\"SELECT game_id, home_team_name, away_team_name, home_line, total, odds_event_id FROM ncaab_games ORDER BY game_date DESC, game_id LIMIT 20\")).fetchall()
    for r in rows:
        print(r)
    dupes = conn.execute(text(\"\"\"
        SELECT game_date, home_team_id, away_team_id, COUNT(*) FROM ncaab_games
        WHERE game_date >= CURRENT_DATE - INTERVAL '3 days'
        GROUP BY game_date, home_team_id, away_team_id HAVING COUNT(*) > 1
    \"\"\")).fetchall()
    print('Exact-orientation dupes in last 3 days:', dupes)
"
```

- [ ] **Step 3: Commit**

```bash
git add jobs/ncaab_sdql_fallback_fill.py
git commit -m "feat: add SDQL fallback-fill job for NCAAB games"
```

---

### Task 5: Delete the old combined SDQL job

**Files:**
- Delete: `jobs/ncaab_seed_yesterdays_games.py`

**Interfaces:** none — Tasks 3 and 4 together fully replace this file's functionality (schedule discovery + enrichment + SDQL fallback), confirmed via their own verification steps.

- [ ] **Step 1: Confirm zero live callers right before deleting**

Run: `grep -rln "ncaab_seed_yesterdays_games" --include="*.py" .`
Expected: no output (only the two new job files' docstrings may mention it by name as a historical reference — if so, that's fine, it's a comment, not a live import).

- [ ] **Step 2: Delete the file**

```bash
git rm jobs/ncaab_seed_yesterdays_games.py
```

- [ ] **Step 3: Confirm nothing else broke**

Run: `./venv/bin/python -m pytest tests/ -q` — expect the current baseline pass count, zero new failures.
Run: `./venv/bin/python -c "import app"` — expect clean exit, no import errors.

- [ ] **Step 4: Re-run both new jobs once more post-cleanup as a final regression check**

```bash
./venv/bin/python jobs/ncaab_odds_api_seed_yesterdays_games.py
./venv/bin/python jobs/ncaab_sdql_fallback_fill.py
```
Expected: same clean behavior as their own task's verification — confirms neither job secretly depended on the deleted file.

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "chore: remove combined SDQL-only NCAAB seed job"
```

---

## Self-Review Notes

- **Spec coverage:** `odds_event_id` migration → Task 1. Team-name mapping fixes → Task 2 (bundled, as decided). Two-job hybrid architecture, scope-via-roster filtering, dual-source scores, neutral-site handling, lenient policies, half/OT enrichment → Task 3 (primary) and Task 4 (fallback), each matching its row in the spec's field-mapping table. The orientation-agnostic duplicate guard and in-memory dedupe are built into Task 4 from its first version, matching the spec's explicit "preserved from the start" decision. Old job deletion → Task 5.
- **Placeholder scan:** no TBD/TODO; every step has runnable code or a concrete command with a stated expected result. Task 2's fix list is given as concrete starting-point guidance (which names to investigate and how) with an explicit instruction to re-verify against current state, not a vague "fix the mappings" directive.
- **Type consistency:** Task 3's `odds_event_id`/`game_site`/`home_qs`/`away_qs`/half-point variables all flow consistently from ESPN event parsing through to the INSERT's bound params, using direct indexing (not summing) per the Global Constraints. Task 4's `params` dict is built once per deduped candidate and reused identically across both the `UPDATE ... COALESCE` and `INSERT` branches — same keys, same types. Both jobs independently compute `odds_event_id`/no-`odds_event_id` consistent with the constraint that only Task 3's job ever sets it.
- **Cross-task dependency check:** Task 4's job is written to be safe to run whether or not Task 3's job already inserted a row for a given game (the exact/reversed-match checks handle both cases), and its dedupe-then-both-orientations-check design was carried over deliberately from the real bug found and fixed during the NCAAF migration — not re-derived from scratch and not left for the review loop to catch a second time.
