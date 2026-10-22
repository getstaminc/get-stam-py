# NHL Odds-API Games Switch + Player Props Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch the daily NHL games job from SDQL to the Odds API (with ESPN filling the fields Odds API can't provide), and build a brand-new `nhl_player_props` import pipeline mirroring NFL's, including a 2023-season historical backfill.

**Architecture:** Two independent pipelines sharing one data-source convention: Odds API for betting lines, ESPN's free site API for actual results, and `shared_utils.convert_team_name` (not the unpopulated `teams.odds_api_team_name`/`espn_team_id` columns) for all team-name resolution. Player identity resolution ports NFL's embedded `resolve_player_simple()` pattern directly (exact alias match → exact name match → create placeholder), not the NBA-only `services/player_resolver.py`.

**Tech Stack:** Python, SQLAlchemy Core (`text()` queries, no ORM queries — ORM models are for migrations/`alembic revision --autogenerate` only, matching existing convention), Alembic, Flask blueprints, pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-nhl-odds-api-switch-design.md`

## Global Constraints

- Team name resolution uses `shared_utils.convert_team_name` + a direct `team_name` lookup against `teams WHERE sport = 'NHL'` — never `odds_api_team_name` or `espn_team_id` (both are NULL for every NHL row today; populating them is out of scope).
- Player-prop odds import uses `draftkings` as the sole bookmaker, matching NFL.
- All new jobs run under `DATABASE_URL` with `postgres://` → `postgresql://` normalization, matching every existing job.
- No code in this plan touches the trends/game-details UI — that's an explicit follow-on phase per the spec.
- Every new pure parsing/transformation function gets a real pytest unit test using recorded fixture JSON. Functions that make live network/DB calls are verified by manual dry-run (same convention as every existing NFL/NBA/MLB import job — none of them have automated test coverage either; this plan's unit-tested pure functions are a net improvement, not a parity drop).

---

## Part A: Games pipeline

### Task 1: `odds_event_id` column + `models/nhl_game.py`

**Files:**
- Create: `migrations/versions/a1e8f3c92b47_add_odds_event_id_to_nhl_games.py`
- Create: `models/nhl_game.py`
- Modify: `models/__init__.py`

**Interfaces:**
- Produces: `NHL_Game` SQLAlchemy model (import name for later tasks: `from models.nhl_game import NHL_Game`), and the `nhl_games.odds_event_id` column (nullable, unique) that Task 3's job writes to.

- [ ] **Step 1: Write the migration**

```python
"""add_odds_event_id_to_nhl_games

Revision ID: a1e8f3c92b47
Revises: 689b5984c18e
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1e8f3c92b47'
down_revision: Union[str, None] = '689b5984c18e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('nhl_games', sa.Column('odds_event_id', sa.String(100), nullable=True))
    op.create_unique_constraint('uq_nhl_games_odds_event_id', 'nhl_games', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_nhl_games_odds_event_id', 'nhl_games', type_='unique')
    op.drop_column('nhl_games', 'odds_event_id')
```

- [ ] **Step 2: Run the migration**

Run: `source venv/bin/activate && alembic upgrade head`
Expected: `Running upgrade 689b5984c18e -> a1e8f3c92b47, add_odds_event_id_to_nhl_games`

- [ ] **Step 3: Write `models/nhl_game.py`**

Mirrors `models/nba_game.py`, with `nhl_games`' actual existing columns (confirmed via `\d nhl_games`) plus the new column from Step 1:

```python
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ARRAY, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from .base import Base


class NHL_Game(Base):
    __tablename__ = 'nhl_games'

    game_id = Column(Integer, primary_key=True, autoincrement=True)
    game_date = Column(Date, nullable=False)
    game_site = Column(String(100), nullable=False)
    home_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    home_team_name = Column(String(100), nullable=False)
    away_team_name = Column(String(100), nullable=False)
    home_goals = Column(Integer, nullable=False)
    away_goals = Column(Integer, nullable=False)
    home_money_line = Column(Float)
    away_money_line = Column(Float)
    home_period_goals = Column(ARRAY(Integer))
    away_period_goals = Column(ARRAY(Integer))
    home_starting_goalie = Column(String(100))
    away_starting_goalie = Column(String(100))
    home_powerplay_goals = Column(Integer)
    away_powerplay_goals = Column(Integer)
    total = Column(Float)
    overtime = Column(Boolean)
    shoot_out = Column(Boolean)
    playoffs = Column(Boolean)
    sdql_game_id = Column(Integer, unique=True)
    odds_event_id = Column(String(100), unique=True)
    created_date = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    modified_date = Column(TIMESTAMP, server_default=func.now(), nullable=False)
```

- [ ] **Step 4: Register the model**

In `models/__init__.py`, add near the other game models:

```python
from .nhl_game import NHL_Game
```

And add `'NHL_Game'` to the `__all__` list.

- [ ] **Step 5: Verify the model matches the live table**

Run:
```bash
source venv/bin/activate && python3 -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.nhl_game import NHL_Game
import os
from dotenv import load_dotenv
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
Session = sessionmaker(bind=engine)
session = Session()
row = session.query(NHL_Game).order_by(NHL_Game.game_date.desc()).first()
print(row.game_date, row.home_team_name, row.away_team_name, row.odds_event_id)
session.close()
"
```
Expected: prints the most recent NHL game with `odds_event_id` as `None` (no rows have one yet).

- [ ] **Step 6: Commit**

```bash
git add migrations/versions/a1e8f3c92b47_add_odds_event_id_to_nhl_games.py models/nhl_game.py models/__init__.py
git commit -m "Add odds_event_id column and NHL_Game model"
```

---

### Task 2: ESPN NHL game-enrichment pure functions

**Files:**
- Create: `jobs/nhl_espn_enrichment.py`
- Test: `tests/test_nhl_espn_enrichment.py`

**Interfaces:**
- Produces (consumed by Task 3):
  - `extract_period_goals(competitor: dict) -> List[int]`
  - `detect_overtime_shootout(status_detail: str) -> Tuple[bool, bool]` — returns `(overtime, shoot_out)`
  - `is_playoff_game(season_type: int) -> bool`
  - `count_powerplay_goals(plays: list, espn_team_id: str) -> int`
  - `find_starting_goalie(plays: list, shooting_espn_team_id: str) -> Optional[str]` — pass the OPPONENT's `espn_team_id` here; see Step 1 docstring.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_nhl_espn_enrichment.py`:

```python
from jobs.nhl_espn_enrichment import (
    extract_period_goals,
    detect_overtime_shootout,
    is_playoff_game,
    count_powerplay_goals,
    find_starting_goalie,
)


def test_extract_period_goals_regulation():
    competitor = {"linescores": [{"displayValue": "1"}, {"displayValue": "0"}, {"displayValue": "2"}]}
    assert extract_period_goals(competitor) == [1, 0, 2]


def test_extract_period_goals_shootout_includes_bonus_entry():
    # DET 4 @ SJ 3, 2026-10-17, event 401892525 (real game, Final/SO)
    competitor = {"linescores": [{"displayValue": "1"}, {"displayValue": "0"}, {"displayValue": "2"}, {"displayValue": "0"}, {"displayValue": "1"}]}
    assert extract_period_goals(competitor) == [1, 0, 2, 0, 1]


def test_detect_overtime_shootout_plain_final():
    assert detect_overtime_shootout("Final") == (False, False)


def test_detect_overtime_shootout_ot_only():
    assert detect_overtime_shootout("Final/OT") == (True, False)


def test_detect_overtime_shootout_shootout():
    assert detect_overtime_shootout("Final/SO") == (True, True)


def test_is_playoff_game():
    assert is_playoff_game(3) is True
    assert is_playoff_game(2) is False
    assert is_playoff_game(1) is False


def test_count_powerplay_goals():
    plays = [
        {"type": {"text": "Goal"}, "scoringPlay": True, "team": {"id": "30"}, "strength": {"text": "Power Play"}},
        {"type": {"text": "Goal"}, "scoringPlay": True, "team": {"id": "30"}, "strength": {"text": "Even Strength"}},
        {"type": {"text": "Goal"}, "scoringPlay": True, "team": {"id": "9"}, "strength": {"text": "Power Play"}},
        {"type": {"text": "Shot"}, "scoringPlay": False, "team": {"id": "30"}, "strength": {"text": "Power Play"}},
    ]
    assert count_powerplay_goals(plays, "30") == 1
    assert count_powerplay_goals(plays, "9") == 1


def test_find_starting_goalie_identifies_opponent_starter():
    # Real play-by-play shape from FLA @ BUF, 2026-10-12, event 401892485.
    # Buffalo shoots (team id "2"); the saver named here is Florida's starter.
    plays = [
        {
            "type": {"text": "Shot"},
            "period": {"number": 1},
            "team": {"id": "2"},
            "participants": [
                {"athlete": {"displayName": "Rasmus Dahlin"}, "type": "shooter"},
                {"athlete": {"displayName": "Jacob Markstrom"}, "type": "saver"},
            ],
        },
        {
            "type": {"text": "Shot"},
            "period": {"number": 1},
            "team": {"id": "2"},
            "participants": [
                {"athlete": {"displayName": "Someone Else"}, "type": "shooter"},
                {"athlete": {"displayName": "Akira Schmid"}, "type": "saver"},
            ],
        },
    ]
    # Shots BY team "2" (Buffalo) are saved by Florida's starter -> pass Buffalo's id
    # to get Florida's starter (the opponent of whoever is shooting).
    assert find_starting_goalie(plays, "2") == "Jacob Markstrom"


def test_find_starting_goalie_no_shots_returns_none():
    assert find_starting_goalie([], "2") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && python -m pytest tests/test_nhl_espn_enrichment.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'jobs.nhl_espn_enrichment'`

- [ ] **Step 3: Write the implementation**

Create `jobs/nhl_espn_enrichment.py`:

```python
"""Pure functions for enriching NHL games with data ESPN has but the Odds API
doesn't: period goals, overtime/shootout, playoffs, powerplay goals, and
starting goalies. All verified against real ESPN NHL summary responses —
see tests/test_nhl_espn_enrichment.py for the specific games checked.

ESPN's boxscore `starter` field on goalie entries is unpopulated (confirmed
null on every game checked), so starting goalie is derived from play-by-play
instead: the first period-1 shot a team takes is saved by the OPPOSING
team's starting goalie.
"""
from typing import List, Optional, Tuple


def extract_period_goals(competitor: dict) -> List[int]:
    """Per-period goals from ESPN's `linescores` array on a competitor. A
    shootout-deciding goal appears as a bonus 5th entry; left in as-is since
    nhl_games.home_period_goals/away_period_goals is an array column with no
    fixed length requirement."""
    return [int(entry["displayValue"]) for entry in competitor.get("linescores", [])]


def detect_overtime_shootout(status_detail: str) -> Tuple[bool, bool]:
    """ESPN's status.type.detail is literally 'Final', 'Final/OT', or
    'Final/SO'. A shootout game went through overtime first, so shoot_out=True
    implies overtime=True."""
    detail = status_detail or ""
    shoot_out = "SO" in detail
    overtime = shoot_out or "OT" in detail
    return overtime, shoot_out


def is_playoff_game(season_type: int) -> bool:
    """ESPN season.type: 1=preseason, 2=regular season, 3=postseason."""
    return season_type == 3


def count_powerplay_goals(plays: list, espn_team_id: str) -> int:
    """Count scoring plays credited to espn_team_id with strength.text ==
    'Power Play'. Only scoringPlay=True entries count — a non-scoring 'Shot'
    play can also carry strength info and must not be counted."""
    count = 0
    for play in plays:
        if not play.get("scoringPlay"):
            continue
        if str(play.get("team", {}).get("id", "")) != str(espn_team_id):
            continue
        if (play.get("strength") or {}).get("text") != "Power Play":
            continue
        count += 1
    return count


def find_starting_goalie(plays: list, shooting_espn_team_id: str) -> Optional[str]:
    """Return the name of the goalie who faced the FIRST period-1 shot taken
    BY shooting_espn_team_id — that goalie belongs to the opposing team, and
    is that team's starter. Pass the team that is SHOOTING; the name
    returned belongs to the OTHER team."""
    for play in plays:
        if play.get("type", {}).get("text") != "Shot":
            continue
        if play.get("period", {}).get("number") != 1:
            continue
        if str(play.get("team", {}).get("id", "")) != str(shooting_espn_team_id):
            continue
        for participant in play.get("participants", []):
            if participant.get("type") == "saver":
                return participant["athlete"]["displayName"]
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && python -m pytest tests/test_nhl_espn_enrichment.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add jobs/nhl_espn_enrichment.py tests/test_nhl_espn_enrichment.py
git commit -m "Add pure ESPN NHL game-enrichment functions with unit tests"
```

---

### Task 3: `jobs/nhl_odds_api_seed_yesterdays_games.py` + retire old jobs

**Files:**
- Create: `jobs/nhl_odds_api_seed_yesterdays_games.py`
- Delete: `jobs/nhl_seed_yesterdays_games.py` (SDQL)
- Delete: `jobs/nhl_odds_api_yesterday.py` (stale hardcoded-date prototype)

**Interfaces:**
- Consumes: `jobs.nhl_espn_enrichment.{extract_period_goals, detect_overtime_shootout, is_playoff_game, count_powerplay_goals, find_starting_goalie}` (Task 2); `shared_utils.convert_team_name`, `shared_utils.convert_to_eastern`.
- Produces: `seed_yesterdays_nhl_games()` — the function Heroku Scheduler will invoke via `python jobs/nhl_odds_api_seed_yesterdays_games.py`.

- [ ] **Step 1: Write the job**

```python
#!/usr/bin/env python3
"""Seed yesterday's NHL games from the Odds API, enriched with ESPN data for
fields the Odds API doesn't provide (period goals, starting goalies,
powerplay goals, overtime/shootout, playoffs). Replaces the SDQL-based
jobs/nhl_seed_yesterdays_games.py.

game_site is hardcoded 'home' — home_team_id/away_team_id already disambiguate
home vs. away, so SDQL's 'neutral' distinction isn't carried forward.
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
from jobs.nhl_espn_enrichment import (
    extract_period_goals,
    detect_overtime_shootout,
    is_playoff_game,
    count_powerplay_goals,
    find_starting_goalie,
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")


def get_completed_nhl_games_for_date(target_date_str: str, retries=3, delay=2):
    """Odds API current (non-historical) scores for the last 3 days, filtered
    to games whose Eastern-converted commence date matches target_date_str."""
    url = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/scores/"
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
    """Historical h2h/totals odds for a date (yesterday's market has closed by
    the time this job runs, so the current-odds endpoint won't have it)."""
    url = "https://api.the-odds-api.com/v4/historical/sports/icehockey_nhl/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "bookmakers": "draftkings",
        "markets": "h2h,totals",
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


def parse_odds_data(odds_game: dict) -> dict:
    """Extract moneyline + total from a draftkings bookmaker entry."""
    odds_info = {"home_money_line": None, "away_money_line": None, "total": None}
    draftkings = next((bm for bm in odds_game.get("bookmakers", []) if bm["key"] == "draftkings"), None)
    if not draftkings:
        return odds_info
    home_team = odds_game["home_team"]
    away_team = odds_game["away_team"]
    for market in draftkings.get("markets", []):
        if market["key"] == "h2h":
            for outcome in market["outcomes"]:
                if outcome["name"] == home_team:
                    odds_info["home_money_line"] = outcome["price"]
                elif outcome["name"] == away_team:
                    odds_info["away_money_line"] = outcome["price"]
        elif market["key"] == "totals":
            points = market["outcomes"][0].get("point") if market.get("outcomes") else None
            odds_info["total"] = points
    return odds_info


def get_espn_enrichment(target_date_str: str, home_team: str, away_team: str) -> dict:
    """Fetch ESPN's NHL summary for the game matching home_team/away_team on
    target_date_str and return the fields the Odds API can't provide. Returns
    an all-None dict if the ESPN game can't be matched."""
    empty = {
        "home_period_goals": None, "away_period_goals": None,
        "home_starting_goalie": None, "away_starting_goalie": None,
        "home_powerplay_goals": None, "away_powerplay_goals": None,
        "overtime": None, "shoot_out": None, "playoffs": None,
    }
    date_compact = target_date_str.replace("-", "")
    try:
        resp = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
            params={"dates": date_compact}, timeout=30,
        )
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except requests.exceptions.RequestException as e:
        print(f"  ESPN scoreboard fetch failed: {e}")
        return empty

    espn_game_id = None
    for event in events:
        comp = event.get("competitions", [{}])[0]
        competitors = {c.get("homeAway"): c.get("team", {}).get("displayName") for c in comp.get("competitors", [])}
        espn_home = shared_utils.convert_team_name(competitors.get("home", ""))
        espn_away = shared_utils.convert_team_name(competitors.get("away", ""))
        if espn_home == home_team and espn_away == away_team:
            espn_game_id = event.get("id")
            break

    if not espn_game_id:
        print(f"  Could not match ESPN event for {away_team} @ {home_team} on {target_date_str}")
        return empty

    try:
        resp = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary",
            params={"event": espn_game_id, "enable": "boxscore,plays"}, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  ESPN summary fetch failed for event {espn_game_id}: {e}")
        return empty

    header = data.get("header", {})
    comp = header.get("competitions", [{}])[0]
    season_type = header.get("season", {}).get("type")
    status_detail = comp.get("status", {}).get("type", {}).get("detail", "")
    plays = data.get("plays", [])

    espn_home_id = espn_away_id = None
    home_linescore = away_linescore = {}
    for competitor in comp.get("competitors", []):
        if competitor.get("homeAway") == "home":
            espn_home_id = str(competitor.get("team", {}).get("id", ""))
            home_linescore = competitor
        elif competitor.get("homeAway") == "away":
            espn_away_id = str(competitor.get("team", {}).get("id", ""))
            away_linescore = competitor

    overtime, shoot_out = detect_overtime_shootout(status_detail)

    return {
        "home_period_goals": extract_period_goals(home_linescore),
        "away_period_goals": extract_period_goals(away_linescore),
        "home_starting_goalie": find_starting_goalie(plays, espn_away_id) if espn_away_id else None,
        "away_starting_goalie": find_starting_goalie(plays, espn_home_id) if espn_home_id else None,
        "home_powerplay_goals": count_powerplay_goals(plays, espn_home_id) if espn_home_id else None,
        "away_powerplay_goals": count_powerplay_goals(plays, espn_away_id) if espn_away_id else None,
        "overtime": overtime,
        "shoot_out": shoot_out,
        "playoffs": is_playoff_game(season_type) if season_type is not None else None,
    }


def seed_yesterdays_nhl_games():
    print("Starting NHL game seeding (Odds API + ESPN)...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        games = get_completed_nhl_games_for_date(yesterday)
        if not games:
            print(f"No completed NHL games found for {yesterday}")
            return

        odds_data = get_historical_odds_for_date(yesterday)
        odds_lookup = {}
        for game in odds_data:
            odds_lookup[f"{game['home_team']}_{game['away_team']}"] = game

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NHL'")).mappings()
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

            home_goals = away_goals = None
            for score in game["scores"]:
                db_name = shared_utils.convert_team_name(score["name"])
                if db_name == db_home:
                    home_goals = int(score["score"])
                elif db_name == db_away:
                    away_goals = int(score["score"])
            if home_goals is None or away_goals is None:
                print(f"Skipping {game['away_team']} @ {game['home_team']} - missing score")
                continue

            existing = conn.execute(text("""
                SELECT 1 FROM nhl_games
                WHERE odds_event_id = :odds_event_id
                   OR (game_date = :game_date AND home_team_name = :home AND away_team_name = :away)
            """), {
                "odds_event_id": game["id"], "game_date": yesterday,
                "home": db_home, "away": db_away,
            }).fetchone()
            if existing:
                print(f"Already seeded: {db_away} @ {db_home} on {yesterday}")
                continue

            odds_info = parse_odds_data(odds_lookup.get(f"{game['home_team']}_{game['away_team']}", {}))
            enrichment = get_espn_enrichment(yesterday, db_home, db_away)

            conn.execute(text("""
                INSERT INTO nhl_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_goals, away_goals, home_money_line, away_money_line,
                    home_period_goals, away_period_goals, home_starting_goalie, away_starting_goalie,
                    home_powerplay_goals, away_powerplay_goals, total, overtime, shoot_out, playoffs,
                    odds_event_id
                ) VALUES (
                    :game_date, 'home', :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_goals, :away_goals, :home_money_line, :away_money_line,
                    :home_period_goals, :away_period_goals, :home_starting_goalie, :away_starting_goalie,
                    :home_powerplay_goals, :away_powerplay_goals, :total, :overtime, :shoot_out, :playoffs,
                    :odds_event_id
                )
            """), {
                "game_date": yesterday, "home_team_id": home_team_id, "away_team_id": away_team_id,
                "home_team_name": db_home, "away_team_name": db_away,
                "home_goals": home_goals, "away_goals": away_goals,
                "home_money_line": odds_info["home_money_line"], "away_money_line": odds_info["away_money_line"],
                "home_period_goals": enrichment["home_period_goals"], "away_period_goals": enrichment["away_period_goals"],
                "home_starting_goalie": enrichment["home_starting_goalie"], "away_starting_goalie": enrichment["away_starting_goalie"],
                "home_powerplay_goals": enrichment["home_powerplay_goals"], "away_powerplay_goals": enrichment["away_powerplay_goals"],
                "total": odds_info["total"], "overtime": enrichment["overtime"],
                "shoot_out": enrichment["shoot_out"], "playoffs": enrichment["playoffs"],
                "odds_event_id": game["id"],
            })
            inserted += 1
            print(f"Inserted: {db_away} {away_goals} @ {db_home} {home_goals}")

        conn.commit()
        print(f"Seeded {inserted} NHL games for {yesterday}")
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_nhl_games()
```

- [ ] **Step 2: Delete the superseded jobs**

```bash
git rm jobs/nhl_seed_yesterdays_games.py jobs/nhl_odds_api_yesterday.py
```

- [ ] **Step 3: Manual verification (live dry run)**

This job touches real network + DB calls, so it's verified by running it, not by a mocked unit test (same convention as every existing seed job). Run against a date with known completed games already in `nhl_games` from SDQL, pointed at a scratch/staging DB if available, or read-only-review the printed output if not:

Run: `source venv/bin/activate && python jobs/nhl_odds_api_seed_yesterdays_games.py`
Expected: prints each matched game with scores, moneylines, and enrichment fields; either inserts new rows or logs "Already seeded" for games SDQL already wrote. Spot-check one inserted row's `home_period_goals`/`overtime`/`home_starting_goalie` against ESPN's own boxscore page for that game.

- [ ] **Step 4: Update the Heroku Scheduler job (manual, not code)**

In the Heroku dashboard's Scheduler add-on, change the NHL games job command from `python jobs/nhl_seed_yesterdays_games.py` to `python jobs/nhl_odds_api_seed_yesterdays_games.py`. This isn't in the repo (no `app.json` scheduler config exists), so it's a manual dashboard step — note it in the PR description as a deploy follow-up.

- [ ] **Step 5: Commit**

```bash
git add jobs/nhl_odds_api_seed_yesterdays_games.py
git commit -m "Switch NHL daily games job from SDQL to Odds API + ESPN enrichment"
```

---

## Part B: Player props schema

### Task 4: `nhl_players`/`nhl_player_aliases`/`nhl_player_name_mismatch`/`nhl_player_props` tables + models

**Files:**
- Create: `migrations/versions/f4d2b8a61c93_add_nhl_player_props_tables.py`
- Create: `models/nhl_player.py`
- Create: `models/nhl_player_alias.py`
- Create: `models/nhl_player_name_mismatch.py`
- Create: `models/nhl_player_prop.py`
- Modify: `models/__init__.py`

**Interfaces:**
- Produces: the 4 tables and 4 models Tasks 5–8 read/write via raw SQL (`nhl_players`, `nhl_player_aliases`, `nhl_player_name_mismatch`, `nhl_player_props`). Column names below are the exact names later tasks use.

- [ ] **Step 1: Write the migration**

```python
"""add_nhl_player_props_tables

Revision ID: f4d2b8a61c93
Revises: a1e8f3c92b47
Create Date: 2026-10-20 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4d2b8a61c93'
down_revision: Union[str, None] = 'a1e8f3c92b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'nhl_players',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('espn_player_id', sa.String(50), unique=True, nullable=True),
        sa.Column('player_name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('position', sa.String(10)),
        sa.Column('team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('first_seen_date', sa.Date, nullable=False),
        sa.Column('last_seen_date', sa.Date, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'nhl_player_aliases',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nhl_players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('source', 'normalized_name', name='uq_nhl_player_aliases_source_normalized'),
    )

    op.create_table(
        'nhl_player_props',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nhl_players.id'), nullable=False),
        sa.Column('normalized_name', sa.String(255)),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('odds_event_id', sa.String(100)),
        sa.Column('espn_event_id', sa.String(100)),
        sa.Column('odds_source', sa.String(50), server_default='odds_api'),
        sa.Column('bookmaker', sa.String(50)),

        # Skater scoring
        sa.Column('odds_player_goals', sa.Numeric(4, 1)),
        sa.Column('odds_player_goals_over_price', sa.Integer),
        sa.Column('odds_player_goals_under_price', sa.Integer),
        sa.Column('odds_player_assists', sa.Numeric(4, 1)),
        sa.Column('odds_player_assists_over_price', sa.Integer),
        sa.Column('odds_player_assists_under_price', sa.Integer),
        sa.Column('odds_player_points', sa.Numeric(4, 1)),
        sa.Column('odds_player_points_over_price', sa.Integer),
        sa.Column('odds_player_points_under_price', sa.Integer),
        sa.Column('odds_player_shots_on_goal', sa.Numeric(4, 1)),
        sa.Column('odds_player_shots_on_goal_over_price', sa.Integer),
        sa.Column('odds_player_shots_on_goal_under_price', sa.Integer),

        # Goalie
        sa.Column('odds_player_total_saves', sa.Numeric(4, 1)),
        sa.Column('odds_player_total_saves_over_price', sa.Integer),
        sa.Column('odds_player_total_saves_under_price', sa.Integer),

        # Anytime goal (binary yes/no market, no under column)
        sa.Column('odds_player_goal_scorer_anytime', sa.Numeric(4, 1)),
        sa.Column('odds_player_goal_scorer_anytime_over_price', sa.Integer),

        # Actuals
        sa.Column('actual_player_goals', sa.Integer),
        sa.Column('actual_player_assists', sa.Integer),
        sa.Column('actual_player_points', sa.Integer),
        sa.Column('actual_player_shots_on_goal', sa.Integer),
        sa.Column('actual_player_total_saves', sa.Integer),
        sa.Column('actual_player_goal_scorer_anytime', sa.Boolean),

        sa.Column('player_team_name', sa.String(100)),
        sa.Column('player_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('opponent_team_name', sa.String(100)),
        sa.Column('opponent_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),

        sa.Column('odds_home_team', sa.String(100)),
        sa.Column('odds_away_team', sa.String(100)),
        sa.Column('odds_home_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_away_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),

        sa.Column('did_not_play', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('actuals_unavailable_reason', sa.String(30)),

        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.UniqueConstraint('player_id', 'odds_event_id', name='uq_nhl_player_props_player_odds_event'),
    )

    op.create_table(
        'nhl_player_name_mismatch',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('nhl_player_props_id', sa.Integer, sa.ForeignKey('nhl_player_props.id'), nullable=False),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('odds_home_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_away_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_home_team', sa.String(100)),
        sa.Column('odds_away_team', sa.String(100)),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nhl_players.id')),
        sa.Column('resolved', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('ix_nhl_players_normalized_name', 'nhl_players', ['normalized_name'])
    op.create_index('ix_nhl_player_aliases_normalized_name', 'nhl_player_aliases', ['normalized_name'])
    op.create_index('idx_nhl_player_props_game_date_normalized_name', 'nhl_player_props', ['game_date', 'normalized_name'])
    op.create_index('ix_nhl_player_props_player_game_date', 'nhl_player_props', ['player_id', 'game_date'])
    op.create_index('idx_nhl_name_mismatch_game_date', 'nhl_player_name_mismatch', ['game_date'])
    op.create_index('idx_nhl_name_mismatch_resolved', 'nhl_player_name_mismatch', ['resolved'])
    op.create_index('idx_nhl_name_mismatch_player_props', 'nhl_player_name_mismatch', ['nhl_player_props_id'])


def downgrade() -> None:
    op.drop_index('idx_nhl_name_mismatch_player_props', 'nhl_player_name_mismatch')
    op.drop_index('idx_nhl_name_mismatch_resolved', 'nhl_player_name_mismatch')
    op.drop_index('idx_nhl_name_mismatch_game_date', 'nhl_player_name_mismatch')
    op.drop_index('ix_nhl_player_props_player_game_date', 'nhl_player_props')
    op.drop_index('idx_nhl_player_props_game_date_normalized_name', 'nhl_player_props')
    op.drop_index('ix_nhl_player_aliases_normalized_name', 'nhl_player_aliases')
    op.drop_index('ix_nhl_players_normalized_name', 'nhl_players')

    op.drop_table('nhl_player_name_mismatch')
    op.drop_table('nhl_player_props')
    op.drop_table('nhl_player_aliases')
    op.drop_table('nhl_players')
```

- [ ] **Step 2: Run the migration**

Run: `source venv/bin/activate && alembic upgrade head`
Expected: `Running upgrade a1e8f3c92b47 -> f4d2b8a61c93, add_nhl_player_props_tables`

- [ ] **Step 3: Write the 4 models**

`models/nhl_player.py`:
```python
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from .base import Base


class NHLPlayer(Base):
    __tablename__ = 'nhl_players'

    id = Column(Integer, primary_key=True, autoincrement=True)
    espn_player_id = Column(String(50), unique=True)
    player_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    position = Column(String(10))
    team_id = Column(Integer, ForeignKey('teams.team_id'))
    first_seen_date = Column(Date, nullable=False)
    last_seen_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_nhl_players_normalized_name', 'normalized_name'),
    )
```

`models/nhl_player_alias.py`:
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class NHLPlayerAlias(Base):
    __tablename__ = 'nhl_player_aliases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('nhl_players.id', ondelete='CASCADE'), nullable=False)
    source = Column(String(50), nullable=False)
    source_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('source', 'normalized_name', name='uq_nhl_player_aliases_source_normalized'),
        Index('ix_nhl_player_aliases_normalized_name', 'normalized_name'),
    )
