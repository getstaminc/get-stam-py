# Trend Collision Feature — Design

Date: 2026-10-12
Status: Approved (pre-implementation)

## 1. Problem

The app already surfaces single-team trends ("Lakers have won 5 straight") and,
for MLB/NFL/NCAAF/soccer, enriches them with a historical continuation rate
("...and historically that streak continues 57% of the time"). That logic
lives in `api/services/historical/trend_context_service.py` +
`trend_enrichment.py`.

What's missing: when *two* active trends collide in the same game (e.g. the
home team enters on a 5-game losing streak while the away team enters on a
7-game winning streak), there's no way to see how that specific collision has
played out historically across the league. This feature adds that.

## 2. Requirements (confirmed with user)

- **Trend types in scope**: all six existing types — `win_streak`,
  `loss_streak`, `cover_streak`, `no_cover_streak`, `over_streak`,
  `under_streak`. Any type may be paired with any other type (not just
  win-vs-loss).
- **Match scope**: league-wide, not matchup-specific. A query like "5+ game
  losing streak vs 7+ game winning streak" counts *any* two opposing teams in
  that sport's history with that profile, not just the same two teams as
  today's game.
- **Match threshold**: "at least" (`>=`), not exact. A historical 8-game skid
  matches a query for "5+ game losing streak."
- **Outcome metric**: report all three angles — straight-up winner, ATS
  cover, and over/under result — each as a rate + sample size, same shape as
  the existing `continuation_rate`/`sample_size` pair.
- **Home/away framing**: outcomes are reported from the perspective of
  "team carrying trend A" vs "team carrying trend B," not home/away. A trend
  pairing doesn't care which side is home.
- **Surface**: automatically on game cards, alongside existing trend pills —
  not a separate explorer tool.
- **Sport scope for v1**: MLB, NFL, NCAAF, soccer (the sports where
  `enrich_game_trends` already runs and real spread columns are configured
  in `SPORT_CONFIG`). NBA/NHL/NCAAB are explicitly out of scope — they don't
  currently call the enrichment step at all, and NBA's spread column is
  already flagged as ambiguous (duplicate of moneyline) in
  `trend_context_service.py`. Wiring those up is a separate, pre-existing
  gap this feature does not need to fix.
- **Schema changes**: none. See §5.

## 3. Current architecture (for reference)

- `BaseHistoricalService` (`api/services/historical/base_service.py`) — DB
  connection boilerplate + description-rewriting helpers
  (`_apply_h2h_context`, `_apply_venue_context`). No streak/percentage math.
- `<sport>_trends_service.py` (e.g. `nba_trends_service.py`) —
  `analyze_multiple_games_trends()` computes each team's *current* streak
  per trend type via `calc_streak()` (counts consecutive `True`s from the
  most recent game backward). Emits `homeTeamTrends`, `awayTeamTrends`,
  `headToHeadTrends`, etc. per game.
- `trend_context_service.py` — the continuation-rate engine.
  `_load_sport_context(sport)` loads **all** completed games for a sport
  once into a module-level cache (`_context_cache`), bucketing by
  `(home_team_name, away_team_name)` and by team. `_continuation_stats*()`
  walks each sequence and, every time a streak hits exactly N, checks
  whether the next game continued it. `get_streak_stats()` /
  `get_streak_context()` expose this as rate + sample size + sentence.
- `trend_enrichment.py::enrich_game_trends(results, sport)` — glues the two
  together: for each game's trend categories, calls into
  `trend_context_service` and attaches `continuation_rate`/`sample_size`
  onto each trend dict in place. Called from the MLB/NFL/NCAAF/soccer trend
  routes only.
- Frontend: `GameWithTrends` (TS interface, `trendAnalysis.ts`) mirrors the
  backend's per-game trend categories. `GamesWithTrends.tsx` flattens all
  categories into one list per game and renders via `TrendInsightCard.tsx`,
  which parses the rate back out of `description` for the headline and uses
  `continuation_rate`/`sample_size` for a confidence badge.

## 4. New computation: entering-streak index + collision lookup

### 4.1 Entering streaks

Extend `_load_sport_context(sport)` to additionally compute, per team per
game, the streak **entering** that game for each trend type — i.e. the same
`calc_streak()` logic, but walked forward chronologically so each game gets
the streak value as of just before it was played (not the final, most-recent
streak). Store as:

```python
entering_streaks: dict[str, dict[game_id, dict[str, int]]]
# entering_streaks["Dodgers"][game_id] = {
#   "win_streak": 3, "loss_streak": 0,
#   "cover_streak": 1, "no_cover_streak": 0,
#   "over_streak": 0, "under_streak": 2,
# }
```

This reuses the per-team chronological game lists already built for
`team_games` in `_load_sport_context` — no new DB query.

### 4.2 Collision index

From the same pass, build one record per historical game:

