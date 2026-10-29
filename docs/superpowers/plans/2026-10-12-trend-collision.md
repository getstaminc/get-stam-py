# Trend Collision Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface, on game cards for MLB/NFL/NCAAF/soccer, how often a historical "trend collision" (today's home-side trend vs. today's away-side trend, any of the 6 streak types) has occurred league-wide and what happened — straight-up winner, ATS cover, and total result.

**Architecture:** A new `trend_collision_service.py` module builds, once per sport per cache window, an "entering streak" index (per team, per game, the streak value *before* that game — in both a venue-agnostic "general" flavor and venue-pinned "home-only"/"away-only" flavors) plus a flat `collision_index` of every historical game tagged with both teams' entering streaks and that game's outcome. `get_collision_stats()` queries that index for a given (home-side trend, away-side trend) pair. `trend_enrichment.py`'s existing `enrich_game_trends()` is extended to compute this for every (home trend × away trend) combination on a game and attach matches as a new `collisionTrends` category, shaped as ordinary `TrendResult` objects so the existing frontend rendering needs no new component.

**Tech Stack:** Python/Flask backend (psycopg2, no ORM), React/TypeScript frontend, pytest.

**Spec:** [docs/superpowers/specs/2026-10-12-trend-collision-design.md](../specs/2026-10-12-trend-collision-design.md)

## Global Constraints

- Trend types: `win_streak`, `loss_streak`, `cover_streak`, `no_cover_streak`, `over_streak`, `under_streak` — any type may pair with any other.
- Match scope: league-wide (any two teams), not restricted to today's specific matchup.
- Match threshold: `>=` (at least that long), not exact.
- Outcome metrics: straight-up winner, ATS cover, and over/under — each as rate + sample size.
- Venue-specific trends (`homeTeamHomeTrends`/`awayTeamAwayTrends`) are pinned to the home/away role they're defined for. General trends (`homeTeamTrends`/`awayTeamTrends`) carry no venue identity — the historical search pools both arrangements (today's home/away roles may be satisfied by either physical team in a historical game).
- Sport scope for v1: `mlb`, `nfl`, `ncaaf`, `soccer_epl`/`soccer_laliga`/`soccer_bundesliga`/`soccer_ligue1`/`soccer_seriea` (the sports already wired into `enrich_game_trends`). No NBA/NHL/NCAAB work.
- No new DB schema/columns/migrations.

---

### Task 1: Extend `trend_context_service.py`'s data with `game_id` and `is_home`, add two small public helpers