```

`models/nhl_player_name_mismatch.py`:
```python
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.sql import func
from .base import Base


class NHLPlayerNameMismatch(Base):
    __tablename__ = 'nhl_player_name_mismatch'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nhl_player_props_id = Column(Integer, ForeignKey('nhl_player_props.id'), nullable=False)
    game_date = Column(Date, nullable=False)
    odds_home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_away_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_home_team = Column(String(100))
    odds_away_team = Column(String(100))
    normalized_name = Column(String(255), nullable=False)
    player_id = Column(Integer, ForeignKey('nhl_players.id'))
    resolved = Column(Boolean, nullable=False, default=False)
    resolution_notes = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_nhl_name_mismatch_game_date', 'game_date'),
        Index('idx_nhl_name_mismatch_resolved', 'resolved'),
        Index('idx_nhl_name_mismatch_player_props', 'nhl_player_props_id'),
    )
```

`models/nhl_player_prop.py`:
```python
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class NHLPlayerProp(Base):
    __tablename__ = 'nhl_player_props'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('nhl_players.id'), nullable=False)
    normalized_name = Column(String(255))
    game_date = Column(Date, nullable=False)
    odds_event_id = Column(String(100))
    espn_event_id = Column(String(100))
    odds_source = Column(String(50), server_default='odds_api')
    bookmaker = Column(String(50))

    odds_player_goals = Column(Numeric(4, 1))
    odds_player_goals_over_price = Column(Integer)
    odds_player_goals_under_price = Column(Integer)
    odds_player_assists = Column(Numeric(4, 1))
    odds_player_assists_over_price = Column(Integer)
    odds_player_assists_under_price = Column(Integer)
    odds_player_points = Column(Numeric(4, 1))
    odds_player_points_over_price = Column(Integer)
    odds_player_points_under_price = Column(Integer)
    odds_player_shots_on_goal = Column(Numeric(4, 1))
    odds_player_shots_on_goal_over_price = Column(Integer)
    odds_player_shots_on_goal_under_price = Column(Integer)
    odds_player_total_saves = Column(Numeric(4, 1))
    odds_player_total_saves_over_price = Column(Integer)
    odds_player_total_saves_under_price = Column(Integer)
    odds_player_goal_scorer_anytime = Column(Numeric(4, 1))
    odds_player_goal_scorer_anytime_over_price = Column(Integer)

    actual_player_goals = Column(Integer)
    actual_player_assists = Column(Integer)
    actual_player_points = Column(Integer)
    actual_player_shots_on_goal = Column(Integer)
    actual_player_total_saves = Column(Integer)
    actual_player_goal_scorer_anytime = Column(Boolean)

    player_team_name = Column(String(100))
    player_team_id = Column(Integer, ForeignKey('teams.team_id'))
    opponent_team_name = Column(String(100))
    opponent_team_id = Column(Integer, ForeignKey('teams.team_id'))

    odds_home_team = Column(String(100))
    odds_away_team = Column(String(100))
    odds_home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_away_team_id = Column(Integer, ForeignKey('teams.team_id'))

    did_not_play = Column(Boolean, nullable=False, default=False)
    actuals_unavailable_reason = Column(String(30))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('player_id', 'odds_event_id', name='uq_nhl_player_props_player_odds_event'),
        Index('idx_nhl_player_props_game_date_normalized_name', 'game_date', 'normalized_name'),
        Index('ix_nhl_player_props_player_game_date', 'player_id', 'game_date'),
    )
