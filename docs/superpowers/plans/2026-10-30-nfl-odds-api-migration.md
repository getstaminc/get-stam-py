# NFL Odds-API-and-ESPN Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the SDQL-sourced NFL games job (`jobs/nfl_seed_yesterdays_games.py`) with a new Odds API + ESPN job (`jobs/nfl_odds_api_seed_yesterdays_games.py`), then delete the old job and the now-fully-orphaned SDQL helper code.

**Architecture:** Single new job file, structured identically to the already-live `jobs/nhl_odds_api_seed_yesterdays_games.py` (Odds API live `scores` for the final score, Odds API historical `odds` for moneyline/spread/total, ESPN `scoreboard`+`summary` for quarter scores/neutral-site/playoffs/OT) — then a second task deletes the old job and the SDQL-only dead code cluster once the new job is verified against live data.

**Tech Stack:** Python, `requests` (Odds API + ESPN), `sqlalchemy` (`create_engine`/`text`), `shared_utils.convert_team_name`/`convert_to_eastern`.

**Spec:** `docs/superpowers/specs/2026-10-30-nfl-odds-api-migration-design.md`

## Global Constraints

- Go-forward only — no backfill, no change to existing `nfl_games` rows.
- Always insert a game once the final score is known; leave odds-derived columns (`home_line`/`away_line`/`total`/`home_money_line`/`away_money_line`) NULL if a market is unavailable, never skip the whole game over missing pricing.
- If ESPN enrichment can't be matched for a game, insert with `home/away_quarter_scores`, `game_site`, `playoffs` left NULL rather than dropping the game.
- Bookmaker selection: prefer DraftKings per market; if DraftKings doesn't carry a given market for that event, use the first bookmaker in the API response's `bookmakers` array (response order) that does.
- No new migration, no new ORM model — `nfl_games.odds_event_id` and its unique constraint already exist.
- `DATABASE_URL` needs the `postgres://` → `postgresql://` replacement used everywhere else in `jobs/`.

---

### Task 1: Build and verify `jobs/nfl_odds_api_seed_yesterdays_games.py`

**Files:**
- Create: `jobs/nfl_odds_api_seed_yesterdays_games.py`

**Interfaces:**
- Produces: `get_completed_nfl_games_for_date(date_str) -> list[dict]`, `get_historical_odds_for_date(date_str) -> list[dict]`, `parse_odds_data(odds_game) -> dict`, `get_espn_enrichment(date_str, home, away) -> dict`, `seed_yesterdays_nfl_games()`.

- [ ] **Step 1: Write the complete job file**