**Files:**
- Modify: `api/services/historical/trend_context_service.py:164-268` (`_load_sport_context`), and add two new public functions near the bottom of the "Public API" section (after line 433, before `get_streak_context`).
- Test: `tests/services/historical/test_trend_context_service.py` (new file; new `tests/services/historical/` package needs an `__init__.py` — check whether `tests/` elsewhere uses one; this repo's `tests/` has no `__init__.py` files per `pytest.ini`'s `pythonpath = .`, so don't add one here either, just the new subdirectory and test file).

**Interfaces:**
- Produces: `get_trend_types(sport: str) -> Tuple[str, ...]` — pure function, no DB. `get_sport_context(sport: str) -> Optional[Dict]` — thin public wrapper around `_load_sport_context`.
- Produces (data shape change, consumed by Task 2+): every dict in `team_games[team]` now also has `'game_id'` and `'is_home'` (bool) keys. Every dict appended to `home_h2h_games[(ht, at)]` / `gen_h2h_games[...]` now also has `'game_id'`.

- [ ] **Step 1: Write the failing test for `get_trend_types`**

Create `tests/services/historical/test_trend_context_service.py`:

```python
from api.services.historical.trend_context_service import get_trend_types


def test_get_trend_types_includes_cover_for_sports_with_real_spread():
    assert get_trend_types('nfl') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak', 'cover_streak', 'no_cover_streak')
    assert get_trend_types('ncaaf') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak', 'cover_streak', 'no_cover_streak')
    assert get_trend_types('soccer_epl') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak', 'cover_streak', 'no_cover_streak')


def test_get_trend_types_excludes_cover_for_sports_without_real_spread():
    assert get_trend_types('mlb') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak')
    assert get_trend_types('nba') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak')
    assert get_trend_types('nhl') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak')


def test_get_trend_types_unknown_sport_returns_base_only():
    assert get_trend_types('not_a_sport') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/services/historical/test_trend_context_service.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_trend_types'`

- [ ] **Step 3: Implement `get_trend_types` and `get_sport_context`**

In `api/services/historical/trend_context_service.py`, add after the `_pct` helper (line 398, before `get_streak_stats`):

```python
def get_trend_types(sport: str) -> Tuple[str, ...]:
    """The trend types this sport's continuation/collision engines support.
    Cover/no-cover is only included for sports with a real (non-moneyline-duplicate)
    spread column configured in SPORT_CONFIG."""
    cfg = SPORT_CONFIG.get(sport, {})
    base = ('over_streak', 'under_streak', 'win_streak', 'loss_streak')
    if cfg.get('home_spread') and cfg.get('away_spread'):
        return base + ('cover_streak', 'no_cover_streak')
    return base


def get_sport_context(sport: str) -> Optional[Dict]:
    """Public accessor for the cached per-sport game context (team_games,
    home_h2h_games, etc.) — for other modules (e.g. trend_collision_service)
    that need the raw loaded data rather than a continuation-rate query."""
    return _load_sport_context(sport)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/services/historical/test_trend_context_service.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Add `game_id` to the SQL query and `is_home` to `team_games`**

In `_load_sport_context` (same file), modify the query (around line 188-198):

```python
        query = f"""
            SELECT game_id, game_date, home_team_name, away_team_name,
                   {cfg['home_score']} AS hs,
                   {cfg['away_score']} AS aw,
                   {cfg['total_col']}  AS tl,
                   home_money_line    AS hml,
                   away_money_line    AS aml{spread_select}
            FROM {cfg['table']}
            WHERE {cfg['home_score']} IS NOT NULL AND {cfg['away_score']} IS NOT NULL{league_where}
            ORDER BY game_date ASC{', ' + cfg['time_col'] + ' ASC NULLS LAST' if cfg.get('time_col') else ''}, game_id ASC
        """
```

(Only change: `game_id` added as the first selected column.)

Then modify the row-processing loop (around line 209-226):

```python
        for row in rows:
            ht, at = row['home_team_name'], row['away_team_name']
            hln, aln = row.get('hln'), row.get('aln')
            gid = row['game_id']
            # 'ln' is the home team's own spread (for home_h2h/gen_h2h, perspective is home);
            # 'aln' is kept alongside so the away-perspective flip in _continuation_stats can use it.
            g = {'game_id': gid, 'hs': row['hs'], 'aw': row['aw'], 'tl': row['tl'], 'game_date': row['game_date'],
                 'hml': row['hml'], 'aml': row['aml'], 'ln': hln, 'aln': aln}
            home_h2h_games[(ht, at)].append(g)
            gen_h2h_games[(min(ht, at), max(ht, at))].append(g)
            # Team-perspective: each team's own score, own ML, and own spread first.
            # 'is_home' records which role this team actually played in this specific
            # game, so a venue-filtered (home-only/away-only) subsequence can be derived.
            team_games[ht].append({
                'game_id': gid, 'hs': row['hs'], 'aw': row['aw'], 'tl': row['tl'],
                'game_date': row['game_date'], 'hml': row['hml'], 'ln': hln, 'is_home': True,
            })
            team_games[at].append({
                'game_id': gid, 'hs': row['aw'], 'aw': row['hs'], 'tl': row['tl'],
                'game_date': row['game_date'], 'hml': row['aml'], 'ln': aln, 'is_home': False,
            })
```

- [ ] **Step 6: Run the full existing test suite to confirm nothing else broke**

Run: `pytest tests/ -v`
Expected: PASS (all prior tests still pass — this module isn't imported by any existing test, so this is a pure sanity check, not a regression test for this change specifically. There is no existing DB-mocking convention in this repo for `_load_sport_context`'s SQL itself; the new `game_id`/`is_home` fields are instead pinned by Task 2–4's unit tests, which construct fixture data in this exact shape.)

- [ ] **Step 7: Commit**

```bash
git add api/services/historical/trend_context_service.py tests/services/historical/test_trend_context_service.py
git commit -m "feat: add game_id/is_home to trend context, expose get_trend_types/get_sport_context"
```

---

### Task 2: `trend_collision_service.py` — forward-walked entering-streak computation

**Files:**
- Create: `api/services/historical/trend_collision_service.py`
- Test: `tests/services/historical/test_trend_collision_service.py` (new)

**Interfaces:**
- Consumes: nothing from other tasks yet (pure functions over plain dicts).
- Produces: `_build_entering_streaks(team_games: Dict[str, List[Dict]], trend_types: Tuple[str, ...]) -> Tuple[Dict, Dict, Dict]` returning `(general, home_venue, away_venue)`, each shaped `{team_name: {game_id: {trend_type: int}}}`. Game dicts consumed must have `game_id`, `game_date`, `hs`, `aw`, `tl`, `ln`, `is_home` keys (Task 1's shape).

- [ ] **Step 1: Write the failing tests**

Create `tests/services/historical/test_trend_collision_service.py`:

```python
from api.services.historical.trend_collision_service import _build_entering_streaks

TREND_TYPES = ('over_streak', 'under_streak', 'win_streak', 'loss_streak', 'cover_streak', 'no_cover_streak')


def _game(game_id, date, hs, aw, tl, ln, is_home):
    return {'game_id': game_id, 'game_date': date, 'hs': hs, 'aw': aw, 'tl': tl, 'ln': ln, 'is_home': is_home}


def test_general_entering_streak_walks_forward_and_resets():
    # Dodgers: W, W, L, W (chronological) -> entering win_streak before each game: 0, 1, 0, 0
    games = [
        _game('g1', '2026-01-01', 5, 1, 6, 0, True),   # win
        _game('g2', '2026-01-02', 5, 1, 6, 0, False),  # win
        _game('g3', '2026-01-03', 1, 5, 6, 0, True),   # loss
        _game('g4', '2026-01-04', 5, 1, 6, 0, False),  # win
    ]
    general, _, _ = _build_entering_streaks({'Dodgers': games}, TREND_TYPES)
    assert general['Dodgers']['g1']['win_streak'] == 0
    assert general['Dodgers']['g2']['win_streak'] == 1
    assert general['Dodgers']['g3']['win_streak'] == 2
    assert general['Dodgers']['g4']['win_streak'] == 0


def test_home_venue_entering_streak_only_counts_home_games():
    # Dodgers home games only, in order: W (g1), L (g3) -> entering win_streak: 0, 1
    # g2/g4 are away games and must not affect the home-only sequence at all.
    games = [
        _game('g1', '2026-01-01', 5, 1, 6, 0, True),   # home win
        _game('g2', '2026-01-02', 1, 5, 6, 0, False),  # away loss
        _game('g3', '2026-01-03', 1, 5, 6, 0, True),   # home loss
        _game('g4', '2026-01-04', 5, 1, 6, 0, False),  # away win
    ]
    _, home_venue, away_venue = _build_entering_streaks({'Dodgers': games}, TREND_TYPES)
    assert home_venue['Dodgers']['g1']['win_streak'] == 0
    assert home_venue['Dodgers']['g3']['win_streak'] == 1
    assert 'g2' not in home_venue['Dodgers']
    assert 'g4' not in home_venue['Dodgers']
    assert away_venue['Dodgers']['g2']['loss_streak'] == 0
    assert away_venue['Dodgers']['g4']['loss_streak'] == 1  # entering g4, away loss-streak is 1 (from g2)


def test_entering_streak_skips_games_missing_required_data_for_that_trend_type():
    # g2 has no spread ('ln' is None) -> excluded from cover_streak's sequence only.
    games = [
        _game('g1', '2026-01-01', 5, 1, 6, -3, True),   # covers (5-3=2 < 1? no: 5+(-3)=2 > 1 -> covers)
        _game('g2', '2026-01-02', 5, 1, 6, None, True),  # no spread data
        _game('g3', '2026-01-03', 5, 1, 6, -3, True),   # covers
    ]
    general, _, _ = _build_entering_streaks({'Dodgers': games}, TREND_TYPES)
    assert general['Dodgers']['g1']['cover_streak'] == 0
    assert 'cover_streak' not in general['Dodgers'].get('g2', {})
    assert general['Dodgers']['g3']['cover_streak'] == 1  # only g1 counted as prior cover
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/services/historical/test_trend_collision_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api.services.historical.trend_collision_service'`

- [ ] **Step 3: Implement `trend_collision_service.py`**

Create `api/services/historical/trend_collision_service.py`:

```python
"""Trend collision service — given a trend active on each side of a matchup
(any of the 6 streak types, at any venue-scope), find every historical game
where that same collision occurred league-wide and report what happened.
"""

from typing import Any, Dict, List, Tuple


def _typed_results(games: List[Dict], trend_type: str) -> List[Tuple[Any, bool]]:
    """Chronologically-ordered (game_id, result) pairs for one trend type.
    Games missing the data a type needs are skipped entirely (same semantics
    as trend_context_service._game_results)."""
    out: List[Tuple[Any, bool]] = []
    for g in sorted(games, key=lambda x: x['game_date']):
        hs, aw, tl, ln = g.get('hs'), g.get('aw'), g.get('tl'), g.get('ln')
        if hs is None or aw is None:
            continue
        if trend_type in ('over_streak', 'under_streak') and tl is None:
            continue
        if trend_type in ('cover_streak', 'no_cover_streak') and ln is None:
            continue

        if trend_type == 'over_streak':
            result = (hs + aw) > tl
        elif trend_type == 'under_streak':
            result = (hs + aw) < tl
        elif trend_type == 'win_streak':
            result = hs > aw
        elif trend_type == 'loss_streak':
            result = hs < aw
        elif trend_type == 'cover_streak':
            result = (hs + ln) > aw
        elif trend_type == 'no_cover_streak':
            result = (hs + ln) < aw
        else:
            continue
        out.append((g['game_id'], result))
    return out


def _entering_streaks_for_games(games: List[Dict], trend_type: str) -> Dict[Any, int]:
    """Entering-streak snapshot (the running count BEFORE each game) for one
    trend type, walked forward chronologically."""
    snapshots: Dict[Any, int] = {}
    current = 0
    for game_id, result in _typed_results(games, trend_type):
        snapshots[game_id] = current
        current = current + 1 if result else 0
    return snapshots


def _build_entering_streaks(
    team_games: Dict[str, List[Dict]],
    trend_types: Tuple[str, ...],
) -> Tuple[Dict[str, Dict[Any, Dict[str, int]]], Dict[str, Dict[Any, Dict[str, int]]], Dict[str, Dict[Any, Dict[str, int]]]]:
    """For every team, compute entering-streak snapshots in three flavors:
    general (all games), home_venue (only games that team played at home),
    away_venue (only games that team played away). Returns
    (general, home_venue, away_venue), each shaped
    {team_name: {game_id: {trend_type: entering_streak_count}}}.
    """
    general: Dict[str, Dict[Any, Dict[str, int]]] = {}
    home_venue: Dict[str, Dict[Any, Dict[str, int]]] = {}
    away_venue: Dict[str, Dict[Any, Dict[str, int]]] = {}

    for team, games in team_games.items():
        general[team] = {}
        home_venue[team] = {}
        away_venue[team] = {}
        home_games = [g for g in games if g.get('is_home')]
        away_games = [g for g in games if not g.get('is_home')]

        for tt in trend_types:
            for game_id, count in _entering_streaks_for_games(games, tt).items():
                general[team].setdefault(game_id, {})[tt] = count
            for game_id, count in _entering_streaks_for_games(home_games, tt).items():
                home_venue[team].setdefault(game_id, {})[tt] = count
            for game_id, count in _entering_streaks_for_games(away_games, tt).items():
                away_venue[team].setdefault(game_id, {})[tt] = count

    return general, home_venue, away_venue
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/services/historical/test_trend_collision_service.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add api/services/historical/trend_collision_service.py tests/services/historical/test_trend_collision_service.py
git commit -m "feat: compute general and venue-specific entering-streak indexes"
```

---

### Task 3: Build the `collision_index` from `home_h2h_games` + entering streaks

**Files:**
- Modify: `api/services/historical/trend_collision_service.py`
- Test: `tests/services/historical/test_trend_collision_service.py`

**Interfaces:**
- Consumes: `_build_entering_streaks` output (Task 2).
- Produces: `_build_collision_index(home_h2h_games: Dict[Tuple[str, str], List[Dict]], general: Dict, home_venue: Dict, away_venue: Dict, has_spread: bool) -> List[Dict]`. Each record: `{'game_id', 'home': {'name', 'general', 'home_venue'}, 'away': {'name', 'general', 'away_venue'}, 'outcome': {'winner', 'ats_result', 'total_result'}}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/services/historical/test_trend_collision_service.py`:

```python
from api.services.historical.trend_collision_service import _build_collision_index


def test_collision_index_records_winner_ats_and_total():
    home_h2h_games = {
        ('Huskers', 'Sooners'): [
            {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 30, 'aw': 20, 'tl': 45, 'ln': -3},  # home wins, home covers (30-3=27>20), over (50>45)
        ],
    }
    general = {'Huskers': {'g1': {'win_streak': 5}}, 'Sooners': {'g1': {'loss_streak': 5}}}
    home_venue = {'Huskers': {'g1': {'win_streak': 5}}}
    away_venue = {'Sooners': {'g1': {'loss_streak': 5}}}

    index = _build_collision_index(home_h2h_games, general, home_venue, away_venue, has_spread=True)

    assert len(index) == 1
    record = index[0]
    assert record['game_id'] == 'g1'
    assert record['home']['name'] == 'Huskers'
    assert record['home']['general'] == {'win_streak': 5}
    assert record['home']['home_venue'] == {'win_streak': 5}
    assert record['away']['name'] == 'Sooners'
    assert record['away']['general'] == {'loss_streak': 5}
    assert record['away']['away_venue'] == {'loss_streak': 5}
    assert record['outcome'] == {'winner': 'home', 'ats_result': 'home', 'total_result': 'over'}


def test_collision_index_handles_ties_pushes_and_missing_data():
    home_h2h_games = {
        ('A', 'B'): [
            {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 10, 'tl': 20, 'ln': 0},   # tie, ats push, total push
            {'game_id': 'g2', 'game_date': '2026-01-02', 'hs': 10, 'aw': 8, 'tl': None, 'ln': None},  # no spread/total configured
        ],
    }
    index = _build_collision_index(home_h2h_games, {}, {}, {}, has_spread=True)
    g1, g2 = (r for r in index if r['game_id'] in ('g1', 'g2'))
    assert g1['outcome'] == {'winner': None, 'ats_result': 'push', 'total_result': 'push'}
    assert g2['outcome'] == {'winner': 'home', 'ats_result': None, 'total_result': None}  # ln/tl both None -> no spread/total data for this game
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/services/historical/test_trend_collision_service.py -v`
Expected: FAIL with `ImportError: cannot import name '_build_collision_index'`

- [ ] **Step 3: Implement `_build_collision_index`**

Add to `api/services/historical/trend_collision_service.py`:

```python
def _build_collision_index(
    home_h2h_games: Dict[Tuple[str, str], List[Dict]],
    general: Dict[str, Dict[Any, Dict[str, int]]],
    home_venue: Dict[str, Dict[Any, Dict[str, int]]],
    away_venue: Dict[str, Dict[Any, Dict[str, int]]],
    has_spread: bool,
) -> List[Dict]:
    """One record per historical game, carrying both teams' entering streaks
    and that game's outcome (straight-up / ATS / total)."""
    index: List[Dict] = []
    for (home_team, away_team), games in home_h2h_games.items():
        for g in games:
            game_id = g['game_id']
            hs, aw, tl, ln = g.get('hs'), g.get('aw'), g.get('tl'), g.get('ln')
            if hs is None or aw is None:
                continue

            if hs > aw:
                winner = 'home'
            elif hs < aw:
                winner = 'away'
            else:
                winner = None

            if has_spread and ln is not None:
                if hs + ln > aw:
                    ats_result = 'home'
                elif hs + ln < aw:
                    ats_result = 'away'
                else:
                    ats_result = 'push'
            else:
                ats_result = None

            if tl is not None:
                total = hs + aw
                if total > tl:
                    total_result = 'over'
                elif total < tl:
                    total_result = 'under'
                else:
                    total_result = 'push'
            else:
                total_result = None

            index.append({
                'game_id': game_id,
                'home': {
                    'name': home_team,
                    'general': general.get(home_team, {}).get(game_id, {}),
                    'home_venue': home_venue.get(home_team, {}).get(game_id, {}),
                },
                'away': {
                    'name': away_team,
                    'general': general.get(away_team, {}).get(game_id, {}),
                    'away_venue': away_venue.get(away_team, {}).get(game_id, {}),
                },
                'outcome': {
                    'winner': winner,
                    'ats_result': ats_result,
                    'total_result': total_result,
                },
            })
    return index
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/services/historical/test_trend_collision_service.py -v`
Expected: PASS (5 tests total)

- [ ] **Step 5: Commit**

```bash
git add api/services/historical/trend_collision_service.py tests/services/historical/test_trend_collision_service.py
git commit -m "feat: build collision_index from home_h2h_games and entering streaks"
```

---

### Task 4: Per-sport cache loader + `get_collision_stats()` query function

**Files:**
- Modify: `api/services/historical/trend_collision_service.py`
- Test: `tests/services/historical/test_trend_collision_service.py`

**Interfaces:**
- Consumes: `get_sport_context`, `get_trend_types`, `SPORT_CONFIG` from `trend_context_service` (Task 1); `_build_entering_streaks`, `_build_collision_index` (Tasks 2-3).
- Produces: `get_collision_stats(sport: str, home_criterion: Dict, away_criterion: Dict) -> Optional[Dict]`. Each criterion: `{'trend_type': str, 'min_length': int, 'venue': 'general' | 'venue_specific'}`. Return shape: `{'sample_size': int, 'straight_up': {'home_side_win_rate': float, 'sample_size': int} | None, 'ats': {...} | None, 'total': {...} | None}`, or `None` if no sport context or zero matches.

This is the function Task 5 (`trend_enrichment.py`) calls directly — test it thoroughly, since its matching rule (straight vs. swapped arrangement) is the crux of the whole feature.

- [ ] **Step 1: Write the failing tests**

Append to `tests/services/historical/test_trend_collision_service.py`:

```python
from unittest.mock import patch
from api.services.historical.trend_collision_service import get_collision_stats, _collision_cache


def _ctx(team_games, home_h2h_games):
    return {'team_games': team_games, 'home_h2h_games': home_h2h_games}


def setup_function(_):
    _collision_cache.clear()


def test_venue_specific_criteria_are_pinned_to_their_role_no_swap():
    # Home team's home-venue win_streak of 5 meets away team's away-venue loss_streak of 5.
    # A reversed arrangement (if it existed) must NOT be counted for venue-specific criteria.
    # Huskers' and Sooners' only *recorded matchup* is g1 (hs=30, aw=10, tl=35 -> total 40 is OVER,
    # ln=-3 -> home covers 27>10). Five prior home wins/away losses (dated before g1) give each team
    # an entering streak of exactly 5 at g1 — the minimum the query asks for.
    deciding = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 30, 'aw': 10, 'tl': 35, 'ln': -3}
    home_h2h_games = {('Huskers', 'Sooners'): [deciding]}

    prior_huskers_home_wins = [
        {'game_id': f'h{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 20, 'aw': 10, 'tl': 30, 'ln': -3, 'is_home': True}
        for i in range(1, 6)
    ]
    prior_sooners_away_losses = [
        {'game_id': f's{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 20, 'tl': 30, 'ln': 3, 'is_home': False}
        for i in range(1, 6)
    ]
    team_games = {
        'Huskers': prior_huskers_home_wins + [{**deciding, 'is_home': True}],
        'Sooners': prior_sooners_away_losses + [{**deciding, 'hs': 10, 'aw': 30, 'ln': 3, 'is_home': False}],
    }

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'ncaaf': {'home_spread': 'home_line', 'away_spread': 'away_line'}}):
        stats = get_collision_stats(
            'ncaaf',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'venue_specific'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'venue_specific'},
        )

    assert stats['sample_size'] == 1
    assert stats['straight_up']['home_side_win_rate'] == 1.0
    assert stats['ats']['home_side_cover_rate'] == 1.0
    assert stats['total']['over_rate'] == 1.0


def test_general_criteria_pool_both_arrangements():
    # Team A enters with a 5-game win_streak as the home_h2h AWAY team (A@B), and B enters with a
    # 5-game loss_streak as the home_h2h HOME team. Since both criteria are general, querying
    # "home: win_streak>=5, away: loss_streak>=5" must still match via the swapped arrangement.
    prior_a_wins = [
        {'game_id': f'a{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 20, 'aw': 10, 'tl': 30, 'ln': None, 'is_home': True}
        for i in range(1, 6)
    ]
    prior_b_losses = [
        {'game_id': f'b{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 20, 'tl': 30, 'ln': None, 'is_home': True}
        for i in range(1, 6)
    ]
    # The deciding game: B is home, A is away (A still carries its general win_streak, B its general loss_streak)
    deciding = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 15, 'aw': 25, 'tl': 30, 'ln': None}
    team_games = {
        'A': prior_a_wins + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 25, 'aw': 15, 'tl': 30, 'ln': None, 'is_home': False}],
        'B': prior_b_losses + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 15, 'aw': 25, 'tl': 30, 'ln': None, 'is_home': True}],
    }
    home_h2h_games = {('B', 'A'): [deciding]}  # the prior games belong to other opponents; only g1 is B-vs-A

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'mlb': {}}):
        stats = get_collision_stats(
            'mlb',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'general'},
        )

    assert stats['sample_size'] == 1
    # A (literal away team) satisfied the "home" criterion via the swap, and A lost this game (15<25 means
    # literal home B=15 lost, literal away A=25 won) -> home_side (=A) won.
    assert stats['straight_up']['home_side_win_rate'] == 1.0


def test_below_threshold_does_not_match():
    team_games = {
        'A': [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 30, 'ln': None, 'is_home': True}],
        'B': [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 30, 'ln': None, 'is_home': False}],
    }
    home_h2h_games = {('A', 'B'): [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 30, 'ln': None}]}

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'mlb': {}}):
        stats = get_collision_stats(
            'mlb',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'general'},  # A has 0 entering win_streak (first game)
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'general'},
        )

    assert stats is None


def test_no_sport_context_returns_none():
    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=None):
        assert get_collision_stats(
            'mlb',
            {'trend_type': 'win_streak', 'min_length': 3, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 3, 'venue': 'general'},
        ) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/services/historical/test_trend_collision_service.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_collision_stats'` (and `_collision_cache`)

- [ ] **Step 3: Implement the loader and `get_collision_stats`**

Add to the top of `api/services/historical/trend_collision_service.py` (imports) and the bottom (new code):

```python
from .trend_context_service import SPORT_CONFIG, get_sport_context, get_trend_types

_collision_cache: Dict[str, Dict] = {}


def _load_collision_context(sport: str) -> Any:
    if sport in _collision_cache:
        return _collision_cache[sport]

    ctx = get_sport_context(sport)
    if not ctx:
        return None

    cfg = SPORT_CONFIG.get(sport, {})
    has_spread = bool(cfg.get('home_spread') and cfg.get('away_spread'))
    trend_types = get_trend_types(sport)

    general, home_venue, away_venue = _build_entering_streaks(ctx.get('team_games', {}), trend_types)
    collision_index = _build_collision_index(
        ctx.get('home_h2h_games', {}), general, home_venue, away_venue, has_spread,
    )

    result = {'collision_index': collision_index}
    _collision_cache[sport] = result
    return result


def get_collision_stats(
    sport: str,
    home_criterion: Dict[str, Any],
    away_criterion: Dict[str, Any],
) -> Any:
    """Scan the sport's collision_index for every historical game matching both
    criteria (>= threshold). 'home_side' in the result labels whichever team
    satisfied home_criterion in each matched game — the literal home team,
    unless both criteria are 'general' and a role-swapped arrangement matched
    instead (general trends carry no venue identity, so either physical team
    may satisfy either side of the query)."""
    ctx = _load_collision_context(sport)
    if not ctx:
        return None

    both_general = home_criterion['venue'] == 'general' and away_criterion['venue'] == 'general'

    matches = 0
    su_wins = su_total = 0
    ats_wins = ats_total = 0
    over_count = over_total = 0

    for game in ctx['collision_index']:
        home_pool = game['home']['home_venue'] if home_criterion['venue'] == 'venue_specific' else game['home']['general']
        away_pool = game['away']['away_venue'] if away_criterion['venue'] == 'venue_specific' else game['away']['general']
        home_val = home_pool.get(home_criterion['trend_type'], 0)
        away_val = away_pool.get(away_criterion['trend_type'], 0)

        straight = home_val >= home_criterion['min_length'] and away_val >= away_criterion['min_length']

        swapped = False
        if not straight and both_general:
            swapped_home_val = game['away']['general'].get(home_criterion['trend_type'], 0)
            swapped_away_val = game['home']['general'].get(away_criterion['trend_type'], 0)
            swapped = swapped_home_val >= home_criterion['min_length'] and swapped_away_val >= away_criterion['min_length']

        if not (straight or swapped):
            continue

        matches += 1
        home_side_is_literal_home = straight

        winner = game['outcome']['winner']
        if winner is not None:
            su_total += 1
            home_side_won = (winner == 'home') if home_side_is_literal_home else (winner == 'away')
            if home_side_won:
                su_wins += 1

        ats_result = game['outcome']['ats_result']
        if ats_result not in (None, 'push'):
            ats_total += 1
            home_side_covered = (ats_result == 'home') if home_side_is_literal_home else (ats_result == 'away')
            if home_side_covered:
                ats_wins += 1

        total_result = game['outcome']['total_result']
        if total_result not in (None, 'push'):
            over_total += 1
            if total_result == 'over':
                over_count += 1

    if matches == 0:
        return None

    return {
        'sample_size': matches,
        'straight_up': {'home_side_win_rate': su_wins / su_total, 'sample_size': su_total} if su_total else None,
        'ats': {'home_side_cover_rate': ats_wins / ats_total, 'sample_size': ats_total} if ats_total else None,
        'total': {'over_rate': over_count / over_total, 'sample_size': over_total} if over_total else None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/services/historical/test_trend_collision_service.py -v`
Expected: PASS (9 tests total)

- [ ] **Step 5: Commit**

```bash
git add api/services/historical/trend_collision_service.py tests/services/historical/test_trend_collision_service.py
git commit -m "feat: add get_collision_stats query with general-vs-venue-specific matching rules"
```

---

### Task 5: Attach `collisionTrends` in `trend_enrichment.py`

**Files:**
- Modify: `api/services/historical/trend_enrichment.py`
- Test: `tests/services/historical/test_trend_enrichment.py` (new)

**Interfaces:**
- Consumes: `get_collision_stats(sport, home_criterion, away_criterion)` (Task 4).
- Produces: `enrich_game_trends(results, sport)` now also sets `game_trends['collisionTrends']`, a `List[Dict]` where each dict has `type: 'win_streak' | 'loss_streak'`, `count: int`, `description: str`, `continuation_rate: float`, `sample_size: int` (so it slots directly into the frontend's existing `TrendResult[]` rendering — see Task 6-8), plus the richer structured fields `home_trend`, `away_trend`, `straight_up_rate`, `ats_rate`, `total_rate`, `secondary_rates: List[Dict]` for anything beyond the primary metric.

- [ ] **Step 1: Write the failing test**

Create `tests/services/historical/test_trend_enrichment.py`:

```python
from unittest.mock import patch

from api.services.historical.trend_enrichment import enrich_game_trends


def _game_trends():
    return {
        'game': {'home': {'team': 'Huskers', 'odds': {'h2h': -150}}, 'away': {'team': 'Sooners', 'odds': {'h2h': 130}}},
        'homeTeamTrends': [],
        'awayTeamTrends': [],
        'headToHeadTrends': [],
        'homeTeamHomeTrends': [{'type': 'win_streak', 'count': 5, 'description': 'Huskers won 5 straight at home'}],
        'awayTeamAwayTrends': [{'type': 'loss_streak', 'count': 5, 'description': 'Sooners lost 5 straight on the road'}],
        'homeAtHomeH2HTrends': [],
    }


def test_collision_trends_attached_when_stats_available():
    stats = {
        'sample_size': 14,
        'straight_up': {'home_side_win_rate': 0.62, 'sample_size': 14},
        'ats': {'home_side_cover_rate': 0.55, 'sample_size': 12},
        'total': {'over_rate': 0.48, 'sample_size': 14},
    }
    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', return_value=stats):
        results = enrich_game_trends([_game_trends()], 'ncaaf')

    collisions = results[0]['collisionTrends']
    assert len(collisions) == 1
    c = collisions[0]
    assert c['type'] in ('win_streak', 'loss_streak')
    assert c['sample_size'] == 14
    assert c['continuation_rate'] == 0.62  # straight_up is furthest from 0.5 among the three -> primary
    assert 'continues 62% of the time' in c['description']
    assert c['straight_up_rate'] == 0.62
    assert c['ats_rate'] == 0.55
    assert c['total_rate'] == 0.48
    assert c['secondary_rates'] == [
        {'label': 'ATS', 'rate': 0.55, 'sample_size': 12},
        {'label': 'Total', 'rate': 0.48, 'sample_size': 14},
    ]


def test_collision_trends_empty_when_no_stats():
    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', return_value=None):
        results = enrich_game_trends([_game_trends()], 'ncaaf')

    assert results[0]['collisionTrends'] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/services/historical/test_trend_enrichment.py -v`
Expected: FAIL — `KeyError: 'collisionTrends'`

- [ ] **Step 3: Implement the collision integration**

In `api/services/historical/trend_enrichment.py`, add the import and three new helpers, and extend `enrich_game_trends`:

```python
from .trend_context_service import get_streak_context, get_streak_stats
from .trend_collision_service import get_collision_stats


def _collision_rate_label(key: str) -> str:
    return {'straight_up': 'Win', 'ats': 'ATS', 'total': 'Total'}[key]


def _pick_primary_metric(stats: dict):
    """Pick whichever of straight_up/ats/total deviates most from 50% to drive
    the headline sentence and confidence badge; the rest become secondary_rates."""
    candidates = []
    if stats.get('straight_up'):
        candidates.append(('straight_up', stats['straight_up']['home_side_win_rate'], stats['straight_up']['sample_size']))
    if stats.get('ats'):
        candidates.append(('ats', stats['ats']['home_side_cover_rate'], stats['ats']['sample_size']))
    if stats.get('total'):
        candidates.append(('total', stats['total']['over_rate'], stats['total']['sample_size']))
    if not candidates:
        return None
    return max(candidates, key=lambda c: abs(c[1] - 0.5))


def _collision_phrase(team: str, trend: dict) -> str:
    tt, n = trend['type'], trend['count']
    word = {
        'win_streak': f'{n}-game win streak',
        'loss_streak': f'{n}-game skid',
        'cover_streak': f'{n}-game covering streak',
        'no_cover_streak': f'{n}-game run of failing to cover',
        'over_streak': f'{n}-game OVER streak',
        'under_streak': f'{n}-game UNDER streak',
    }.get(tt, f'{tt} of {n}')
    return f"{team}'s {word}"


def _build_collision_entry(home: str, home_trend: dict, away: str, away_trend: dict, stats: dict):
    primary = _pick_primary_metric(stats)
    if primary is None:
        return None
    primary_key, primary_rate, primary_sample = primary

    matchup = f"{_collision_phrase(home, home_trend)} meets {_collision_phrase(away, away_trend)}"
    pct = f"{round(primary_rate * 100)}%"
    sentence = (
        f"Historically when this collision has happened, the home side's "
        f"{_collision_rate_label(primary_key).lower()} continues {pct} of the time "
        f"({primary_sample} instances)"
    )

    secondary_rates = []
    for key in ('straight_up', 'ats', 'total'):
        if key == primary_key or not stats.get(key):
            continue
        rate_field = {'straight_up': 'home_side_win_rate', 'ats': 'home_side_cover_rate', 'total': 'over_rate'}[key]
        secondary_rates.append({
            'label': _collision_rate_label(key),
            'rate': stats[key][rate_field],
            'sample_size': stats[key]['sample_size'],
        })

    return {
        'type': 'win_streak' if primary_rate >= 0.5 else 'loss_streak',
        'count': max(home_trend['count'], away_trend['count']),
        'description': f"{matchup} — {sentence}",
        'continuation_rate': primary_rate,
        'sample_size': primary_sample,
        'home_trend': {'team': home, 'type': home_trend['type'], 'count': home_trend['count']},
        'away_trend': {'team': away, 'type': away_trend['type'], 'count': away_trend['count']},
        'straight_up_rate': stats['straight_up']['home_side_win_rate'] if stats.get('straight_up') else None,
        'ats_rate': stats['ats']['home_side_cover_rate'] if stats.get('ats') else None,
        'total_rate': stats['total']['over_rate'] if stats.get('total') else None,
        'secondary_rates': secondary_rates,
    }


def _collision_criteria(trends: list, venue: str) -> list:
    return [{'trend_type': t['type'], 'min_length': t['count'], 'venue': venue, 'raw': t} for t in trends]
```

Then, inside `enrich_game_trends`, after the existing `for key, focal_team, ... in trend_keys:` loop (which ends at the original line 85 `t['description'] = desc`), add:

```python
        home_criteria = (
            _collision_criteria(game_trends.get('homeTeamTrends') or [], 'general')
            + _collision_criteria(game_trends.get('homeTeamHomeTrends') or [], 'venue_specific')
        )
        away_criteria = (
            _collision_criteria(game_trends.get('awayTeamTrends') or [], 'general')
            + _collision_criteria(game_trends.get('awayTeamAwayTrends') or [], 'venue_specific')
        )

        collision_trends = []
        for hc in home_criteria:
            for ac in away_criteria:
                stats = get_collision_stats(
                    sport,
                    {'trend_type': hc['trend_type'], 'min_length': hc['min_length'], 'venue': hc['venue']},
                    {'trend_type': ac['trend_type'], 'min_length': ac['min_length'], 'venue': ac['venue']},
                )
                if not stats:
                    continue
                entry = _build_collision_entry(home, hc['raw'], away, ac['raw'], stats)
                if entry:
                    collision_trends.append(entry)
        game_trends['collisionTrends'] = collision_trends
```

(`home`/`away` are already in scope — defined near the top of the per-`game_trends` loop body, lines 41-42.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/services/historical/test_trend_enrichment.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full backend test suite**

Run: `pytest tests/ -v`
Expected: PASS (all tests, including Tasks 1-4's new ones)

- [ ] **Step 6: Commit**

```bash
git add api/services/historical/trend_enrichment.py tests/services/historical/test_trend_enrichment.py
git commit -m "feat: attach collisionTrends to enrich_game_trends output"
```

---

### Task 6: Frontend types — `TrendResult.secondary_rates` and `GameWithTrends.collisionTrends`

**Files:**
- Modify: `getstam-react/src/utils/trendAnalysis.ts:6-23`

**Interfaces:**
- Produces: `TrendResult.secondary_rates?: Array<{ label: string; rate: number; sample_size: number }>`; `GameWithTrends.collisionTrends?: TrendResult[]`.

- [ ] **Step 1: Update the interfaces**

In `getstam-react/src/utils/trendAnalysis.ts`, replace lines 6-23:

```typescript
export interface SecondaryRate {
  label: string;
  rate: number;
  sample_size: number;
}

export interface TrendResult {
  type: TrendType;
  count: number;
  description: string;
  continuation_rate?: number;
  sample_size?: number;
  secondary_rates?: SecondaryRate[];
}

export interface GameWithTrends {
  game: any;
  homeTeamTrends: TrendResult[];
  awayTeamTrends: TrendResult[];
  headToHeadTrends: TrendResult[];
  homeTeamHomeTrends?: TrendResult[];
  awayTeamAwayTrends?: TrendResult[];
  homeAtHomeH2HTrends?: TrendResult[];
  collisionTrends?: TrendResult[];
  hasTrends: boolean;
}
```

- [ ] **Step 2: Typecheck**

Run: `cd getstam-react && npx tsc --noEmit`
Expected: no new errors (this is an additive interface change; nothing currently reads these new optional fields yet, so no call site breaks).

- [ ] **Step 3: Commit**

```bash
git add getstam-react/src/utils/trendAnalysis.ts
git commit -m "feat: add collisionTrends and secondary_rates to trend type definitions"
```

---

### Task 7: Flatten `collisionTrends` into `GamesWithTrends.tsx`'s rendered lists

**Files:**
- Modify: `getstam-react/src/components/GamesWithTrends.tsx:106-141,160-167`

**Interfaces:**
- Consumes: `GameWithTrends.collisionTrends` (Task 6).

- [ ] **Step 1: Add `collisionTrends` to the length-filter pass**

In `getstam-react/src/components/GamesWithTrends.tsx`, replace lines 106-117:

```typescript
  const filtered = gamesWithTrends.map((gwt) => {
    const homeTeamTrends = filterByLength(gwt.homeTeamTrends);
    const awayTeamTrends = filterByLength(gwt.awayTeamTrends);
    const headToHeadTrends = filterByLength(gwt.headToHeadTrends);
    const homeTeamHomeTrends = filterByLength(gwt.homeTeamHomeTrends || []);
    const awayTeamAwayTrends = filterByLength(gwt.awayTeamAwayTrends || []);
    const homeAtHomeH2HTrends = filterByLength(gwt.homeAtHomeH2HTrends || []);
    const collisionTrends = filterByLength(gwt.collisionTrends || []);
    const hasTrends =
      homeTeamTrends.length > 0 || awayTeamTrends.length > 0 || headToHeadTrends.length > 0 ||
      homeTeamHomeTrends.length > 0 || awayTeamAwayTrends.length > 0 || homeAtHomeH2HTrends.length > 0 ||
      collisionTrends.length > 0;
    return { ...gwt, homeTeamTrends, awayTeamTrends, headToHeadTrends, homeTeamHomeTrends, awayTeamAwayTrends, homeAtHomeH2HTrends, collisionTrends, hasTrends };
  }).filter((gwt) => gwt.hasTrends);
```

- [ ] **Step 2: Add `collisionTrends` to both trend-collecting arrays**

Replace lines 134-141:

```typescript
  const getTopTrends = (gwt: GameWithTrends) => [
    ...(gwt.headToHeadTrends || []),
    ...(gwt.homeAtHomeH2HTrends || []),
    ...(gwt.collisionTrends || []),
    ...(gwt.homeTeamHomeTrends || []),
    ...(gwt.awayTeamAwayTrends || []),
    ...(gwt.homeTeamTrends || []),
    ...(gwt.awayTeamTrends || []),
  ].sort((a, b) => b.count - a.count);
```

Replace lines 160-167:

```typescript
          const allTrends = [
            ...(gwt.headToHeadTrends || []),
            ...(gwt.homeAtHomeH2HTrends || []),
            ...(gwt.collisionTrends || []),
            ...(gwt.homeTeamHomeTrends || []),
            ...(gwt.awayTeamAwayTrends || []),
            ...(gwt.homeTeamTrends || []),
            ...(gwt.awayTeamTrends || []),
          ].sort((a, b) => getConfidenceScore(b) - getConfidenceScore(a) || b.count - a.count);
```

(`collisionTrends` is placed right after the two H2H categories — it's the next-most-specific signal, ahead of the single-team venue/general trends.)

- [ ] **Step 3: Typecheck**

Run: `cd getstam-react && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add getstam-react/src/components/GamesWithTrends.tsx
git commit -m "feat: include collisionTrends in GamesWithTrends flattened lists"
```

---

### Task 8: Render `secondary_rates` in `TrendInsightCard.tsx`

**Files:**
- Modify: `getstam-react/src/components/TrendInsightCard.tsx:223-232`

**Interfaces:**
- Consumes: `TrendResult.secondary_rates` (Task 6).

- [ ] **Step 1: Add the secondary-rates line**

In `getstam-react/src/components/TrendInsightCard.tsx`, replace lines 223-232:

```tsx
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography sx={{ fontWeight: 800, fontSize: "0.88rem", color: trendColor, lineHeight: 1.3 }}>
                  {title}
                </Typography>
                {context && (
                  <Typography sx={{ fontSize: "0.75rem", color: "#64748b", mt: 0.3, lineHeight: 1.4 }}>
                    {context}
                  </Typography>
                )}
                {trend.secondary_rates && trend.secondary_rates.length > 0 && (
                  <Typography sx={{ fontSize: "0.72rem", color: "#94a3b8", mt: 0.2, lineHeight: 1.4 }}>
                    {trend.secondary_rates
                      .map((r) => `${r.label}: ${Math.round(r.rate * 100)}% (${r.sample_size})`)
                      .join(" • ")}
                  </Typography>
                )}
              </Box>
```

- [ ] **Step 2: Typecheck**

Run: `cd getstam-react && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add getstam-react/src/components/TrendInsightCard.tsx
git commit -m "feat: render secondary collision rates (ATS/total) on trend cards"
```

---

### Task 9: Manual verification in the running app

**Files:** none (verification only)

- [ ] **Step 1: Start the backend in development mode**

Run: `FLASK_ENV=development python app.py` (from repo root, venv activated)

- [ ] **Step 2: Start the frontend**

Run: `cd getstam-react && npm start`

- [ ] **Step 3: Exercise the NFL or NCAAF trends endpoint directly with `enrich: true`**

Find two real teams in the DB where one currently has an active losing-ish and the other a winning-ish streak (or construct a synthetic payload), then:

```bash
curl -s -X POST http://127.0.0.1:5000/api/historical/trends/nfl \
  -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d '{"games": [{"home_team_name": "<Home Team>", "away_team_name": "<Away Team>", "game_id": "manual-check-1"}], "enrich": true, "minTrendLength": 3}' | python -m json.tool
```

Confirm the response includes a `collisionTrends` key on the game (possibly empty if no qualifying collision exists for that pairing — try a few team pairs if the first is empty) and, where present, that `description`, `continuation_rate`, `sample_size`, and `secondary_rates` look sane (percentages between 0-100, sample sizes are small positive integers, description names both teams).

- [ ] **Step 4: Confirm in the browser**

Navigate to an NFL or NCAAF games page in the running React app, find a game whose card shows a new collision insight, and visually confirm: the card renders without layout breakage, the collision insight reads naturally, and the secondary-rates line (if present) displays correctly. Also confirm a game with NO qualifying collision still renders its existing trends unaffected.

- [ ] **Step 5: Report results**

No commit for this task — it's verification only. If anything looks wrong, go back and fix the relevant task (with its own commit) rather than patching ad hoc.