```

- [ ] **Step 4: Register the models**

In `models/__init__.py`, add:
```python
from .nhl_player import NHLPlayer
from .nhl_player_alias import NHLPlayerAlias
from .nhl_player_name_mismatch import NHLPlayerNameMismatch
from .nhl_player_prop import NHLPlayerProp
```
And add `'NHLPlayer', 'NHLPlayerAlias', 'NHLPlayerNameMismatch', 'NHLPlayerProp'` to `__all__`.

- [ ] **Step 5: Verify the tables exist**

Run:
```bash
source venv/bin/activate && python3 -c "
from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://'))
tables = inspect(engine).get_table_names()
for t in ['nhl_players', 'nhl_player_aliases', 'nhl_player_props', 'nhl_player_name_mismatch']:
    print(t, t in tables)
"
```
Expected: all four print `True`.

- [ ] **Step 6: Commit**

```bash
git add migrations/versions/f4d2b8a61c93_add_nhl_player_props_tables.py models/nhl_player.py models/nhl_player_alias.py models/nhl_player_name_mismatch.py models/nhl_player_prop.py models/__init__.py
git commit -m "Add nhl_players/aliases/props/mismatch tables and models"
```

---

## Part C: Import jobs

### Task 5: `jobs/nhl_historical_player_odds_import.py`

**Files:**
- Create: `jobs/nhl_historical_player_odds_import.py`
- Test: `tests/test_nhl_odds_import_parsing.py`

**Interfaces:**
- Consumes: `nhl_players`/`nhl_player_aliases`/`nhl_player_props` (Task 4), `shared_utils.convert_team_name`.
- Produces: `import_historical_odds_date_range(start_date, end_date)` (consumed by Task 7's orchestrator); `resolve_player_simple(conn, player_name, game_date) -> Optional[int]` and `resolve_team_id_from_name(conn, odds_team_name) -> Optional[int]` (consumed by Task 8's mismatch route indirectly via shared naming convention — Task 8 does not call these directly, but matches their alias-table shape).

- [ ] **Step 1: Write the failing test**

Create `tests/test_nhl_odds_import_parsing.py`. The fixture below is a trimmed-but-real shape of what `GET /v4/historical/sports/icehockey_nhl/events/{id}/odds` returns (verified live against event `0922c474e6588f94af491684dbae6cdb`, 2026-10-18):

```python
from datetime import date

from jobs.nhl_historical_player_odds_import import parse_historical_player_props


FIXTURE_ODDS_DATA = {
    "id": "0922c474e6588f94af491684dbae6cdb",
    "home_team": "Calgary Flames",
    "away_team": "Carolina Hurricanes",
    "bookmakers": [
        {
            "key": "draftkings",
            "markets": [
                {
                    "key": "player_goals",
                    "outcomes": [
                        {"name": "Over", "description": "Sebastian Aho", "price": 165, "point": 0.5},
                        {"name": "Under", "description": "Sebastian Aho", "price": -225, "point": 0.5},
                    ],
                },
                {
                    "key": "player_assists",
                    "outcomes": [
                        {"name": "Over", "description": "Sebastian Aho", "price": -130, "point": 0.5},
                        {"name": "Under", "description": "Sebastian Aho", "price": -105, "point": 0.5},
                    ],
                },
                {
                    "key": "player_total_saves",
                    "outcomes": [
                        {"name": "Over", "description": "Devin Cooley", "price": -115, "point": 27.5},
                        {"name": "Under", "description": "Devin Cooley", "price": -120, "point": 27.5},
                    ],
                },
                {
                    "key": "player_goal_scorer_anytime",
                    "outcomes": [
                        {"name": "Yes", "description": "Andrei Svechnikov", "price": 155},
                    ],
                },
            ],
        }
    ],
}


