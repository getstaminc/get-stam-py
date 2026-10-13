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
- **Home/away framing**: both kinds of trend already exist in this codebase
  and both must be collision-able:
  - *Venue-specific* trends (today's `homeTeamHomeTrends` /
    `awayTeamAwayTrends` — e.g. "Huskers won their last 5 **home** games,"
    "Oklahoma lost their last 5 **road** games") are inherently pinned to a
    role — the metric doesn't exist for a team except in that role. For
    these, the historical search is naturally home/away-framed: it can only
    ever be matched by whichever team is actually playing that role in a
    given historical game.
  - *General* trends (today's `homeTeamTrends` / `awayTeamTrends` — e.g.
    "Tennessee won their last 7 games," "Texas lost their last 5 games,"
    with no venue qualifier) carry no venue identity. For these, the
    historical search must NOT impose today's home/away arrangement —
    either team in a historical game may satisfy either side of the
    query, and the match is accepted in whichever arrangement works. See
    §4.3 for the matching algorithm.
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

### 4.1 Entering streaks — general and venue-specific

Extend `_load_sport_context(sport)` to additionally compute, per team per
game, the streak **entering** that game for each trend type — i.e. the same
`calc_streak()` logic, but walked forward chronologically so each game gets
the streak value as of just before it was played (not the final, most-recent
streak). This is computed in two flavors per team, mirroring the existing
trend categories:

- **General** — walked over *all* of the team's games, any venue (feeds
  `homeTeamTrends`/`awayTeamTrends`-style collisions).
- **Venue-specific** — walked over only the team's home games, and
  separately only its away games (feeds `homeTeamHomeTrends`/
  `awayTeamAwayTrends`-style collisions). A team's home-venue sequence only
  has entries for games it played at home; its away-venue sequence only for
  games it played away.

```python
entering_streaks: dict[str, dict[game_id, dict[str, int]]]          # general
entering_streaks_home_venue: dict[str, dict[game_id, dict[str, int]]]  # home games only
entering_streaks_away_venue: dict[str, dict[game_id, dict[str, int]]]  # away games only
# entering_streaks["Dodgers"][game_id] = {
#   "win_streak": 3, "loss_streak": 0,
#   "cover_streak": 1, "no_cover_streak": 0,
#   "over_streak": 0, "under_streak": 2,
# }
```

This reuses the per-team chronological game lists already built for
`team_games` in `_load_sport_context` (filtered by venue for the two
venue-specific passes) — no new DB query.

### 4.2 Collision index

From the same pass, build one record per historical game. Each side carries
both its general and (role-appropriate) venue-specific entering streaks,
since a historical game's home team only ever needs its home-venue sequence
and the away team only its away-venue sequence:

```python
collision_index[sport]: list[dict]
# {
#   "game_id": ...,
#   "home": {
#     "name": ...,
#     "general": {...},        # from entering_streaks
#     "home_venue": {...},     # from entering_streaks_home_venue
#   },
#   "away": {
#     "name": ...,
#     "general": {...},
#     "away_venue": {...},     # from entering_streaks_away_venue
#   },
#   "outcome": {
#     "winner": "home" | "away",
#     "ats_result": "home" | "away" | "push",
#     "total_result": "over" | "under" | "push",
#   },
# }
```

Built once per sport, alongside the existing cache (same invalidation —
whatever currently clears `_context_cache` clears this too; no new
invalidation path needed).

### 4.3 Query function

Each side of a query is a criterion: `{trend_type, min_length, venue}` where
`venue` is `"general"` or `"venue_specific"` — set directly by which trend
category the input came from (`homeTeamTrends` → general,
`homeTeamHomeTrends` → venue_specific, etc; same for away).

```python
def get_collision_stats(
    sport: str,
    home_criterion: dict,  # {trend_type, min_length, venue}
    away_criterion: dict,
) -> dict:
    """
    Scans collision_index[sport] for historical games matching both
    criteria (>= per §2). Returns:
    {
      "sample_size": int,
      "straight_up": {"home_side_win_rate": float},
      "ats": {"home_side_cover_rate": float},
      "total": {"over_rate": float},
    }
    """
```

Matching rule, per historical game in the index:

- If `home_criterion.venue == "venue_specific"`, it can only be checked
  against that game's `home.home_venue` streak — venue-specific trends are
  pinned to the role they're defined for. Likewise `away_criterion` against
  `away.away_venue` when venue-specific.
- If a criterion is `"general"`, it's checked against the matching role's
  `general` streak first (`home.general` for the home criterion, `away.general`
  for the away criterion). If **both** criteria are `"general"`, a game also
  counts as a match with the roles swapped (home team satisfying the away
  criterion and vice versa) — general trends carry no venue identity, so
  today's home/away arrangement shouldn't constrain which physical team
  satisfies which side of the query. When a venue-specific criterion is
  present on either side, no swapping happens — that side's role is already
  pinned, so the other side (general or not) is evaluated against the
  remaining role only.
- `"home_side"` / `"away_side"` in the output always refer to *which
  criterion* a team satisfied (the home-query-side vs the away-query-side),
  not necessarily which physical role it played in that historical game —
  this only diverges from literal home/away when a swapped general-vs-general
  match occurred.

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
for each game, take the cross-product of the home-side trend categories
(`homeTeamTrends` ∪ `homeTeamHomeTrends`) × the away-side trend categories
(`awayTeamTrends` ∪ `awayTeamAwayTrends`) — already computed by the sport's
trends service, typically 0–3 trends per side — tag each with
`venue: "general"` or `"venue_specific"` by which category it came from,
call `get_collision_stats()` for each pairing, and attach any matches
(`sample_size > 0`) as a new category on the per-game result:

```python
results[i]["collisionTrends"] = [
  {
    "home_trend": {"team": "Huskers", "type": "win_streak", "count": 5, "venue": "venue_specific"},
    "away_trend": {"team": "Sooners", "type": "loss_streak", "count": 5, "venue": "venue_specific"},
    "description": "...",
    "straight_up_rate": 0.62,
    "ats_rate": 0.55,
    "total_rate": 0.48,
    "sample_size": 14,
  },
  {
    "home_trend": {"team": "Volunteers", "type": "win_streak", "count": 7, "venue": "general"},
    "away_trend": {"team": "Longhorns", "type": "loss_streak", "count": 5, "venue": "general"},
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

- Unit tests for `entering_streaks`/`entering_streaks_home_venue`/
  `entering_streaks_away_venue` computation against a small fixture game
  list (verify forward-walked streak values match hand-computed
  expectations, including streak resets and venue filtering).
- Unit tests for `get_collision_stats()`: fixture `collision_index` with
  known games, covering all three cases — both criteria venue-specific (no
  swapping), both general (swapped arrangement also matches), and mixed
  (venue-specific side pinned, general side evaluated against the
  remaining role only) — plus `>=` matching and rate computation.
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
