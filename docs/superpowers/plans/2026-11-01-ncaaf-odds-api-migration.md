# NCAAF Odds-API-and-ESPN Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `odds_event_id` column to `ncaaf_games`, fix the pre-existing NCAAF team-name mapping bugs in `shared_utils.py`, then build two new scheduled jobs — `jobs/ncaaf_odds_api_seed_yesterdays_games.py` (Odds API + ESPN, primary) and `jobs/ncaaf_sdql_fallback_fill.py` (SDQL, fills only what's still NULL) — replacing the single SDQL-only `jobs/ncaaf_seed_yesterdays_games.py`.

**Architecture:** One migration, one shared-file name-mapping fix, two new job files, one deletion. Job 1 drives off ESPN's combined `groups=90`+`groups=81` scoreboard (the only reliable schedule-discovery source for this sport, confirmed during design — `/teams` does not respect `groups`), enriches with Odds API where available, and uses our existing `teams` table as the scope filter rather than trying to interpret ESPN's division semantics. Job 2 reuses the current job's proven SDQL-fetching logic unchanged, but fills gaps via `COALESCE` instead of inserting fresh rows.

**Tech Stack:** Python, `requests` (Odds API + ESPN + SDQL), `sqlalchemy` (`create_engine`/`text`), `shared_utils.convert_team_name`/`convert_to_eastern`, `alembic`.

**Spec:** `docs/superpowers/specs/2026-11-01-ncaaf-odds-api-migration-design.md`

## Global Constraints

- Job 1 (Odds API+ESPN) never drops a game over missing odds or failed enrichment — same lenient policy as NFL/NBA.
- Job 2 (SDQL) never overwrites a non-NULL value on an existing row — it only fills gaps, via `COALESCE(existing, new)` on every column it touches.
- Job 1's scope filter is our existing `teams WHERE sport='NCAAF'` roster via `convert_team_name` — not ESPN's `groups` semantics. A team that doesn't resolve to an existing roster row is silently skipped.
- `game_site` is derived from ESPN's `neutralSite` flag in job 1 (same as NFL, NOT NBA's hardcoded `'home'`); job 2 uses SDQL's own `site` field, only when still NULL.
- `odds_event_id` is only ever set by job 1 — job 2 never sets it (SDQL has no equivalent id).
- `home_quarter_scores`/`away_quarter_scores` are JSON-typed columns — must be `json.dumps()`'d before binding (confirmed bug class from the NFL/NBA migrations).
- `DATABASE_URL` needs the `postgres://` → `postgresql://` replacement used everywhere else in `jobs/`.

---

### Task 1: Add `odds_event_id` migration for `ncaaf_games`

**Files:**
- Create: `migrations/versions/<new_revision>_add_odds_event_id_to_ncaaf_games.py`

**Interfaces:**
- Produces: a new nullable `odds_event_id` column + unique constraint `uq_ncaaf_games_odds_event_id` on `ncaaf_games`, consumed by Task 3's job.

- [ ] **Step 1: Generate and fill in the migration**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/ncaaf-odds-api-migration && ./venv/bin/python -m alembic revision -m "add_odds_event_id_to_ncaaf_games"`

Replace the generated file's docstring and `upgrade`/`downgrade` functions with:

```python
"""add_odds_event_id_to_ncaaf_games

Mirrors fd711e7e2b11 (same column added to nba_games_1) and a7c2e9f4b1d3
(nfl_games) - lays the groundwork for seeding ncaaf_games from the Odds API
scores endpoint instead of SportsDatabase/SDQL.
"""