def test_parse_standard_over_under_market():
    props = parse_historical_player_props(FIXTURE_ODDS_DATA, "2026-10-18T22:10:00Z")
    aho_goals = next(p for p in props if p["player_name"] == "Sebastian Aho" and p["stat_type"] == "goals")
    assert aho_goals["line"] == 0.5
    assert aho_goals["over_price"] == 165
    assert aho_goals["under_price"] == -225
    assert aho_goals["game_date"] == date(2026, 10, 18)


def test_parse_anytime_goal_scorer_binary_market():
    props = parse_historical_player_props(FIXTURE_ODDS_DATA, "2026-10-18T22:10:00Z")
    anytime = next(p for p in props if p["player_name"] == "Andrei Svechnikov")
    assert anytime["stat_type"] == "goal_scorer_anytime"
    assert anytime["line"] == 0.5
    assert anytime["over_price"] == 155
    assert anytime["under_price"] is None


def test_parse_skips_outcomes_missing_point_on_standard_markets():
    data = {
        **FIXTURE_ODDS_DATA,
        "bookmakers": [{
            "key": "draftkings",
            "markets": [{
                "key": "player_goals",
                "outcomes": [{"name": "Over", "description": "No Point Player", "price": 100, "point": None}],
            }],
        }],
    }
    props = parse_historical_player_props(data, "2026-10-18T22:10:00Z")
    assert props == []


def test_parse_ignores_non_draftkings_bookmakers():
    data = {**FIXTURE_ODDS_DATA, "bookmakers": [{"key": "fanduel", "markets": FIXTURE_ODDS_DATA["bookmakers"][0]["markets"]}]}
    assert parse_historical_player_props(data, "2026-10-18T22:10:00Z") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && python -m pytest tests/test_nhl_odds_import_parsing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'jobs.nhl_historical_player_odds_import'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Historical NHL player-prop odds import from the Odds API, mirroring
jobs/nfl_historical_player_odds_import.py. No team D/ST equivalent exists for
NHL, so unlike the NFL job there's no separate defense-props split.

Team resolution uses shared_utils.convert_team_name + a direct team_name
lookup, NOT teams.odds_api_team_name (unpopulated for every NHL team today).
"""
import os
import sys
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import requests
import pytz
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shared_utils

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

NHL_MARKETS = "player_goals,player_assists,player_points,player_shots_on_goal,player_total_saves,player_goal_scorer_anytime"

# Maps Odds API market stat_type -> (line_col, over_col, under_col).
# goal_scorer_anytime has no under column (binary yes/no market).
STAT_COLUMNS = {
    'goals': ('odds_player_goals', 'odds_player_goals_over_price', 'odds_player_goals_under_price'),
    'assists': ('odds_player_assists', 'odds_player_assists_over_price', 'odds_player_assists_under_price'),
    'points': ('odds_player_points', 'odds_player_points_over_price', 'odds_player_points_under_price'),
    'shots_on_goal': ('odds_player_shots_on_goal', 'odds_player_shots_on_goal_over_price', 'odds_player_shots_on_goal_under_price'),
    'total_saves': ('odds_player_total_saves', 'odds_player_total_saves_over_price', 'odds_player_total_saves_under_price'),
    'goal_scorer_anytime': ('odds_player_goal_scorer_anytime', 'odds_player_goal_scorer_anytime_over_price', None),
}


def get_historical_nhl_events(target_date: date, retries=3, delay=2) -> List[Dict]:
    print(f"Fetching NHL events for {target_date}...")
    url = "https://api.the-odds-api.com/v4/historical/sports/icehockey_nhl/events"
    params = {'apiKey': ODDS_API_KEY, 'date': f"{target_date.strftime('%Y-%m-%d')}T12:00:00Z"}
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            events = data.get('data', data) if isinstance(data, dict) else data
            print(f"  Found {len(events)} NHL events for {target_date}")
            return events
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching events (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay * (i + 1))
            else:
                return []
    return []


def get_historical_player_odds(event_id: str, target_date: date, retries=3, delay=2) -> Optional[Dict]:
    print(f"    Fetching player odds for event {event_id}...")
    events = get_historical_nhl_events(target_date)
    commence_time = next((e.get('commence_time') for e in events if e.get('id') == event_id), None)

    if commence_time:
        commence_dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
        times_to_try = [
            (commence_dt - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            commence_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
        ]
    else:
        times_to_try = [f"{target_date.strftime('%Y-%m-%d')}T23:00:00Z"]

    url = f"https://api.the-odds-api.com/v4/historical/sports/icehockey_nhl/events/{event_id}/odds"
    for odds_query_time in times_to_try:
        params = {
            'apiKey': ODDS_API_KEY, 'date': odds_query_time, 'regions': 'us',
            'markets': NHL_MARKETS, 'oddsFormat': 'american', 'bookmakers': 'draftkings',
        }
        for i in range(3):
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 422:
                    break
                response.raise_for_status()
                data = response.json()
                odds_data = data.get('data', data) if isinstance(data, dict) else data
                if not odds_data or not odds_data.get('bookmakers'):
                    break
                print(f"      Found player odds for event {event_id} at {odds_query_time}")
                return odds_data
            except requests.exceptions.RequestException as e:
                print(f"      Error fetching odds (attempt {i+1}/3): {e}")
                time.sleep(2 * (i + 1))
    return None


def parse_historical_player_props(odds_data: Dict, commence_time: str) -> List[Dict]:
    """Parse historical NHL player props from odds data. Standard markets
    (goals/assists/points/shots_on_goal/total_saves) are Over/Under; goal_scorer_anytime
    is a binary Yes/No market stored with a fixed 0.5 line and only the over slot."""
    game_start = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
    game_date = game_start.astimezone(pytz.timezone('US/Eastern')).date()
    props = []

    draftkings = next((bm for bm in odds_data.get('bookmakers', []) if bm['key'] == 'draftkings'), None)
    if not draftkings:
        return props

    event_id = odds_data['id']
    home_team = odds_data.get('home_team', '')
    away_team = odds_data.get('away_team', '')

    for market in draftkings.get('markets', []):
        stat_type = market['key'].replace('player_', '')
        outcomes = market.get('outcomes', [])

        if stat_type == 'goal_scorer_anytime':
            for outcome in outcomes:
                if (outcome.get('name') or '').strip().lower() != 'yes':
                    continue
                description = outcome.get('description', '')
                price = outcome.get('price')
                if not description or price is None:
                    continue
                props.append({
                    'player_name': description, 'event_id': event_id, 'game_date': game_date,
                    'home_team': home_team, 'away_team': away_team, 'bookmaker': 'draftkings',
                    'stat_type': stat_type, 'line': 0.5, 'over_price': price, 'under_price': None,
                })
            continue

        players_data = {}
        for outcome in outcomes:
            bet_side = (outcome.get('name') or '').strip().lower()
            player_name = outcome.get('description', '')
            point = outcome.get('point')
            price = outcome.get('price')
            if not player_name or point is None:
                continue
            if player_name not in players_data:
                players_data[player_name] = {
                    'player_name': player_name, 'event_id': event_id, 'game_date': game_date,
                    'home_team': home_team, 'away_team': away_team, 'bookmaker': 'draftkings',
                    'stat_type': stat_type, 'line': point, 'over_price': None, 'under_price': None,
                }
            record = players_data[player_name]
            if bet_side == 'over':
                record['over_price'] = price
            elif bet_side == 'under':
                record['under_price'] = price

        for record in players_data.values():
            if record['over_price'] is not None:
                props.append(record)

    return props


def normalize_name_simple(name: str) -> str:
    if not name:
        return ""
    return name.lower().strip().replace("'", "").replace("-", "").replace(".", "")


def resolve_team_id_from_name(conn, odds_team_name: str) -> Optional[int]:
    db_name = shared_utils.convert_team_name(odds_team_name)
    result = conn.execute(text("""
        SELECT team_id FROM teams WHERE team_name = :team_name AND sport = 'NHL'
    """), {'team_name': db_name}).fetchone()
    if result:
        return result[0]
    print(f"    Could not resolve NHL team: {odds_team_name} (converted: {db_name})")
    return None


def resolve_player_simple(conn, player_name: str, game_date: date) -> Optional[int]:
    """Exact alias match -> exact normalized-name match (+ add alias) -> create
    placeholder player (+ add alias). No fuzzy matching here, same as NFL's
    resolve_player_simple -- fuzzy/mismatched cases get logged to
    nhl_player_name_mismatch by the actuals job instead, for manual review."""
    normalized = normalize_name_simple(player_name)

    alias_result = conn.execute(text("""
        SELECT player_id FROM nhl_player_aliases WHERE normalized_name = :name
        ORDER BY created_at DESC LIMIT 1
    """), {'name': normalized}).fetchone()
    if alias_result:
        return alias_result[0]

    player_result = conn.execute(text("""
        SELECT id FROM nhl_players WHERE normalized_name = :name
    """), {'name': normalized}).fetchone()
    if player_result:
        conn.execute(text("""
            INSERT INTO nhl_player_aliases (player_id, source, source_name, normalized_name, created_at)
            VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
            ON CONFLICT (source, normalized_name) DO NOTHING
        """), {'player_id': player_result[0], 'source_name': player_name, 'normalized_name': normalized})
        return player_result[0]

    new_player = conn.execute(text("""
        INSERT INTO nhl_players (player_name, normalized_name, first_seen_date, last_seen_date, created_at, updated_at)
        VALUES (:player_name, :normalized_name, :first_seen_date, :last_seen_date, NOW(), NOW())
        RETURNING id
    """), {'player_name': player_name, 'normalized_name': normalized, 'first_seen_date': game_date, 'last_seen_date': game_date})
    player_id = new_player.fetchone()[0]

    conn.execute(text("""
        INSERT INTO nhl_player_aliases (player_id, source, source_name, normalized_name, created_at)
        VALUES (:player_id, 'odds_api', :source_name, :normalized_name, NOW())
        ON CONFLICT (source, normalized_name) DO NOTHING
    """), {'player_id': player_id, 'source_name': player_name, 'normalized_name': normalized})
    print(f"    Created new NHL player: {player_name} (ID: {player_id})")
    return player_id


def insert_historical_props_to_db(conn, props_data: List[Dict]) -> int:
    inserted_count = 0
    for prop in props_data:
        if prop['stat_type'] not in STAT_COLUMNS:
            continue
        player_id = resolve_player_simple(conn, prop['player_name'], prop['game_date'])
        if not player_id:
            continue

        home_team_id = resolve_team_id_from_name(conn, prop['home_team'])
        away_team_id = resolve_team_id_from_name(conn, prop['away_team'])
        line_col, over_col, under_col = STAT_COLUMNS[prop['stat_type']]

        existing = conn.execute(text("""
            SELECT id FROM nhl_player_props WHERE player_id = :player_id AND odds_event_id = :odds_event_id
        """), {'player_id': player_id, 'odds_event_id': prop['event_id']}).fetchone()

        under_set_clause = f"{under_col} = :under_price," if under_col else ""
        under_insert_col = f", {under_col}" if under_col else ""
        under_insert_val = ", :under_price" if under_col else ""

        if existing:
            conn.execute(text(f"""
                UPDATE nhl_player_props
                SET {line_col} = :line, {over_col} = :over_price, {under_set_clause}
                    odds_home_team = :odds_home_team, odds_away_team = :odds_away_team,
                    odds_home_team_id = :odds_home_team_id, odds_away_team_id = :odds_away_team_id,
                    updated_at = NOW()
                WHERE id = :record_id
            """), {
                'line': prop['line'], 'over_price': prop['over_price'], 'under_price': prop['under_price'],
                'odds_home_team': prop['home_team'], 'odds_away_team': prop['away_team'],
                'odds_home_team_id': home_team_id, 'odds_away_team_id': away_team_id,
                'record_id': existing[0],
            })
        else:
            params = {
                'player_id': player_id, 'odds_event_id': prop['event_id'], 'game_date': prop['game_date'],
                'bookmaker': prop['bookmaker'], 'odds_source': 'odds_api',
                'odds_home_team': prop['home_team'], 'odds_away_team': prop['away_team'],
                'odds_home_team_id': home_team_id, 'odds_away_team_id': away_team_id,
                'line': prop['line'], 'over_price': prop['over_price'],
            }
            if under_col:
                params['under_price'] = prop['under_price']
            conn.execute(text(f"""
                INSERT INTO nhl_player_props (
                    player_id, normalized_name, odds_event_id, game_date, bookmaker, odds_source,
                    odds_home_team, odds_away_team, odds_home_team_id, odds_away_team_id,
                    {line_col}, {over_col}{under_insert_col}
                ) VALUES (
                    :player_id, (SELECT normalized_name FROM nhl_players WHERE id = :player_id),
                    :odds_event_id, :game_date, :bookmaker, :odds_source,
                    :odds_home_team, :odds_away_team, :odds_home_team_id, :odds_away_team_id,
                    :line, :over_price{under_insert_val}
                )
            """), params)
            inserted_count += 1
    return inserted_count


def import_historical_player_odds_for_date(target_date: date, conn) -> int:
    print(f"\n=== Importing Historical NHL Player Odds for {target_date} ===")
    events = get_historical_nhl_events(target_date)
    if not events:
        return 0

    eastern = pytz.timezone('US/Eastern')
    filtered = [
        e for e in events
        if e.get('commence_time')
        and datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00')).astimezone(eastern).date() == target_date
    ]
    print(f"  Filtered to {len(filtered)} events on {target_date} ET")

    total_imported = 0
    for i, event in enumerate(filtered, 1):
        event_id, commence_time = event.get('id'), event.get('commence_time')
        if not event_id or not commence_time:
            continue
        print(f"\n  Processing event {i}/{len(filtered)}: {event_id}")
        odds_data = get_historical_player_odds(event_id, target_date)
        if not odds_data:
            continue
        props_data = parse_historical_player_props(odds_data, commence_time)
        if not props_data:
            continue
        total_imported += insert_historical_props_to_db(conn, props_data)
        if i < len(filtered):
            time.sleep(3)
    return total_imported


def import_historical_odds_date_range(start_date: date, end_date: date):
    print("=== Historical NHL Player Odds Import ===")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        current_date = start_date
        total = 0
        while current_date <= end_date:
            try:
                total += import_historical_player_odds_for_date(current_date, conn)
                conn.commit()
            except Exception as e:
                print(f"Error processing {current_date}: {e}")
                conn.rollback()
            current_date += timedelta(days=1)
            if current_date <= end_date:
                time.sleep(5)
        print(f"\nTotal player prop records imported: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        start = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end = datetime.strptime(sys.argv[2], '%Y-%m-%d').date() if len(sys.argv) >= 3 else start
    else:
        start = end = date.today() - timedelta(days=1)
    import_historical_odds_date_range(start, end)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && python -m pytest tests/test_nhl_odds_import_parsing.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add jobs/nhl_historical_player_odds_import.py tests/test_nhl_odds_import_parsing.py
git commit -m "Add NHL historical player-prop odds import job"
```

---

### Task 6: `jobs/nhl_historical_player_actuals_import_reverse.py`

**Files:**
- Create: `jobs/nhl_historical_player_actuals_import_reverse.py`
- Test: `tests/test_nhl_actuals_boxscore.py`

**Interfaces:**
- Consumes: `nhl_players`/`nhl_player_aliases`/`nhl_player_props`/`nhl_player_name_mismatch` (Task 4).
- Produces: `import_historical_actuals_date_range_reverse(start_date, end_date)` and `process_game_reverse(conn, game_id, game_date) -> int` (both consumed by Task 7's orchestrator; `process_game_reverse` also consumed by Task 8's mismatch route, matching the NFL precedent where the mismatch route imports it directly).

- [ ] **Step 1: Write the failing test**

The fixture below uses the real ESPN NHL boxscore `keys` (verified live against event `401892533`, 2026-10-18 CBJ @ MIN) — note `shotsTotal` is "shots on goal" and `shootoutGoals` is unrelated, a distinction that matters because the two labels ("S" and "SOG") look confusingly swapped from their keys:

```python
from jobs.nhl_historical_player_actuals_import_reverse import build_player_stats_lookup_nhl


FIXTURE_BOXSCORE = {
    "boxscore": {
        "players": [
            {
                "team": {"id": "30", "displayName": "Minnesota Wild"},
                "statistics": [
                    {
                        "name": "forwards",
                        "keys": ["blockedShots", "hits", "takeaways", "plusMinus", "timeOnIce",
                                  "powerPlayTimeOnIce", "shortHandedTimeOnIce", "evenStrengthTimeOnIce",
                                  "shifts", "goals", "ytdGoals", "assists", "shotsTotal", "shotsMissed",
                                  "shootoutGoals", "faceoffsWon", "faceoffsLost", "faceoffPercent",
                                  "giveaways", "penalties", "penaltyMinutes"],
                        "athletes": [{
                            "athlete": {"id": "4697086", "displayName": "Danila Yurov"},
                            "stats": ["0", "0", "0", "1", "14:02", "0:00", "0:00", "14:02", "16",
                                      "1", "4", "0", "3", "0", "0", "0", "0", "0", "0", "0", "0"],
                        }],
                    },
                    {"name": "defenses", "keys": [], "athletes": []},
                    {"name": "skaters", "keys": [], "athletes": []},
                    {
                        "name": "goalies",
                        "keys": ["goalsAgainst", "shotsAgainst", "shootoutSaves", "shootoutShotsAgainst",
                                  "saves", "savePct", "evenStrengthSaves", "powerPlaySaves",
                                  "shortHandedSaves", "timeOnIce", "ytdGoals", "penaltyMinutes"],
                        "athletes": [{
                            "athlete": {"id": "4874737", "displayName": "Jesper Wallstedt"},
                            "stats": ["1", "22", "0", "0", "21", ".955", "15", "4", "2", "60:00", "0", "0"],
                        }],
                    },
                ],
            },
        ],
    },
}


def test_build_player_stats_lookup_extracts_skater_stats():
    lookup, team_info = build_player_stats_lookup_nhl(FIXTURE_BOXSCORE)
    yurov = lookup["danila yurov"]
    assert yurov["actual_goals"] == 1
    assert yurov["actual_assists"] == 4
    assert yurov["actual_shots_on_goal"] == 3  # shotsTotal, NOT the shootoutGoals ("SOG") label
    assert yurov["actual_total_saves"] is None
    assert yurov["espn_player_id"] == "4697086"


def test_build_player_stats_lookup_extracts_goalie_saves():
    lookup, team_info = build_player_stats_lookup_nhl(FIXTURE_BOXSCORE)
    wallstedt = lookup["jesper wallstedt"]
    assert wallstedt["actual_total_saves"] == 21
    assert wallstedt["actual_goals"] is None


def test_build_player_stats_lookup_team_info():
    lookup, team_info = build_player_stats_lookup_nhl(FIXTURE_BOXSCORE)
    assert team_info == [{"name": "Minnesota Wild", "espn_id": "30"}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && python -m pytest tests/test_nhl_actuals_boxscore.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'jobs.nhl_historical_player_actuals_import_reverse'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Historical NHL player-prop actuals import from ESPN's free site API,
mirroring jobs/nfl_historical_player_actuals_import_reverse.py's "reverse"
approach: fetch ESPN's boxscore once per game, then match every nhl_player_props
row for that game against it (rather than resolving player-by-player).

Team resolution uses shared_utils.convert_team_name (teams.espn_team_id is
unpopulated for NHL). "skaters" is always empty in ESPN's NHL boxscore --
real skater stats live in "forwards" and "defenses", which never overlap.
"""
import os
import sys
import time as _time
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import requests
from unidecode import unidecode
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shared_utils

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