```python
#!/usr/bin/env python3
"""Seed yesterday's NFL games from the Odds API, enriched with ESPN data for
fields the Odds API doesn't provide (quarter scores, neutral-site flag,
playoffs, overtime). Replaces the SDQL-based jobs/nfl_seed_yesterdays_games.py.
"""
import os
import sys
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


def get_completed_nfl_games_for_date(target_date_str: str, retries=3, delay=2):
    """Odds API current (non-historical) scores for the last 3 days, filtered
    to games whose Eastern-converted commence date matches target_date_str."""
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores/"
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
            print(f"Error fetching scores (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
    return []


def get_historical_odds_for_date(date_str: str, retries=3, delay=2):
    """Historical h2h/spreads/totals odds for a date (yesterday's market has
    closed by the time this job runs, so the current-odds endpoint won't
    have it). No bookmakers filter here — parse_odds_data picks per-market."""
    url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_nfl/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "date": f"{date_str}T00:00:00Z",
    }
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def _market_from_preferred_bookmaker(bookmakers, market_key, preferred="draftkings"):
    """Return the named market dict from the preferred bookmaker if it has
    one, else from the first bookmaker (response order) that does."""
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
    """Extract moneyline, spread, and total — each market independently
    sourced per _market_from_preferred_bookmaker's fallback rule."""
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


def get_espn_enrichment(target_date_str: str, home_team: str, away_team: str) -> dict:
    """Fetch ESPN's NFL summary for the game matching home_team/away_team on
    target_date_str. Returns an all-None dict if the ESPN game can't be
    matched or any request fails — enrichment is never allowed to drop the
    game itself, only to be missing."""
    empty = {
        "home_quarter_scores": None, "away_quarter_scores": None,
        "neutral_site": None, "playoffs": None, "overtime_detail": None,
    }
    date_compact = target_date_str.replace("-", "")
    try:
        resp = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
            params={"dates": date_compact, "limit": 50}, headers=ESPN_HEADERS, timeout=30,
        )
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except requests.exceptions.RequestException as e:
        print(f"  ESPN scoreboard fetch failed: {e}")
        return empty

    espn_event_id = None
    for event in events:
        comp = event.get("competitions", [{}])[0]
        competitors = {c.get("homeAway"): c.get("team", {}).get("displayName") for c in comp.get("competitors", [])}
        espn_home = shared_utils.convert_team_name(competitors.get("home", ""))
        espn_away = shared_utils.convert_team_name(competitors.get("away", ""))
        if espn_home == home_team and espn_away == away_team:
            espn_event_id = event.get("id")
            break

    if not espn_event_id:
        print(f"  Could not match ESPN event for {away_team} @ {home_team} on {target_date_str}")
        return empty

    try:
        resp = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary",
            params={"event": espn_event_id, "enable": "boxscore"}, headers=ESPN_HEADERS, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  ESPN summary fetch failed for event {espn_event_id}: {e}")
        return empty

    try:
        header = data.get("header", {})
        comp = header.get("competitions", [{}])[0]
        season_type = header.get("season", {}).get("type")
        status_detail = comp.get("status", {}).get("type", {}).get("detail", "")
        neutral_site = comp.get("neutralSite")

        home_quarter_scores = away_quarter_scores = None
        for competitor in comp.get("competitors", []):
            scores = [int(ls.get("displayValue", 0)) for ls in competitor.get("linescores", [])]
            if competitor.get("homeAway") == "home":
                home_quarter_scores = scores
            elif competitor.get("homeAway") == "away":
                away_quarter_scores = scores

        return {
            "home_quarter_scores": home_quarter_scores,
            "away_quarter_scores": away_quarter_scores,
            "neutral_site": bool(neutral_site) if neutral_site is not None else None,
            "playoffs": (season_type == 3) if season_type is not None else None,
            "overtime_detail": status_detail,
        }
    except (KeyError, ValueError, TypeError) as e:
        print(f"  ESPN summary parse failed for event {espn_event_id}: {e}")
        return empty


def seed_yesterdays_nfl_games():
    print("Starting NFL game seeding (Odds API + ESPN)...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        games = get_completed_nfl_games_for_date(yesterday)
        if not games:
            print(f"No completed NFL games found for {yesterday}")
            return

        odds_data = get_historical_odds_for_date(yesterday)
        odds_lookup = {g["id"]: g for g in odds_data}

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NFL'")).mappings()
        }

        inserted = 0
        for game in games:
            db_home = shared_utils.convert_team_name(game["home_team"])
            db_away = shared_utils.convert_team_name(game["away_team"])
            home_team_id = teams_dict.get(db_home)
            away_team_id = teams_dict.get(db_away)
            if home_team_id is None or away_team_id is None:
                print(f"Skipping {game['away_team']} @ {game['home_team']} - unresolved team id")
                continue

            home_points = away_points = None
            for score in game["scores"]:
                db_name = shared_utils.convert_team_name(score["name"])
                if db_name == db_home:
                    home_points = int(score["score"])
                elif db_name == db_away:
                    away_points = int(score["score"])
            if home_points is None or away_points is None:
                print(f"Skipping {game['away_team']} @ {game['home_team']} - missing score")
                continue

            existing = conn.execute(text("""
                SELECT 1 FROM nfl_games
                WHERE odds_event_id = :odds_event_id
                   OR (game_date = :game_date AND home_team_name = :home AND away_team_name = :away)
            """), {
                "odds_event_id": game["id"], "game_date": yesterday,
                "home": db_home, "away": db_away,
            }).fetchone()
            if existing:
                print(f"Already seeded: {db_away} @ {db_home} on {yesterday}")
                continue

            odds_info = parse_odds_data(odds_lookup.get(game["id"], {}))
            enrichment = get_espn_enrichment(yesterday, db_home, db_away)

            home_qs = enrichment["home_quarter_scores"]
            away_qs = enrichment["away_quarter_scores"]
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

            game_site = "neutral" if enrichment["neutral_site"] else "home"
            commence_utc = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
            start_time = shared_utils.convert_to_eastern(commence_utc).time()

            print(f"Inserting: {db_away} {away_points} @ {db_home} {home_points} on {yesterday}")

            conn.execute(text("""
                INSERT INTO nfl_games (
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
                "home_quarter_scores": home_qs, "away_quarter_scores": away_qs,
                "home_first_half_points": home_first_half, "away_first_half_points": away_first_half,
                "home_second_half_points": home_second_half, "away_second_half_points": away_second_half,
                "home_overtime_points": home_overtime, "away_overtime_points": away_overtime,
                "home_money_line": odds_info["home_money_line"], "away_money_line": odds_info["away_money_line"],
                "playoffs": enrichment["playoffs"], "start_time": start_time,
                "total": odds_info["total"], "odds_event_id": game["id"],
            })
            inserted += 1

        conn.commit()
        print(f"Seeded {inserted} NFL game(s) for {yesterday}")
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_nfl_games()
```