def upgrade() -> None:
    op.add_column('ncaaf_games', sa.Column('odds_event_id', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_ncaaf_games_odds_event_id', 'ncaaf_games', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_ncaaf_games_odds_event_id', 'ncaaf_games', type_='unique')
    op.drop_column('ncaaf_games', 'odds_event_id')
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
    row = conn.execute(text(\"SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'ncaaf_games' AND column_name = 'odds_event_id'\")).fetchone()
    print('column:', row)
    idx = conn.execute(text(\"SELECT indexname FROM pg_indexes WHERE tablename = 'ncaaf_games' AND indexname LIKE '%odds_event_id%'\")).fetchall()
    print('constraint/index:', idx)
"
```
Expected: `column: ('odds_event_id', 'YES')` and a non-empty constraint/index list.

- [ ] **Step 3: Commit**

```bash
git add migrations/versions/<the new migration file>
git commit -m "feat: add odds_event_id column to ncaaf_games"
```

---

### Task 2: Fix NCAAF team-name mapping bugs in `shared_utils.py`

**Files:**
- Modify: `shared_utils.py` (the `#NCAA Football` section, currently starting around line 451)

**Interfaces:**
- Produces: corrected/added entries in `convert_team_name`'s NCAAF section, consumed by both Task 3 and Task 4's matching logic (Task 4 doesn't call `convert_team_name` for SDQL matching, but Task 3 and the data-integrity-report job both depend on this section being accurate).

- [ ] **Step 1: Re-run the reconciliation script to get the current real mismatch list**

Repo state may have shifted since this plan was written — re-derive the list fresh rather than trusting the brief's copy of it. Run:
```bash
cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/ncaaf-odds-api-migration
./venv/bin/python3 -c "
import os, sys, requests
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import shared_utils
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
with engine.connect() as conn:
    db_teams = set(r[0] for r in conn.execute(text(\"SELECT team_name FROM teams WHERE sport = 'NCAAF'\")).fetchall())

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
dates = ['20260905', '20260912', '20260919', '20260926', '20261003', '20261010', '20261017']
all_names = set()
for d in dates:
    for g in [90, 81]:
        r = requests.get('https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard',
                          headers=UA, params={'dates': d, 'limit': 400, 'groups': g}, timeout=20)
        for e in r.json().get('events', []):
            if e.get('status', {}).get('type', {}).get('name') != 'STATUS_FINAL':
                continue
            for c in e['competitions'][0]['competitors']:
                all_names.add(c['team']['displayName'])

matched, unmatched = 0, []
for name in sorted(all_names):
    short = shared_utils.convert_team_name(name)
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

For each unmatched name, decide: is this a team we already track under a different spelling (fix the dict), or a genuinely out-of-scope Division II/III/NAIA school (leave it unmatched — do not add an entry for it). The following fixes were confirmed correct during design research and should be applied as a starting point — re-verify each against the current file before editing, since line numbers and exact existing wording may have shifted:

- Fix `'Hawaii Rainbow Warriors': 'HAW'` → add `"Hawai'i Rainbow Warriors": 'HAW'` (keep or remove the no-apostrophe version; ESPN's current spelling has the apostrophe)
- Fix: `'UMass Minutemen': 'MAS'` → add `'Massachusetts Minutemen': 'MAS'`
- Fix: `'Southern Mississippi Golden Eagles': 'SMIS'` → add `'Southern Miss Golden Eagles': 'SMIS'`
- Fix: `'Campbell Camels': 'CAMP'` → add `'Campbell Fighting Camels': 'CAMP'`
- Fix: `'Gardner-Webb Bulldogs': 'GARD'` → add `"Gardner-Webb Runnin' Bulldogs": 'GARD'`
- Fix: `'Presbyterian College Blue Hose': 'PRES'` → add `'Presbyterian Blue Hose': 'PRES'`
- Fix: `'Prairie View Panthers': 'PRVW'` → add `'Prairie View A&M Panthers': 'PRVW'`
- Fix: `'San Jose State Spartans': 'SJST'` → add `'San José State Spartans': 'SJST'`
- Fix: `'Southeast Missouri State Red Hawks': 'SEMST'` → add `'Southeast Missouri State Redhawks': 'SEMST'`
- Fix: `'Florida International Golden Panthers': 'FINT'` → add `'Florida International Panthers': 'FINT'`
- Fix: `'Connecticut Huskies': 'CON'` → add `'UConn Huskies': 'CON'`
- Fix: `'Albany Great Danes': 'ALBS'` → add `'UAlbany Great Danes': 'ALBS'`
- Fix: `'Appalachian State Mountaineers': 'APP'` → add `'App State Mountaineers': 'APP'`
- Fix: `'Sam Houston State Bearkats': 'SHST'` → add `'Sam Houston Bearkats': 'SHST'`
- Fix: `'Texas A&M-Commerce Lions': 'TXAMC'` → add `'East Texas A&M Lions': 'TXAMC'` (school renamed; keep the old entry too in case any historical data still uses the old name)
- Fix: `'Tarleton State': 'TARL'` → change this entry's key to `'Tarleton State Texans': 'TARL'` (the old key is missing the mascot word and so never matches ESPN's full name)
- For `'Miami (OH) RedHawks'`: run `SELECT team_id, team_name FROM teams WHERE sport='NCAAF' AND team_name ILIKE '%miami%oh%' OR team_name ILIKE '%MIAO%'` to find the actual stored short code for this school, then confirm or fix the dict's `'Miami (OH) RedHawks': 'MIAOH'` entry to match exactly what's stored (the dict and the DB may disagree by one character).

For every other name in the Step 1 output not listed above: investigate briefly (is it a Division II/III/NAIA/small-conference school not in our 259-team roster?) — if so, leave it alone, don't add a mapping. Do not spend more than a glance per entry; the goal is catching real misses, not auditing every small school.

- [ ] **Step 3: Re-run the Step 1 script and verify the fixes landed**

Re-run the exact script from Step 1. Expected: the `Matched` count increases by roughly the number of real fixes applied in Step 2 (don't expect an exact match to any specific number — re-derive and sanity-check, don't force a target). Spot-check that the entries you fixed no longer appear in the `Unmatched` list, and that what remains unmatched still looks like genuine small-school/Division II noise (eyeball a handful of names), not more real teams.

- [ ] **Step 4: Run the full test suite**

Run: `./venv/bin/python -m pytest tests/ -q`
Expected: 158 passed (or whatever the current baseline is at run time) — this is a shared file used across every sport, so a regression here would show up broadly.

- [ ] **Step 5: Commit**

```bash
git add shared_utils.py
git commit -m "fix: correct NCAAF team-name mappings in convert_team_name for ESPN's current naming"
```

---

### Task 3: Build and verify `jobs/ncaaf_odds_api_seed_yesterdays_games.py`

**Files:**
- Create: `jobs/ncaaf_odds_api_seed_yesterdays_games.py`

**Interfaces:**
- Consumes: `ncaaf_games.odds_event_id` (Task 1), corrected `shared_utils.convert_team_name` (Task 2).
- Produces: `get_completed_ncaaf_games_for_date`, `get_historical_odds_for_date`, `get_espn_games_for_date`, `_market_from_preferred_bookmaker`, `parse_odds_data`, `seed_yesterdays_ncaaf_games`.

- [ ] **Step 1: Write the complete job file**

```python
#!/usr/bin/env python3
"""Seed yesterday's NCAAF games from ESPN (schedule discovery + score/
enrichment fallback) and Odds API (score + lines where available).

ESPN drives discovery (groups=90 FBS + groups=81 broad -- the only
reliable division-aware source for this sport; /teams does not respect
groups the way /scoreboard does). A game is only processed if BOTH teams
resolve, via convert_team_name, to an existing row in
`teams WHERE sport='NCAAF'` -- our own 259-team roster is the scope filter,
not ESPN's division semantics (groups=81 also returns Division II/III/NAIA
noise we've never tracked).

Odds API enriches with real lines where it has the game (effectively all
FBS, occasional marquee FCS); ESPN's own competitor.score is the fallback
final score for games Odds API doesn't track at all (most FCS games).
A second, later-scheduled job (jobs/ncaaf_sdql_fallback_fill.py) fills
remaining gaps from SDQL -- this job never calls SDQL.
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


def get_completed_ncaaf_games_for_date(target_date_str: str, retries=3, delay=2):
    """Odds API current (non-historical) scores for the last 3 days,
    filtered to games whose Eastern-converted commence date matches
    target_date_str. Returns the raw list of Odds API game dicts."""
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/scores/"
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
    url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_ncaaf/odds"
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
    """ESPN scoreboard for date_str, groups=90 (FBS) + groups=81 (broad --
    includes real FCS plus Division II/III/NAIA noise filtered out later
    by the caller via the teams-roster check). Returns deduped raw event
    dicts (STATUS_FINAL only)."""
    date_compact = date_str.replace("-", "")
    all_events = []
    seen_ids = set()
    for group in (90, 81):
        for i in range(retries):
            try:
                resp = requests.get(
                    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
                    params={"dates": date_compact, "limit": 400, "groups": group},
                    headers=ESPN_HEADERS, timeout=30,
                )
                resp.raise_for_status()
                events = resp.json().get("events", [])
                break
            except requests.exceptions.RequestException as e:
                print(f"  ESPN scoreboard fetch failed (groups={group}, attempt {i+1}/{retries}): {e}")
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    events = []
        for e in events:
            if e.get("status", {}).get("type", {}).get("name") != "STATUS_FINAL":
                continue
            eid = e.get("id")
            if eid in seen_ids:
                continue
            seen_ids.add(eid)
            all_events.append(e)
    return all_events


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


def seed_yesterdays_ncaaf_games():
    print("Starting NCAAF game seeding (ESPN discovery + Odds API enrichment)...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

        espn_events = get_espn_games_for_date(yesterday)
        if not espn_events:
            print(f"No completed NCAAF games found on ESPN for {yesterday}")
            return

        odds_games = get_completed_ncaaf_games_for_date(yesterday)
        odds_lookup_by_teams = {}
        for g in odds_games:
            db_h = shared_utils.convert_team_name(g["home_team"])
            db_a = shared_utils.convert_team_name(g["away_team"])
            odds_lookup_by_teams[(db_h, db_a)] = g

        odds_data = get_historical_odds_for_date(yesterday)
        odds_info_by_event_id = {g["id"]: g for g in odds_data}

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAF'")).mappings()
        }

        inserted = 0
        for event in espn_events:
            comp = event["competitions"][0]
            home_c = next((c for c in comp["competitors"] if c.get("homeAway") == "home"), {})
            away_c = next((c for c in comp["competitors"] if c.get("homeAway") == "away"), {})
            espn_home_name = home_c.get("team", {}).get("displayName", "")
            espn_away_name = away_c.get("team", {}).get("displayName", "")

            db_home = shared_utils.convert_team_name(espn_home_name)
            db_away = shared_utils.convert_team_name(espn_away_name)
            home_team_id = teams_dict.get(db_home)
            away_team_id = teams_dict.get(db_away)
            if home_team_id is None or away_team_id is None:
                continue  # out of our tracked scope (Division II/III/NAIA leakage) -- silently skip

            odds_game = odds_lookup_by_teams.get((db_home, db_away))
            odds_event_id = odds_game["id"] if odds_game else None

            if odds_game:
                home_points = away_points = None
                for score in odds_game["scores"]:
                    name = shared_utils.convert_team_name(score["name"])
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
                SELECT 1 FROM ncaaf_games
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
            game_site = None if neutral_site is None else ("neutral" if neutral_site else "home")

            home_qs = [int(ls.get("displayValue", 0)) for ls in home_c.get("linescores", [])] or None
            away_qs = [int(ls.get("displayValue", 0)) for ls in away_c.get("linescores", [])] or None
            if home_qs and away_qs:
                home_first_half = sum(home_qs[:2])
                away_first_half = sum(away_qs[:2])
                home_second_half = sum(home_qs[2:4])
                away_second_half = sum(away_qs[2:4])
                home_overtime = home_qs[4] if len(home_qs) > 4 else None
                away_overtime = away_qs[4] if len(away_qs) > 4 else None
            else:
                home_first_half = away_first_half = None
                home_second_half = away_second_half = None
                home_overtime = away_overtime = None

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
                INSERT INTO ncaaf_games (
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
        print(f"Seeded {inserted} NCAAF game(s) for {yesterday}")
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_ncaaf_games()
```

- [ ] **Step 2: Run it against real data and sanity-check**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/ncaaf-odds-api-migration && ./venv/bin/python jobs/ncaaf_odds_api_seed_yesterdays_games.py`

(Symlink `./venv`/`.env` from the main checkout first if they don't exist in this worktree.)

Expected: a mix of `Inserting:`/`Already seeded:`/skip lines, ending with `Seeded N NCAAF game(s) for <date>`, no unhandled exception. If "yesterday" has zero games (off-season or a date with no games), temporarily hardcode a known in-season date with real games for a one-off manual verification run, then revert the hardcode before committing — same approach used for NFL/NBA's verification.

For at least one inserted game with `odds_event_id` set (an FBS game), confirm `home_line`/`away_line` look like real spread numbers, not moneyline-sized numbers. For at least one inserted game with `odds_event_id` NULL (a smaller/FCS game Odds API didn't track), confirm the score and quarter-scores are still populated via ESPN, and that `home_line`/`away_line`/`total`/money-lines are NULL (expected — job 2 fills these later) rather than the job having skipped the game entirely.

- [ ] **Step 3: Commit**

```bash
git add jobs/ncaaf_odds_api_seed_yesterdays_games.py
git commit -m "feat: add NCAAF games seed job sourced from ESPN + Odds API"
```

---

### Task 4: Build and verify `jobs/ncaaf_sdql_fallback_fill.py`

**Files:**
- Create: `jobs/ncaaf_sdql_fallback_fill.py`

**Interfaces:**
- Consumes: rows already inserted by Task 3's job for the same date (if job 1 hasn't run yet for a given date, this job's `COALESCE`-based fill simply has nothing to fill and the row-doesn't-exist INSERT path handles it instead).
- Produces: `get_yesterdays_sdql_games`, `convert_sdql_start_time_to_time`, `fill_yesterdays_ncaaf_games_from_sdql`.

- [ ] **Step 1: Write the complete script**

This reuses the current `jobs/ncaaf_seed_yesterdays_games.py`'s SDQL-fetching logic essentially unchanged (same query, same parsing) — only the persistence step changes, from "insert, skip if a duplicate exists" to "update only-if-NULL via COALESCE, insert only if the row doesn't exist at all."

```python
#!/usr/bin/env python3
"""Fallback fill for NCAAF games: fetches yesterday's games from SDQL (the
same query the old jobs/ncaaf_seed_yesterdays_games.py used) and fills in
ONLY whatever is still NULL on the matching ncaaf_games row -- never
overwrites a value jobs/ncaaf_odds_api_seed_yesterdays_games.py already
supplied. If a game is missing entirely (rare -- ESPN's broad scoreboard
should have caught nearly everything SDQL finds), inserts it fresh from
SDQL with odds_event_id left NULL.

Scheduled to run AFTER jobs/ncaaf_odds_api_seed_yesterdays_games.py, later
in the day (SDQL's data becomes reliably available later than Odds API's).
"""
import os
import sys
import json
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


def convert_sdql_start_time_to_time(start_time):
    try:
        if start_time is None:
            return None
        start_time_str = str(start_time)
        if len(start_time_str) == 3:
            start_time_str = '0' + start_time_str
        if len(start_time_str) == 4:
            hour = int(start_time_str[:2])
            minute = int(start_time_str[2:])
            return f"{hour:02d}:{minute:02d}:00"
        return None
    except (ValueError, TypeError):
        return None


def get_yesterdays_sdql_games(retries=3, delay=1):
    """Same SDQL query the old job used -- unchanged."""
    sdql_url = "https://s3.sportsdatabase.com/NCAAFB/query"
    today = datetime.today().strftime('%Y%m%d')
    two_days_ago = (datetime.today() - timedelta(days=2)).strftime('%Y%m%d')
    sdql_query = (
        f"date,site,team,o:team,points,o:points,total,margin,line,o:line,"
        f"quarter scores,o:quarter scores,playoffs,money line,o:money line,start time,_t"
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


def fill_yesterdays_ncaaf_games_from_sdql():
    print("Starting NCAAF SDQL fallback fill...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        games = get_yesterdays_sdql_games()
        print(f"Fetched {len(games)} SDQL games to use as fallback data")

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAF'")).mappings()
        }

        filled = 0
        inserted = 0
        for game in games:
            if game.get('points') is None or game.get('o:points') is None:
                continue

            home_team_id = teams_dict.get(game['team'])
            away_team_id = teams_dict.get(game['o:team'])
            if home_team_id is None or away_team_id is None:
                continue

            try:
                home_qs = json.loads(game['quarter scores']) if game.get('quarter scores') else None
                away_qs = json.loads(game['o:quarter scores']) if game.get('o:quarter scores') else None
            except (TypeError, json.JSONDecodeError):
                home_qs = away_qs = None

            if home_qs and away_qs:
                home_first_half = sum(home_qs[:2])
                away_first_half = sum(away_qs[:2])
                home_second_half = sum(home_qs[2:4])
                away_second_half = sum(away_qs[2:4])
                home_overtime = home_qs[4] if len(home_qs) > 4 else None
                away_overtime = away_qs[4] if len(away_qs) > 4 else None
            else:
                home_first_half = away_first_half = None
                home_second_half = away_second_half = None
                home_overtime = away_overtime = None

            start_time_raw = game.get('start time')
            start_time = None
            if start_time_raw and start_time_raw != 0:
                start_time = convert_sdql_start_time_to_time(str(start_time_raw))

            total_value = game['total'] if game.get('total') not in (None, '-') else None
            home_money = game.get('money line') if isinstance(game.get('money line'), int) else None
            away_money = game.get('o:money line') if isinstance(game.get('o:money line'), int) else None

            existing = conn.execute(text("""
                SELECT game_id FROM ncaaf_games
                WHERE game_date = :game_date AND home_team_id = :home_team_id AND away_team_id = :away_team_id
            """), {
                "game_date": game['date'], "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()

            params = {
                "game_date": game['date'], "game_site": game.get('site'),
                "home_team_id": home_team_id, "away_team_id": away_team_id,
                "home_team_name": game['team'], "away_team_name": game['o:team'],
                "home_points": game['points'], "away_points": game['o:points'],
                "total_points": game['points'] + game['o:points'], "total_margin": game.get('margin'),
                "home_line": game.get('line'), "away_line": game.get('o:line'),
                "home_quarter_scores": json.dumps(home_qs) if home_qs is not None else None,
                "away_quarter_scores": json.dumps(away_qs) if away_qs is not None else None,
                "home_first_half_points": home_first_half, "away_first_half_points": away_first_half,
                "home_second_half_points": home_second_half, "away_second_half_points": away_second_half,
                "home_overtime_points": home_overtime, "away_overtime_points": away_overtime,
                "home_money_line": home_money, "away_money_line": away_money,
                "playoffs": bool(game.get('playoffs', 0)), "start_time": start_time, "total": total_value,
            }

            if existing:
                conn.execute(text("""
                    UPDATE ncaaf_games SET
                        game_site = COALESCE(game_site, :game_site),
                        home_points = COALESCE(home_points, :home_points),
                        away_points = COALESCE(away_points, :away_points),
                        total_points = COALESCE(total_points, :total_points),
                        total_margin = COALESCE(total_margin, :total_margin),
                        home_line = COALESCE(home_line, :home_line),
                        away_line = COALESCE(away_line, :away_line),
                        home_quarter_scores = COALESCE(home_quarter_scores, :home_quarter_scores),
                        away_quarter_scores = COALESCE(away_quarter_scores, :away_quarter_scores),
                        home_first_half_points = COALESCE(home_first_half_points, :home_first_half_points),
                        away_first_half_points = COALESCE(away_first_half_points, :away_first_half_points),
                        home_second_half_points = COALESCE(home_second_half_points, :home_second_half_points),
                        away_second_half_points = COALESCE(away_second_half_points, :away_second_half_points),
                        home_overtime_points = COALESCE(home_overtime_points, :home_overtime_points),
                        away_overtime_points = COALESCE(away_overtime_points, :away_overtime_points),
                        home_money_line = COALESCE(home_money_line, :home_money_line),
                        away_money_line = COALESCE(away_money_line, :away_money_line),
                        playoffs = COALESCE(playoffs, :playoffs),
                        start_time = COALESCE(start_time, :start_time),
                        total = COALESCE(total, :total)
                    WHERE game_id = :game_id
                """), {**params, "game_id": existing[0]})
                filled += 1
            else:
                conn.execute(text("""
                    INSERT INTO ncaaf_games (
                        game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                        home_points, away_points, total_points, total_margin, home_line, away_line,
                        home_quarter_scores, away_quarter_scores, home_first_half_points, away_first_half_points,
                        home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                        home_money_line, away_money_line, playoffs, start_time, total
                    ) VALUES (
                        :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                        :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                        :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                        :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points,
                        :home_money_line, :away_money_line, :playoffs, :start_time, :total
                    )
                """), params)
                inserted += 1

        conn.commit()
        print(f"Done. Rows filled (existing, NULL-only): {filled}. Rows inserted fresh: {inserted}.")
    except Exception as e:
        print(f"Error during SDQL fallback fill: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    fill_yesterdays_ncaaf_games_from_sdql()
```

- [ ] **Step 2: Run it against real data and verify the fill behavior**

Run: `./venv/bin/python jobs/ncaaf_sdql_fallback_fill.py`

Expected: console output ending with `Done. Rows filled (existing, NULL-only): N. Rows inserted fresh: M.`, no unhandled exception.

Verify the COALESCE behavior directly: pick one row that Task 3's job inserted with `home_line`/`total` NULL (a game Odds API didn't track), confirm this job filled those columns with real SDQL values. Then verify non-destructiveness: pick a row that Task 3's job inserted WITH a real `home_line` already set (an FBS game), re-run this fallback job, and confirm that value is unchanged afterward (COALESCE should have left it alone) — this is the single most important behavior to verify given the "never overwrite" constraint.

```bash
./venv/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
with engine.connect() as conn:
    rows = conn.execute(text(\"SELECT game_id, home_team_name, away_team_name, home_line, total, odds_event_id FROM ncaaf_games ORDER BY game_date DESC, game_id LIMIT 20\")).fetchall()
    for r in rows:
        print(r)
"
```

- [ ] **Step 3: Commit**

```bash
git add jobs/ncaaf_sdql_fallback_fill.py
git commit -m "feat: add SDQL fallback-fill job for NCAAF games"
```

---

### Task 5: Delete the old combined SDQL job

**Files:**
- Delete: `jobs/ncaaf_seed_yesterdays_games.py`

**Interfaces:** none — Tasks 3 and 4 together fully replace this file's functionality (schedule discovery + enrichment + SDQL fallback), confirmed via their own verification steps.

- [ ] **Step 1: Confirm zero live callers right before deleting**

Run: `grep -rln "ncaaf_seed_yesterdays_games" --include="*.py" .`
Expected: no output (only the two new job files' docstrings may mention it by name as a historical reference — if so, that's fine, it's a comment, not a live import).

- [ ] **Step 2: Delete the file**

```bash
git rm jobs/ncaaf_seed_yesterdays_games.py
```

- [ ] **Step 3: Confirm nothing else broke**

Run: `./venv/bin/python -m pytest tests/ -q` — expect the current baseline pass count, zero new failures.
Run: `./venv/bin/python -c "import app"` — expect clean exit, no import errors.

- [ ] **Step 4: Re-run both new jobs once more post-cleanup as a final regression check**

```bash
./venv/bin/python jobs/ncaaf_odds_api_seed_yesterdays_games.py
./venv/bin/python jobs/ncaaf_sdql_fallback_fill.py
```
Expected: same clean behavior as their own task's verification — confirms neither job secretly depended on the deleted file.

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "chore: remove combined SDQL-only NCAAF seed job"
```

---

## Self-Review Notes

- **Spec coverage:** `odds_event_id` migration → Task 1. Team-name mapping fixes → Task 2 (bundled, as decided). Two-job hybrid architecture, scope-via-roster filtering, dual-source scores, neutral-site handling, lenient policies → Task 3 (primary) and Task 4 (fallback), each matching its row in the spec's field-mapping table. Old job deletion → Task 5. The 2026-10-24 data gap is explicitly NOT addressed anywhere in this plan, matching the spec's "out of scope" call.
- **Placeholder scan:** no TBD/TODO; every step has runnable code or a concrete command with a stated expected result. Task 2's fix list is given as concrete starting-point edits with an explicit instruction to re-verify against current state, not a vague "fix the mappings" directive.
- **Type consistency:** Task 3's `odds_event_id`/`game_site`/`home_qs`/`away_qs` all flow consistently from ESPN event parsing through to the INSERT's bound params. Task 4's `params` dict is built once and reused identically across both the `UPDATE ... COALESCE` and `INSERT` branches — same keys, same types, confirmed by inspection of both SQL statements' bound-parameter lists. Both jobs independently compute `odds_event_id`/no-`odds_event_id` consistent with the constraint that only Task 3's job ever sets it.
- **Cross-task dependency check:** Task 4's job is written to be safe to run whether or not Task 3's job already inserted a row for a given game (the `existing` check handles both cases) — this was deliberately verified against the "job 2 runs later in the day" scheduling requirement from the spec, not assumed.