SKATER_STAT_GROUPS = {'forwards', 'defenses'}


def normalize_player_name(name: str) -> str:
    if not name:
        return ''
    normalized = unidecode(name).lower()
    normalized = normalized.replace("'", "").replace("-", "").replace(".", "")
    return ' '.join(normalized.split())


def strip_name_suffix(normalized_name: str) -> str:
    for suffix in [' jr', ' sr', ' ii', ' iii', ' iv', ' v']:
        if normalized_name.endswith(suffix):
            return normalized_name[:-len(suffix)].strip()
    return normalized_name


def parse_name_parts(normalized_name: str) -> Tuple[str, str]:
    parts = normalized_name.strip().split()
    if not parts:
        return '', ''
    if len(parts) == 1:
        return '', parts[0]
    return ' '.join(parts[:-1]), parts[-1]


def names_match_strict(odds_name: str, espn_name: str) -> bool:
    odds_first, odds_last = parse_name_parts(strip_name_suffix(odds_name))
    espn_first, espn_last = parse_name_parts(strip_name_suffix(espn_name))
    first_match = odds_first == espn_first
    if not first_match and odds_first and espn_first:
        first_match = (len(odds_first) == 1 and espn_first.startswith(odds_first)) or \
                      (len(espn_first) == 1 and odds_first.startswith(espn_first))
    return first_match and odds_last == espn_last