```python
collision_index[sport]: list[dict]
# {
#   "game_id": ...,
#   "team_a": {"name": ..., "entering_streaks": {...}},  # home
#   "team_b": {"name": ..., "entering_streaks": {...}},  # away
#   "outcome": {
#     "winner": "team_a" | "team_b",
#     "ats_result": "team_a" | "team_b" | "push",
#     "total_result": "over" | "under" | "push",
#   },
# }
```

Built once per sport, alongside the existing cache (same invalidation —
whatever currently clears `_context_cache` clears this too; no new
invalidation path needed).

### 4.3 Query function

```python
def get_collision_stats(
    sport: str,
    trend_type_a: str, min_length_a: int,
    trend_type_b: str, min_length_b: int,
) -> dict:
    """
    Scans collision_index[sport] for every historical game where one team's
    entering streak for trend_type_a was >= min_length_a and the OPPONENT's
    entering streak for trend_type_b was >= min_length_b, in either
    home/away arrangement. Returns:
    {
      "sample_size": int,
      "straight_up": {"trend_a_team_win_rate": float},
      "ats": {"trend_a_team_cover_rate": float},
      "total": {"over_rate": float},
    }
    """
```

Matching is `>=` per §2. Because team_a/team_b in the index are fixed to
home/away but the query is home/away-agnostic, the function checks both
orderings (home carries trend A / away carries trend B, and vice versa) and
pools results, flipping outcome framing accordingly so stats always read as
"trend-A-team" vs "trend-B-team."

## 5. Why no schema changes

The user asked whether new DB fields would make this easier to query. The
answer is no, for this v1: the feature is surfaced automatically on game
cards, and the existing continuation-rate feature already pays the cost of
loading each sport's full game history into memory once per cache window
(`_context_cache`) rather than per request. This feature rides the same
cache — `entering_streaks` and `collision_index` are built in the same pass,
so there's no additional per-request DB cost to optimize away.

Denormalized streak columns (or a separate derived table) would only earn
their cost if something needed to query this data via raw SQL outside the
Python engine (e.g. BI/reporting), or if a sport's history grew large enough
that even an hourly full-table load became slow. Neither is true today.
Revisit if either changes.

## 6. API / enrichment integration

No new route. Extend `trend_enrichment.py::enrich_game_trends(results, sport)`:
for each game, take the cross-product of `homeTeamTrends` × `awayTeamTrends`
(already computed by the sport's trends service, typically 0–3 trends per
side), call `get_collision_stats()` for each pairing, and attach any matches
(`sample_size > 0`) as a new category on the per-game result:

```python
results[i]["collisionTrends"] = [
  {
    "trend_a": {"team": "Dodgers", "type": "loss_streak", "count": 5},
    "trend_b": {"team": "Padres", "type": "win_streak", "count": 7},
    "description": "...",
    "straight_up_rate": 0.38,
    "ats_rate": 0.44,
    "total_rate": 0.52,
    "sample_size": 21,
  },
  ...
]
```

Only MLB/NFL/NCAAF/soccer routes call `enrich_game_trends`, so this ships
automatically scoped to those sports with no route-level changes.

## 7. Frontend

- `getstam-react/src/utils/trendAnalysis.ts`: add `collisionTrends?:
  CollisionTrend[]` to the `GameWithTrends` interface, with a new
  `CollisionTrend` type matching the shape in §6.
- `getstam-react/src/components/GamesWithTrends.tsx`: add
  `collisionTrends` to the flattened list that feeds `TrendInsightCard`
  (alongside `headToHeadTrends`, `homeTeamHomeTrends`, etc.).
- `getstam-react/src/components/TrendInsightCard.tsx`: needs a variant that
  renders three rates (straight-up / ATS / total) instead of the single
  `continuation_rate` it handles today, plus a description that names both
  teams and both trends (e.g. "Dodgers' 5-game skid meets Padres' 7-game
  streak"). Confidence badge logic can reuse the existing
  deviation-from-50% approach, applied to whichever of the three rates is
  most extreme.

## 8. Testing

- Unit tests for `entering_streaks` computation against a small fixture game
  list (verify forward-walked streak values match hand-computed expectations,
  including streak resets).
- Unit tests for `get_collision_stats()`: fixture `collision_index` with
  known games, assert `>=` matching behavior, both home/away orderings pool
  correctly, and rates compute correctly.
- Integration test on one real sport (MLB) trends route with `enrich=true`,
  asserting `collisionTrends` appears on at least one fixture game with a
  known collision.
- No frontend test changes beyond existing snapshot/type coverage; manual
  check in browser that a real game card renders a collision card correctly
  (and that cards with no collision render unchanged).

## 9. Out of scope / explicitly deferred

- NBA/NHL/NCAAB enrichment wiring (pre-existing gap, separate work).
- Any new DB schema/columns (see §5).
- A standalone "what-if" explorer UI for arbitrary trend-pair queries (user
  chose auto-surfaced-on-game-cards only for v1; `get_collision_stats()` is
  written generically enough to support an explorer later without rework).