- [ ] **Step 2: Run it against real data and sanity-check the output**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/nfl-odds-api-migration && ./venv/bin/python jobs/nfl_odds_api_seed_yesterdays_games.py`

(If `./venv` doesn't exist in this worktree, symlink it and `.env` from the main checkout first: `ln -s /Users/stephaniegillen/Projects/get-stam-py/venv venv && ln -s /Users/stephaniegillen/Projects/get-stam-py/.env .env` — both are gitignored, never committed.)

Expected: one `Inserting: ...` or `Skipping ...`/`Already seeded ...` line per completed NFL game found for yesterday, ending with `Seeded N NFL game(s) for <date>`, no unhandled exception. If there were zero NFL games yesterday (bye week / offseason), the job prints `No completed NFL games found for <date>` and exits cleanly — in that case, temporarily hardcode a known past date with real games into `yesterday` for a one-off manual verification run (revert the hardcode before committing), to confirm the pipeline actually works end-to-end rather than trivially exiting on an empty day.

For at least one inserted game, manually cross-check via a direct query:
```sql
SELECT game_date, home_team_name, away_team_name, home_points, away_points,
       home_line, away_line, total, home_money_line, away_money_line,
       home_quarter_scores, away_quarter_scores, playoffs, game_site, odds_event_id
FROM nfl_games WHERE odds_event_id = '<the event id printed above>';
```
Confirm: `home_points + away_points` equals the final score you can look up independently (e.g. via ESPN.com for that game), `sum(home_quarter_scores) == home_points` and same for away, `home_line`/`away_line` look like plausible real spread numbers (not moneyline prices — this was a bug found in the existing `mlb_seed_yesterdays_games_odds_api.py` during this plan's research, worth avoiding here), and `odds_event_id` is non-NULL.

- [ ] **Step 3: Commit**

```bash
git add jobs/nfl_odds_api_seed_yesterdays_games.py
git commit -m "feat: add NFL games seed job sourced from Odds API + ESPN"
```

---

### Task 2: Delete the old SDQL job and the now-fully-orphaned SDQL helper code

**Files:**
- Delete: `jobs/nfl_seed_yesterdays_games.py`, `sdql_queries.py`, `historical_odds.py`, `single_game_data.py`, `utils.py`

**Interfaces:** none — this task only removes files confirmed to have zero live callers; it does not change any function signature or behavior relied on elsewhere.

- [ ] **Step 1: Re-confirm zero live callers right before deleting (repo state may have shifted since the design spec was written)**

Run these from the repo root and confirm each returns no output:
```bash
grep -rn "import historical_odds\|from historical_odds" --include="*.py" .
grep -rln "sdql_queries\|single_game_data" --include="*.py" . | grep -v -E "single_game_data\.py$|sdql_queries\.py$|^./utils.py$"
grep -rn "from utils import\|^import utils$" --include="*.py" . | grep -v "^./utils.py"
grep -rln "nfl_seed_yesterdays_games" --include="*.py" .
```
Expected: all four commands print nothing. If any prints a match, STOP — a new caller appeared since the spec was written; investigate before deleting anything, this task's premise (zero callers) no longer holds for that file.

- [ ] **Step 2: Delete the five files**

```bash
git rm jobs/nfl_seed_yesterdays_games.py sdql_queries.py historical_odds.py single_game_data.py utils.py
```

- [ ] **Step 3: Confirm nothing else in the app broke**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py/.claude/worktrees/nfl-odds-api-migration && ./venv/bin/python -m pytest tests/ -q`

Expected: same pass count as before this task (158 passed, as of the last full run on this branch's parent) — zero new failures, zero import errors. Also run `./venv/bin/python -c "import app"` to confirm the Flask app itself still imports cleanly (catches any stray top-level import of a deleted module that the test suite doesn't happen to exercise).

- [ ] **Step 4: Re-run the new NFL job once more post-cleanup as a final regression check**

Run: `./venv/bin/python jobs/nfl_odds_api_seed_yesterdays_games.py`

Expected: same clean behavior as Task 1 Step 2 — confirms the new job never secretly depended on anything just deleted.

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "chore: remove SDQL-based NFL seed job and now-orphaned SDQL helper modules"
```

---

## Self-Review Notes

- **Spec coverage:** field-by-field mapping table → Task 1's insert (every column sourced as the spec's table specifies). Go-forward-only, lenient-insert, lenient-ESPN-matching, DraftKings-preferred-with-fallback, no-new-migration decisions → all reflected directly in Task 1's code. Dead-code bundle → Task 2. One refinement beyond the spec's literal wording: the spec said "the unused `check_for_trends` function in `utils.py`"; verification during planning (grep for every importer of `utils`) showed `single_game_data.py` is the *only* file that imports anything from `utils.py` at all, and it's already being deleted — so Task 2 deletes the entire `utils.py` file rather than surgically removing one function, leaving no orphaned remainder (`detect_trends`, `mlb_totals`, `other_totals` were otherwise already dead with zero callers of their own).
- **Placeholder scan:** no TBD/TODO; every step has runnable code or a concrete command with a stated expected result.
- **Type consistency:** `get_espn_enrichment` returns the same dict shape in both its success and `empty` fallback paths (`home_quarter_scores`, `away_quarter_scores`, `neutral_site`, `playoffs`, `overtime_detail`), and `seed_yesterdays_nfl_games` consumes exactly those keys. `parse_odds_data` returns the same five keys in both its early-return and full-parse paths, consumed identically.