def safe_int(value) -> Optional[int]:
    if value is None or value == '':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def get_nhl_games_for_date(target_date: date, retries=3, delay=2) -> List[Dict]:
    """Returns completed NHL games for target_date, sorted by start time:
    [{'game_id', 'game_datetime', 'espn_home_team_id', 'espn_away_team_id'}, ...]"""
    date_str = target_date.strftime('%Y%m%d')
    url = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
    for i in range(retries):
        try:
            response = requests.get(url, params={'dates': date_str, 'limit': 50}, timeout=30)
            response.raise_for_status()
            _time.sleep(0.2)
            data = response.json()
            games = []
            for event in data.get('events', []):
                comp = event.get('competitions', [{}])[0]
                if not comp.get('status', {}).get('type', {}).get('completed'):
                    continue
                game_datetime = None
                if event.get('date'):
                    game_datetime = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
                espn_home_id = espn_away_id = None
                for competitor in comp.get('competitors', []):
                    if competitor.get('homeAway') == 'home':
                        espn_home_id = str(competitor.get('team', {}).get('id', ''))
                    elif competitor.get('homeAway') == 'away':
                        espn_away_id = str(competitor.get('team', {}).get('id', ''))
                games.append({
                    'game_id': event.get('id'), 'game_datetime': game_datetime,
                    'espn_home_team_id': espn_home_id, 'espn_away_team_id': espn_away_id,
                })
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            games.sort(key=lambda g: g['game_datetime'] or epoch)
            return games
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching games (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                _time.sleep(delay * (i + 1))
            else:
                return []
    return []


def get_game_boxscore(game_id: str, retries=3, delay=2) -> Optional[Dict]:
    url = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary"
    for i in range(retries):
        try:
            response = requests.get(url, params={'event': game_id, 'enable': 'boxscore'}, timeout=30)
            response.raise_for_status()
            _time.sleep(0.2)
            data = response.json()
            if not data.get('boxscore'):
                return None
            return data
        except requests.exceptions.RequestException as e:
            print(f"    Error fetching boxscore (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                _time.sleep(delay * (i + 1))
            else:
                return None
    return None


def build_player_stats_lookup_nhl(boxscore_data: Dict) -> Tuple[Dict, List[Dict]]:
    """Build a normalized_name -> stat dict lookup from an ESPN NHL boxscore.
    Skater stats come from 'forwards'+'defenses' (never overlapping; 'skaters'
    is always empty); goalie stats from 'goalies'. points = goals + assists."""
    player_lookup: Dict[str, Dict] = {}
    team_info_list: List[Dict] = []

    for team_data in boxscore_data.get('boxscore', {}).get('players', []):
        team_info = team_data.get('team', {})
        team_name = team_info.get('displayName', 'Unknown Team')
        team_espn_id = str(team_info.get('id', ''))
        team_info_list.append({'name': team_name, 'espn_id': team_espn_id})

        for stat_block in team_data.get('statistics', []):
            group_name = stat_block.get('name', '')
            keys = stat_block.get('keys', [])
            athletes = stat_block.get('athletes', [])
            if group_name not in SKATER_STAT_GROUPS and group_name != 'goalies':
                continue

            for athlete_data in athletes:
                athlete = athlete_data.get('athlete', {})
                stats = athlete_data.get('stats', [])
                espn_player_id = str(athlete.get('id', ''))
                player_name = athlete.get('displayName', '')
                if not espn_player_id or not player_name or len(stats) != len(keys):
                    continue

                stat_dict = dict(zip(keys, stats))
                normalized_name = normalize_player_name(player_name)

                if normalized_name not in player_lookup:
                    player_lookup[normalized_name] = {
                        'espn_player_id': espn_player_id, 'player_name': player_name,
                        'normalized_name': normalized_name, 'did_not_play': False,
                        'player_team_espn_id': team_espn_id, 'player_team_name': team_name,
                        'actual_goals': None, 'actual_assists': None,
                        'actual_shots_on_goal': None, 'actual_total_saves': None,
                    }
                record = player_lookup[normalized_name]

                if group_name in SKATER_STAT_GROUPS:
                    record['actual_goals'] = safe_int(stat_dict.get('goals'))
                    record['actual_assists'] = safe_int(stat_dict.get('assists'))
                    record['actual_shots_on_goal'] = safe_int(stat_dict.get('shotsTotal'))
                elif group_name == 'goalies':
                    record['actual_total_saves'] = safe_int(stat_dict.get('saves'))

    return player_lookup, team_info_list


def get_team_ids_from_boxscore(boxscore_data: Dict) -> Tuple[Optional[str], Optional[str]]:
    teams = boxscore_data.get('boxscore', {}).get('players', [])
    ids = [str(t.get('team', {}).get('id', '')) for t in teams if t.get('team', {}).get('id')]
    return (ids[0], ids[1]) if len(ids) >= 2 else (None, None)


def resolve_internal_team_id_by_espn_name(conn, team_info_list: List[Dict]) -> None:
    """Mutates each entry in team_info_list, setting its internal 'id' by
    resolving the ESPN displayName through convert_team_name."""
    for team_info in team_info_list:
        db_name = shared_utils.convert_team_name(team_info['name'])
        result = conn.execute(text("""
            SELECT team_id FROM teams WHERE team_name = :team_name AND sport = 'NHL'
        """), {'team_name': db_name}).fetchone()
        team_info['id'] = result[0] if result else None


def find_player_in_lookup(normalized_name: str, lookup: Dict, conn, player_id: int) -> Optional[Dict]:
    """4-step match: ESPN ID -> exact normalized name -> alias table -> strict
    first+last name."""
    normalized_name = normalize_player_name(normalized_name)

    player_row = conn.execute(text("""
        SELECT espn_player_id FROM nhl_players WHERE id = :player_id
    """), {'player_id': player_id}).fetchone()
    if player_row and player_row[0]:
        for stats in lookup.values():
            if stats.get('espn_player_id') == player_row[0]:
                return stats

    player_stats = lookup.get(normalized_name)
    if player_stats:
        return player_stats

    alias_rows = conn.execute(text("""
        SELECT normalized_name FROM nhl_player_aliases WHERE player_id = :player_id
    """), {'player_id': player_id}).fetchall()
    for alias_row in alias_rows:
        player_stats = lookup.get(alias_row[0])
        if player_stats:
            return player_stats

    for espn_name, stats in lookup.items():
        if names_match_strict(normalized_name, espn_name):
            return stats

    return None


def process_game_reverse(conn, game_id: str, game_date: date) -> int:
    """Fetch one ESPN boxscore and update every nhl_player_props row for that
    game. Unmatched players with a known ESPN id whose current team matches
    this game are marked did_not_play; everyone else gets a nhl_player_name_mismatch
    row for manual review."""
    boxscore_data = get_game_boxscore(game_id)
    if not boxscore_data:
        return 0

    espn_team_id_1, espn_team_id_2 = get_team_ids_from_boxscore(boxscore_data)
    if not espn_team_id_1 or not espn_team_id_2:
        print("    Could not extract team IDs from boxscore")
        return 0

    player_lookup, team_info_list = build_player_stats_lookup_nhl(boxscore_data)
    resolve_internal_team_id_by_espn_name(conn, team_info_list)

    team1_id = next((t['id'] for t in team_info_list if t['espn_id'] == espn_team_id_1), None)
    team2_id = next((t['id'] for t in team_info_list if t['espn_id'] == espn_team_id_2), None)
    if not team1_id or not team2_id:
        print("    Could not resolve internal team IDs")
        return 0

    prop_records = conn.execute(text("""
        SELECT id, player_id, normalized_name, odds_home_team_id, odds_away_team_id
        FROM nhl_player_props
        WHERE game_date = :game_date
          AND (odds_home_team_id IN (:team1_id, :team2_id) OR odds_away_team_id IN (:team1_id, :team2_id))
    """), {'game_date': game_date, 'team1_id': team1_id, 'team2_id': team2_id}).fetchall()

    updated_count = 0
    for props_id, player_id, normalized_name, odds_home_team_id, odds_away_team_id in prop_records:
        player_stats = find_player_in_lookup(normalized_name, player_lookup, conn, player_id)

        if not player_stats:
            player_row = conn.execute(text("""
                SELECT espn_player_id, team_id FROM nhl_players WHERE id = :player_id
            """), {'player_id': player_id}).fetchone()
            confirmed_espn_id = player_row[0] if player_row else None

            if confirmed_espn_id and player_row[1] in (team1_id, team2_id):
                conn.execute(text("""
                    UPDATE nhl_player_props
                    SET espn_event_id = :espn_event_id, did_not_play = true,
                        actuals_unavailable_reason = 'did_not_play', updated_at = CURRENT_TIMESTAMP
                    WHERE id = :record_id
                """), {'espn_event_id': game_id, 'record_id': props_id})
            elif not confirmed_espn_id:
                home_name = conn.execute(text("SELECT team_name FROM teams WHERE team_id = :id"), {'id': odds_home_team_id}).fetchone()
                away_name = conn.execute(text("SELECT team_name FROM teams WHERE team_id = :id"), {'id': odds_away_team_id}).fetchone()
                existing = conn.execute(text("""
                    SELECT id FROM nhl_player_name_mismatch WHERE nhl_player_props_id = :props_id AND resolved = false
                """), {'props_id': props_id}).fetchone()
                if not existing:
                    conn.execute(text("""
                        INSERT INTO nhl_player_name_mismatch (
                            nhl_player_props_id, game_date, odds_home_team_id, odds_away_team_id,
                            odds_home_team, odds_away_team, normalized_name, player_id, resolved, created_at, updated_at
                        ) VALUES (
                            :props_id, :game_date, :home_id, :away_id, :home_name, :away_name,
                            :normalized_name, :player_id, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                    """), {
                        'props_id': props_id, 'game_date': game_date, 'home_id': odds_home_team_id,
                        'away_id': odds_away_team_id, 'home_name': home_name[0] if home_name else 'Unknown',
                        'away_name': away_name[0] if away_name else 'Unknown',
                        'normalized_name': normalized_name, 'player_id': player_id,
                    })
            continue

        espn_player_id = player_stats.get('espn_player_id')
        if espn_player_id and player_id:
            existing_espn_id = conn.execute(text("SELECT espn_player_id FROM nhl_players WHERE id = :id"), {'id': player_id}).fetchone()
            if existing_espn_id and not existing_espn_id[0]:
                in_use = conn.execute(text("SELECT id FROM nhl_players WHERE espn_player_id = :id"), {'id': str(espn_player_id)}).fetchone()
                if not in_use:
                    conn.execute(text("UPDATE nhl_players SET espn_player_id = :id WHERE id = :pid"),
                                 {'id': str(espn_player_id), 'pid': player_id})

        player_team_espn_id = player_stats.get('player_team_espn_id')
        player_team_id = next((t['id'] for t in team_info_list if t['espn_id'] == player_team_espn_id), None)
        opponent_info = next((t for t in team_info_list if t['espn_id'] != player_team_espn_id), None)

        if player_stats.get('did_not_play'):
            conn.execute(text("""
                UPDATE nhl_player_props
                SET player_team_name = :team_name, player_team_id = :team_id,
                    opponent_team_name = :opp_name, opponent_team_id = :opp_id,
                    espn_event_id = :espn_event_id, did_not_play = true, updated_at = CURRENT_TIMESTAMP
                WHERE id = :record_id
            """), {
                'team_name': player_stats.get('player_team_name'), 'team_id': player_team_id,
                'opp_name': opponent_info['name'] if opponent_info else 'Unknown',
                'opp_id': opponent_info['id'] if opponent_info else None,
                'espn_event_id': game_id, 'record_id': props_id,
            })
            updated_count += 1
            continue

        goals = player_stats.get('actual_goals')
        assists = player_stats.get('actual_assists')
        points = (goals or 0) + (assists or 0) if (goals is not None or assists is not None) else None

        conn.execute(text("""
            UPDATE nhl_player_props
            SET actual_player_goals = :goals, actual_player_assists = :assists,
                actual_player_points = :points, actual_player_shots_on_goal = :sog,
                actual_player_total_saves = :saves,
                actual_player_goal_scorer_anytime = :scored_anytime,
                player_team_name = :team_name, player_team_id = :team_id,
                opponent_team_name = :opp_name, opponent_team_id = :opp_id,
                espn_event_id = :espn_event_id, updated_at = CURRENT_TIMESTAMP
            WHERE id = :record_id
        """), {
            'goals': goals, 'assists': assists, 'points': points,
            'sog': player_stats.get('actual_shots_on_goal'),
            'saves': player_stats.get('actual_total_saves'),
            'scored_anytime': (goals or 0) > 0 if goals is not None else None,
            'team_name': player_stats.get('player_team_name'), 'team_id': player_team_id,
            'opp_name': opponent_info['name'] if opponent_info else 'Unknown',
            'opp_id': opponent_info['id'] if opponent_info else None,
            'espn_event_id': game_id, 'record_id': props_id,
        })
        updated_count += 1

    return updated_count


def import_historical_actuals_for_date_reverse(target_date: date, conn) -> int:
    games = get_nhl_games_for_date(target_date)
    print(f"\n=== Importing NHL Actuals for {target_date} ({len(games)} games) ===")
    total = 0
    for game in games:
        total += process_game_reverse(conn, game['game_id'], target_date)
    return total


def import_historical_actuals_date_range_reverse(start_date: date, end_date: date):
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        current_date = start_date
        total = 0
        while current_date <= end_date:
            try:
                total += import_historical_actuals_for_date_reverse(current_date, conn)
                conn.commit()
            except Exception as e:
                print(f"Error processing {current_date}: {e}")
                conn.rollback()
            current_date += timedelta(days=1)
        print(f"\nTotal records updated: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        start = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end = datetime.strptime(sys.argv[2], '%Y-%m-%d').date() if len(sys.argv) >= 3 else start
    else:
        start = end = date.today() - timedelta(days=1)
    import_historical_actuals_date_range_reverse(start, end)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && python -m pytest tests/test_nhl_actuals_boxscore.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add jobs/nhl_historical_player_actuals_import_reverse.py tests/test_nhl_actuals_boxscore.py
git commit -m "Add NHL historical player-prop actuals import job"
```

---

### Task 7: `jobs/nhl_historical_import_orchestrator_reverse.py`

**Files:**
- Create: `jobs/nhl_historical_import_orchestrator_reverse.py`

**Interfaces:**
- Consumes: `import_historical_odds_date_range` (Task 5), `import_historical_actuals_date_range_reverse` (Task 6).

- [ ] **Step 1: Write the orchestrator**

```python
#!/usr/bin/python3
"""NHL Historical Data Import Orchestrator. Runs odds import then actuals
import for a date range. No-args invocation defaults to yesterday, which is
also what this file is intended to run as via Heroku Scheduler for ongoing
daily ingestion. No defense-props step -- NHL has no team D/ST market.

Usage:
    python3 jobs/nhl_historical_import_orchestrator_reverse.py
    python3 jobs/nhl_historical_import_orchestrator_reverse.py 2023-10-10
    python3 jobs/nhl_historical_import_orchestrator_reverse.py 2023-10-10 2026-10-20
"""
import sys
import os
from datetime import date, datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobs.nhl_historical_player_odds_import import import_historical_odds_date_range
from jobs.nhl_historical_player_actuals_import_reverse import import_historical_actuals_date_range_reverse


def parse_date(date_str: str) -> date:
    for fmt in ('%Y-%m-%d', '%Y%m%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date '{date_str}'")


def main():
    print("=" * 80)
    print("NHL Historical Data Import Orchestrator")
    print("=" * 80)

    if len(sys.argv) < 2:
        start_date = end_date = date.today() - timedelta(days=1)
        print(f"\nNo date provided - defaulting to yesterday: {start_date}")
    else:
        start_date = parse_date(sys.argv[1])
        end_date = parse_date(sys.argv[2]) if len(sys.argv) >= 3 else start_date

    if start_date > end_date:
        print(f"Error: start date ({start_date}) is after end date ({end_date})")
        sys.exit(1)

    print(f"\nImporting NHL player props for {start_date} to {end_date}")

    print("\n" + "=" * 80)
    print("STEP 1: Importing Historical Odds")
    print("=" * 80)
    try:
        import_historical_odds_date_range(start_date, end_date)
    except Exception as e:
        print(f"Error during odds import: {e}")
        print("Continuing with actuals import...")

    print("\n" + "=" * 80)
    print("STEP 2: Importing Historical Actuals")
    print("=" * 80)
    import_historical_actuals_date_range_reverse(start_date, end_date)

    print("\n" + "=" * 80)
    print("Historical Data Import Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Manual verification (single real day)**

Run: `source venv/bin/activate && python jobs/nhl_historical_import_orchestrator_reverse.py 2026-10-18`
Expected: prints odds import progress for 2026-10-18's games, then actuals import progress, ending with "Historical Data Import Complete". Then verify:
```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM nhl_player_props WHERE game_date = '2026-10-18'\")
print('props:', cur.fetchone())
cur.execute(\"SELECT COUNT(*) FROM nhl_player_props WHERE game_date = '2026-10-18' AND actual_player_goals IS NOT NULL\")
print('with actuals:', cur.fetchone())
"
```
Expected: both counts > 0.

- [ ] **Step 3: Commit**

```bash
git add jobs/nhl_historical_import_orchestrator_reverse.py
git commit -m "Add NHL historical import orchestrator"
```

---

## Part D: Admin tooling

### Task 8: `api/routes/internal/nhl_mismatch.py`

**Files:**
- Create: `api/routes/internal/nhl_mismatch.py`
- Modify: `app.py`

**Interfaces:**
- Consumes: `get_game_boxscore`, `build_player_stats_lookup_nhl`, `normalize_player_name`, `process_game_reverse` from `jobs.nhl_historical_player_actuals_import_reverse` (Task 6).
- Produces: `run_auto_resolve_exact_matches(engine)` (consumed by Task 7's orchestrator if you later wire the auto-resolve sweep into it — NFL's orchestrator calls this as its Step 4; left available here but not wired into Task 7's orchestrator by default so this plan's Task 7 stays independently testable without Task 8).

- [ ] **Step 1: Write the route, porting `api/routes/internal/nfl_mismatch.py` with NHL identifiers and no defense-props branches**

```python
"""Internal tool for resolving NHL player name mismatches. Mirrors
api/routes/internal/nfl_mismatch.py exactly -- same schema shape
(nhl_player_props/nhl_players/nhl_player_aliases/nhl_player_name_mismatch),
same boxscore-fetch-by-ESPN-event-id approach. NHL has no team D/ST
equivalent, so there's nothing to split out of the candidate-scoring path.
"""
import os
import sys
from collections import defaultdict
import requests
from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from jobs.nhl_historical_player_actuals_import_reverse import (
    get_game_boxscore,
    build_player_stats_lookup_nhl,
    normalize_player_name,
    process_game_reverse,
)

load_dotenv()

INTERNAL_PASSWORD = os.getenv("INTERNAL_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")

nhl_mismatch_bp = Blueprint("nhl_mismatch", __name__)


@nhl_mismatch_bp.before_request
def check_internal_password():
    if request.method == "OPTIONS":
        return
    pwd = request.headers.get("X-Internal-Password")
    if not INTERNAL_PASSWORD or pwd != INTERNAL_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401


def _get_engine():
    return create_engine(DATABASE_URL)


_SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}


def _scoring_tokens(name: str) -> set:
    return {t for t in name.split() if t not in _SUFFIX_TOKENS}


def score_candidate(odds_name: str, espn_name: str) -> float:
    odds_tokens = _scoring_tokens(odds_name)
    espn_tokens = _scoring_tokens(espn_name)
    overlap = len(odds_tokens & espn_tokens)
    return overlap / max(len(odds_tokens), len(espn_tokens), 1)


def _date_str(game_date) -> str:
    return game_date.isoformat() if hasattr(game_date, "isoformat") else str(game_date)


def search_espn_player_api(name: str) -> list:
    try:
        resp = requests.get("https://site.api.espn.com/apis/search/v2", params={"query": name, "limit": 10}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    candidates = []
    for result_type in data.get("results", []):
        if result_type.get("type") != "player":
            continue
        for item in result_type.get("contents", []):
            uid_parts = dict(p.split(":", 1) for p in item.get("uid", "").split("~") if ":" in p)
            if uid_parts.get("l") != "90":  # NHL league id
                continue
            espn_id = uid_parts.get("a")
            display_name = item.get("displayName", "")
            if not espn_id or not display_name:
                continue
            candidates.append({"espn_player_id": espn_id, "espn_display_name": display_name, "source": "espn_search"})
    return candidates


def _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id):
    row = conn.execute(text("""
        SELECT espn_event_id FROM nhl_player_props
        WHERE game_date = :game_date AND odds_home_team_id = :home_id AND odds_away_team_id = :away_id
          AND espn_event_id IS NOT NULL AND player_id != :player_id
        LIMIT 1
    """), {"game_date": game_date, "home_id": home_team_id, "away_id": away_team_id, "player_id": player_id}).fetchone()
    return row[0] if row else None


@nhl_mismatch_bp.route("/api/internal/nhl/mismatches", methods=["GET"])
def get_mismatches():
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, player_id, normalized_name, game_date, odds_home_team, odds_away_team, nhl_player_props_id
            FROM nhl_player_name_mismatch WHERE resolved = false ORDER BY player_id, game_date
        """)).fetchall()

    groups = defaultdict(lambda: {"player_id": None, "odds_name": None, "mismatch_ids": [], "records": []})
    for id_, player_id, normalized_name, game_date, odds_home_team, odds_away_team, props_id in rows:
        g = groups[player_id]
        g["player_id"] = player_id
        g["odds_name"] = normalized_name
        g["mismatch_ids"].append(id_)
        g["records"].append({
            "id": id_, "game_date": _date_str(game_date), "odds_home_team": odds_home_team,
            "odds_away_team": odds_away_team, "nhl_player_props_id": props_id,
        })

    result = [
        {"player_id": g["player_id"], "odds_name": g["odds_name"], "total_mismatches": len(g["mismatch_ids"]),
         "mismatch_ids": g["mismatch_ids"], "records": g["records"]}
        for g in groups.values()
    ]
    result.sort(key=lambda g: g["total_mismatches"], reverse=True)
    return jsonify(result)


def _compute_mismatch_candidates(engine, player_id):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, normalized_name, game_date, odds_home_team_id, odds_away_team_id
            FROM nhl_player_name_mismatch WHERE resolved = false AND player_id = :player_id ORDER BY game_date
        """), {"player_id": player_id}).fetchall()
        if not rows:
            return None, ("No unresolved mismatches found for this player", 404)

        odds_name = rows[0][1]
        espn_event_id = None
        for row in rows:
            eid = _find_sibling_espn_event(conn, row[2], row[3], row[4], player_id)
            if eid:
                espn_event_id = eid
                break

    if not espn_event_id:
        return None, ("Could not find a sibling prop with espn_event_id for any mismatch date", 404)

    boxscore_data = get_game_boxscore(espn_event_id)
    if not boxscore_data:
        return None, (f"Could not fetch ESPN boxscore for event {espn_event_id}", 500)

    player_lookup, _ = build_player_stats_lookup_nhl(boxscore_data)
    normalized_odds = normalize_player_name(odds_name)

    candidates = []
    for espn_name, stats in player_lookup.items():
        espn_pid = stats.get("espn_player_id")
        if not espn_pid:
            continue
        candidates.append({
            "espn_player_id": espn_pid, "espn_display_name": stats.get("player_name", ""),
            "similarity_score": round(score_candidate(normalized_odds, espn_name), 3),
            "espn_event_id": espn_event_id, "source": "boxscore",
        })
    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    candidates = candidates[:8]

    if not candidates or all(c["similarity_score"] == 0.0 for c in candidates):
        tokens = [t for t in normalized_odds.split() if len(t) > 2]
        if tokens:
            conditions = " OR ".join([f"normalized_name LIKE :tok{i}" for i in range(len(tokens))])
            params = {f"tok{i}": f"%{tok}%" for i, tok in enumerate(tokens)}
            with engine.connect() as conn:
                rows = conn.execute(text(f"""
                    SELECT espn_player_id, player_name, normalized_name FROM nhl_players
                    WHERE espn_player_id IS NOT NULL AND ({conditions}) ORDER BY normalized_name LIMIT 20
                """), params).fetchall()
            db_candidates = [
                {"espn_player_id": r[0], "espn_display_name": r[1],
                 "similarity_score": round(score_candidate(normalized_odds, r[2]), 3),
                 "espn_event_id": espn_event_id, "source": "db_search"}
                for r in rows
            ]
            db_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
            candidates = db_candidates[:8]

    if not candidates or candidates[0]["similarity_score"] < 1.0:
        merged = {c["espn_player_id"]: c for c in candidates}
        for cand in search_espn_player_api(odds_name):
            score = score_candidate(normalized_odds, normalize_player_name(cand["espn_display_name"]))
            cand = {**cand, "similarity_score": round(score, 3), "espn_event_id": espn_event_id}
            existing = merged.get(cand["espn_player_id"])
            if not existing or cand["similarity_score"] > existing["similarity_score"]:
                merged[cand["espn_player_id"]] = cand
        candidates = sorted(merged.values(), key=lambda x: x["similarity_score"], reverse=True)[:8]

    return {"player_id": player_id, "odds_name": odds_name, "espn_event_id": espn_event_id, "candidates": candidates}, None


@nhl_mismatch_bp.route("/api/internal/nhl/mismatches/<int:player_id>/candidates", methods=["GET"])
def get_candidates(player_id):
    data, error = _compute_mismatch_candidates(_get_engine(), player_id)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(data)


def _do_resolve_mismatch(engine, player_id, espn_player_id, espn_name):
    espn_player_id = str(espn_player_id)
    dates_processed, dates_skipped, merged_into = [], [], None

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, game_date, odds_home_team_id, odds_away_team_id
            FROM nhl_player_name_mismatch WHERE resolved = false AND player_id = :player_id ORDER BY game_date
        """), {"player_id": player_id}).fetchall()
        mismatch_data = [tuple(row) for row in rows]
    mismatch_ids = [row[0] for row in mismatch_data]

    with engine.connect() as conn:
        try:
            conn.execute(text("UPDATE nhl_players SET espn_player_id = :id WHERE id = :pid"),
                         {"id": espn_player_id, "pid": player_id})
            conn.commit()
        except IntegrityError:
            conn.rollback()
            row = conn.execute(text("SELECT id FROM nhl_players WHERE espn_player_id = :id"), {"id": espn_player_id}).fetchone()
            if not row:
                return None, ("Duplicate ESPN ID but existing player not found", 500)
            merged_into = row[0]

            src_player = conn.execute(text("SELECT player_name, normalized_name FROM nhl_players WHERE id = :pid"),
                                       {"pid": player_id}).fetchone()

            conn.execute(text("""
                UPDATE nhl_player_props SET player_id = :target_id
                WHERE player_id = :src_id AND odds_event_id NOT IN (
                    SELECT odds_event_id FROM nhl_player_props WHERE player_id = :target_id
                )
            """), {"target_id": merged_into, "src_id": player_id})
            conn.execute(text("DELETE FROM nhl_player_name_mismatch WHERE player_id = :src_id"), {"src_id": player_id})
            conn.execute(text("DELETE FROM nhl_player_props WHERE player_id = :src_id"), {"src_id": player_id})
            conn.execute(text("DELETE FROM nhl_players WHERE id = :pid"), {"pid": player_id})

            if src_player and src_player[1] is not None:
                conn.execute(text("""
                    INSERT INTO nhl_player_aliases (player_id, source, source_name, normalized_name, created_at)
                    VALUES (:pid, 'odds_api', :name, :norm, NOW()) ON CONFLICT (source, normalized_name) DO NOTHING
                """), {"pid": merged_into, "name": src_player[0], "norm": src_player[1]})
            conn.commit()

    for mismatch_id, game_date, home_team_id, away_team_id in mismatch_data:
        date_str = _date_str(game_date)
        with engine.connect() as conn:
            eid = _find_sibling_espn_event(conn, game_date, home_team_id, away_team_id, player_id)
        if eid:
            with engine.connect() as conn:
                try:
                    process_game_reverse(conn, eid, game_date)
                    conn.commit()
                    dates_processed.append(date_str)
                except Exception as e:
                    conn.rollback()
                    print(f"Error processing game {eid} for date {date_str}: {e}")
                    dates_skipped.append(date_str)
        else:
            dates_skipped.append(date_str)

    if merged_into is None and mismatch_ids:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM nhl_player_name_mismatch WHERE id = ANY(:ids)"), {"ids": mismatch_ids})
            conn.commit()

    return {"espn_player_id_set": True, "espn_name": espn_name, "merged_into_player_id": merged_into,
            "dates_processed": dates_processed, "dates_skipped": dates_skipped}, None


@nhl_mismatch_bp.route("/api/internal/nhl/mismatches/<int:player_id>/resolve", methods=["POST"])
def resolve_mismatch(player_id):
    body = request.get_json()
    if not body or "espn_player_id" not in body:
        return jsonify({"error": "Missing espn_player_id in request body"}), 400
    result, error = _do_resolve_mismatch(_get_engine(), player_id, body["espn_player_id"], body.get("espn_name", ""))
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(result)


@nhl_mismatch_bp.route("/api/internal/nhl/placeholders", methods=["GET"])
def get_placeholder_players():
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.id, p.normalized_name, COUNT(pp.id), MIN(pp.game_date), MAX(pp.game_date)
            FROM nhl_players p JOIN nhl_player_props pp ON pp.player_id = p.id
            WHERE p.espn_player_id IS NULL
            GROUP BY p.id, p.normalized_name HAVING COUNT(pp.id) > 0
            ORDER BY COUNT(pp.id) DESC, p.normalized_name
        """)).fetchall()
    return jsonify([
        {"player_id": r[0], "normalized_name": r[1], "total_props": r[2],
         "first_game": _date_str(r[3]) if r[3] else None, "last_game": _date_str(r[4]) if r[4] else None}
        for r in rows
    ])


def _compute_placeholder_candidates(engine, player_id):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT normalized_name FROM nhl_players WHERE id = :pid AND espn_player_id IS NULL
        """), {"pid": player_id}).fetchone()
    if not row:
        return None, ("Placeholder player not found", 404)

    normalized_odds = row[0]
    tokens = [t for t in normalized_odds.split() if len(t) > 2]
    if not tokens:
        return {"player_id": player_id, "odds_name": normalized_odds, "candidates": []}, None

    conditions = " OR ".join([f"normalized_name LIKE :tok{i}" for i in range(len(tokens))])
    params = {f"tok{i}": f"%{tok}%" for i, tok in enumerate(tokens)}
    params["player_id"] = player_id
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT espn_player_id, player_name, normalized_name FROM nhl_players
            WHERE espn_player_id IS NOT NULL AND id != :player_id AND ({conditions})
            ORDER BY normalized_name LIMIT 20
        """), params).fetchall()

    candidates = [
        {"espn_player_id": r[0], "espn_display_name": r[1],
         "similarity_score": round(score_candidate(normalized_odds, r[2]), 3), "source": "db_search"}
        for r in rows
    ]
    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    candidates = candidates[:8]

    if not candidates or candidates[0]["similarity_score"] < 1.0:
        merged = {c["espn_player_id"]: c for c in candidates}
        for cand in search_espn_player_api(normalized_odds):
            score = score_candidate(normalized_odds, normalize_player_name(cand["espn_display_name"]))
            cand = {**cand, "similarity_score": round(score, 3)}
            existing = merged.get(cand["espn_player_id"])
            if not existing or cand["similarity_score"] > existing["similarity_score"]:
                merged[cand["espn_player_id"]] = cand
        candidates = sorted(merged.values(), key=lambda x: x["similarity_score"], reverse=True)[:8]

    return {"player_id": player_id, "odds_name": normalized_odds, "candidates": candidates}, None


@nhl_mismatch_bp.route("/api/internal/nhl/placeholders/<int:player_id>/candidates", methods=["GET"])
def get_placeholder_candidates(player_id):
    data, error = _compute_placeholder_candidates(_get_engine(), player_id)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(data)


def _do_resolve_placeholder(engine, player_id, espn_player_id, espn_name):
    espn_player_id = str(espn_player_id)
    merged_from = None
    target_player_id = player_id

    with engine.connect() as conn:
        try:
            conn.execute(text("""
                UPDATE nhl_players SET espn_player_id = :id WHERE id = :pid AND espn_player_id IS NULL
            """), {"id": espn_player_id, "pid": player_id})
            conn.commit()
        except IntegrityError:
            conn.rollback()
            row = conn.execute(text("SELECT id, normalized_name FROM nhl_players WHERE espn_player_id = :id"),
                                {"id": espn_player_id}).fetchone()
            if not row:
                return None, ("Duplicate ESPN ID but existing player not found", 500)
            target_player_id = row[0]
            merged_from = player_id

            src_player = conn.execute(text("SELECT player_name, normalized_name FROM nhl_players WHERE id = :pid"),
                                       {"pid": player_id}).fetchone()

            conn.execute(text("""
                UPDATE nhl_player_props SET player_id = :target_id
                WHERE player_id = :src_id AND odds_event_id NOT IN (
                    SELECT odds_event_id FROM nhl_player_props WHERE player_id = :target_id
                )
            """), {"target_id": target_player_id, "src_id": player_id})
            conn.execute(text("DELETE FROM nhl_player_aliases WHERE player_id = :pid"), {"pid": player_id})
            conn.execute(text("DELETE FROM nhl_player_name_mismatch WHERE player_id = :pid"), {"pid": player_id})
            conn.execute(text("DELETE FROM nhl_player_props WHERE player_id = :src_id"), {"src_id": player_id})
            conn.execute(text("DELETE FROM nhl_players WHERE id = :pid"), {"pid": player_id})

            if src_player and src_player[1] is not None:
                conn.execute(text("""
                    INSERT INTO nhl_player_aliases (player_id, source, source_name, normalized_name, created_at)
                    VALUES (:pid, 'odds_api', :name, :norm, NOW()) ON CONFLICT (source, normalized_name) DO NOTHING
                """), {"pid": target_player_id, "name": src_player[0], "norm": src_player[1]})
            conn.commit()

    with engine.connect() as conn:
        event_rows = conn.execute(text("""
            SELECT DISTINCT espn_event_id, game_date FROM nhl_player_props
            WHERE player_id = :pid AND espn_event_id IS NOT NULL ORDER BY game_date
        """), {"pid": target_player_id}).fetchall()
        event_data = [tuple(r) for r in event_rows]

    dates_processed, dates_skipped = [], []
    for eid, game_date in event_data:
        date_str = _date_str(game_date)
        with engine.connect() as conn:
            try:
                process_game_reverse(conn, eid, game_date)
                conn.commit()
                dates_processed.append(date_str)
            except Exception as e:
                conn.rollback()
                print(f"Error processing game {eid} for date {date_str}: {e}")
                dates_skipped.append(date_str)

    return {"espn_player_id_set": True, "espn_name": espn_name, "merged_placeholder_id": merged_from,
            "dates_processed": dates_processed, "dates_skipped": dates_skipped}, None


@nhl_mismatch_bp.route("/api/internal/nhl/placeholders/<int:player_id>/resolve", methods=["POST"])
def resolve_placeholder(player_id):
    body = request.get_json()
    if not body or "espn_player_id" not in body:
        return jsonify({"error": "Missing espn_player_id in request body"}), 400
    result, error = _do_resolve_placeholder(_get_engine(), player_id, body["espn_player_id"], body.get("espn_name", ""))
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(result)


def run_auto_resolve_exact_matches(engine):
    """Auto-confirms any mismatch/placeholder player with exactly one
    candidate at a 1.00 similarity score (no tied runner-up)."""
    resolved, skipped = [], []

    with engine.connect() as conn:
        mismatch_player_ids = [r[0] for r in conn.execute(text(
            "SELECT DISTINCT player_id FROM nhl_player_name_mismatch WHERE resolved = false"
        )).fetchall()]
        placeholder_player_ids = [r[0] for r in conn.execute(text("""
            SELECT p.id FROM nhl_players p JOIN nhl_player_props pp ON pp.player_id = p.id
            WHERE p.espn_player_id IS NULL GROUP BY p.id HAVING COUNT(pp.id) > 0
        """)).fetchall()]

    queues = [
        ("mismatch", mismatch_player_ids, _compute_mismatch_candidates, _do_resolve_mismatch),
        ("placeholder", placeholder_player_ids, _compute_placeholder_candidates, _do_resolve_placeholder),
    ]

    for queue_name, player_ids, compute_candidates, do_resolve in queues:
        for player_id in player_ids:
            try:
                data, error = compute_candidates(engine, player_id)
                if error or not data:
                    skipped.append({"player_id": player_id, "queue": queue_name, "reason": error[0] if error else "no data"})
                    continue
                candidates = data["candidates"]
                top_score = candidates[0]["similarity_score"] if candidates else 0
                runner_up_score = candidates[1]["similarity_score"] if len(candidates) > 1 else 0
                if top_score != 1.0 or runner_up_score == 1.0:
                    skipped.append({"player_id": player_id, "queue": queue_name, "odds_name": data.get("odds_name"),
                                     "reason": f"{len(candidates)} candidate(s)" if candidates else "no candidates"})
                    continue
                cand = candidates[0]
                result, error = do_resolve(engine, player_id, cand["espn_player_id"], cand["espn_display_name"])
                if error:
                    skipped.append({"player_id": player_id, "queue": queue_name, "reason": error[0]})
                    continue
                resolved.append({
                    "player_id": player_id, "queue": queue_name, "odds_name": data.get("odds_name"),
                    "espn_player_id": cand["espn_player_id"], "espn_name": cand["espn_display_name"],
                    "merged_into_player_id": result.get("merged_into_player_id") or result.get("merged_placeholder_id"),
                })
            except Exception as e:
                skipped.append({"player_id": player_id, "queue": queue_name, "reason": str(e)})

    return {"auto_resolved_count": len(resolved), "auto_resolved": resolved,
            "skipped_count": len(skipped), "skipped": skipped}


@nhl_mismatch_bp.route("/api/internal/nhl/auto-resolve-exact-matches", methods=["POST"])
def auto_resolve_exact_matches():
    return jsonify(run_auto_resolve_exact_matches(_get_engine()))
```

- [ ] **Step 2: Register the blueprint in `app.py`**

Find the NFL mismatch import/registration (around line 43 and 107-119) and add the NHL equivalent next to it:

```python
from api.routes.internal.nhl_mismatch import nhl_mismatch_bp
```
```python
app.register_blueprint(nhl_mismatch_bp)
```

- [ ] **Step 3: Manual verification**

Run the app locally (`FLASK_ENV=development python app.py`) and hit the placeholders endpoint, which should return an empty list before any props have been imported:

```bash
curl -s -H "X-Internal-Password: $INTERNAL_PASSWORD" http://127.0.0.1:5000/api/internal/nhl/placeholders
```
Expected: `[]` (no placeholder players exist yet since Task 9 hasn't run).

- [ ] **Step 4: Commit**

```bash
git add api/routes/internal/nhl_mismatch.py app.py
git commit -m "Add NHL player-name mismatch resolution admin route"
```

---

## Part E: Backfill

### Task 9: Run the 2023-season historical backfill

Not a code task — the operational step that actually populates `nhl_player_props`. Run under `caffeinate -is` (NFL's backfill hung ~79 min once when the laptop slept mid-run) with unbuffered output for live progress:

- [ ] **Step 1: Run the backfill in chunks (NHL regular season + playoffs, 2023-10-10 through today)**

```bash
caffeinate -is python -u jobs/nhl_historical_import_orchestrator_reverse.py 2023-10-10 2023-12-31 2>&1 | tee /tmp/nhl_backfill_2023_fall.log
caffeinate -is python -u jobs/nhl_historical_import_orchestrator_reverse.py 2024-01-01 2024-06-30 2>&1 | tee /tmp/nhl_backfill_2024_spring.log
caffeinate -is python -u jobs/nhl_historical_import_orchestrator_reverse.py 2024-10-01 2024-12-31 2>&1 | tee /tmp/nhl_backfill_2024_fall.log
caffeinate -is python -u jobs/nhl_historical_import_orchestrator_reverse.py 2025-01-01 2025-06-30 2>&1 | tee /tmp/nhl_backfill_2025_spring.log
caffeinate -is python -u jobs/nhl_historical_import_orchestrator_reverse.py 2025-10-01 2025-12-31 2>&1 | tee /tmp/nhl_backfill_2025_fall.log
caffeinate -is python -u jobs/nhl_historical_import_orchestrator_reverse.py 2026-01-01 2026-10-19 2>&1 | tee /tmp/nhl_backfill_2026.log
```

(Off-season gaps between each season's end and the next season's October start are skipped — no NHL games are played then, so there's nothing to import.)

- [ ] **Step 2: Verify row counts**

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute(\"SELECT MIN(game_date), MAX(game_date), COUNT(*) FROM nhl_player_props\")
print('props:', cur.fetchone())
cur.execute(\"SELECT COUNT(*) FROM nhl_player_props WHERE actual_player_goals IS NOT NULL\")
print('with actuals:', cur.fetchone())
cur.execute(\"SELECT COUNT(*) FROM nhl_player_name_mismatch WHERE resolved = false\")
print('unresolved mismatches:', cur.fetchone())
"
```
Expected: `props` min/max spans 2023-10-10 through 2026-10-19 with a count in the tens of thousands (NFL's 2.5-season backfill produced ~21,400 rows; NHL plays far more games per season than NFL, so expect substantially more). Some unresolved mismatches are expected and normal — that's what Task 8's admin route is for.

- [ ] **Step 3: Sweep auto-resolvable exact matches**

```bash
curl -s -X POST -H "X-Internal-Password: $INTERNAL_PASSWORD" http://127.0.0.1:5000/api/internal/nhl/auto-resolve-exact-matches | python3 -m json.tool
```
Expected: `auto_resolved_count` > 0, `skipped_count` reflects whatever's left for manual review via `/api/internal/nhl/mismatches` and `/api/internal/nhl/placeholders`.
