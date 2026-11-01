# NBA: Backfill Historical `total` Precision (2020-07 to present)

## Context

`nba_games_1.total` was `Integer` until today's migration widened it to `Float`
(`migrations/versions/445848ace83f_widen_nba_games_1_total_to_float.py`). That
fix only applies going forward — every existing row still holds whatever
value was rounded away at insert time, by both the old SDQL job and (until
today) the new Odds-API job. Confirmed live: 509 of 15,037 rows (3.38%) have
`home_points + away_points == total` exactly, which almost certainly means
they're misclassified as a trend "push" today, since a real half-point total
can never push by design.

Odds API's historical coverage for NBA only goes back to **~2020-07-01**
(confirmed live — no data at all for 2015 or 2018 snapshots, real games
starting to appear by July 2020). `nba_games_1` has rows back to 2015-01-02.
So this backfill can only ever reach the back half of the table's history;
2015 through mid-2020 stays as-is permanently (the only alternative is
re-querying paid SDQL, which defeats the point of migrating off it).

**Scope, per decisions already made**: correct all 7,991 rows from
2020-07-01 onward (not just the 204 of those confirmed wrong by the
exact-match check) — other rows in range likely also hold an imprecise
value that happened not to flip the over/under classification, worth fixing
while already re-fetching. Update `total` in place (no temporary column) —
the existing integer value is a known-rounded approximation, not worth
preserving separately.

## Research findings (live-verified 2026-10-31)

- **Odds API historical coverage boundary**: confirmed no NBA data before
  ~2020-07-01; confirmed real games with odds present by that date.
- **Critical methodology finding — snapshot timing matters enormously**: a
  single blanket snapshot per calendar day does NOT work. Tested on
  2021-12-15/16: fetching one snapshot at a fixed time for the whole day
  returned reasonable-looking numbers for games whose kickoff happened to be
  near that snapshot time, but wildly wrong numbers for games that had
  already tipped off hours earlier (e.g., Pacers @ Bucks, kickoff
  01:10 UTC — a snapshot at 00:10 UTC, ~1hr before tip, shows DraftKings
  total 214.5, matching our stored 215 almost exactly; a snapshot at
  02:55 UTC, ~1h45m **after** tip, shows DraftKings total 224.5 — a fully
  drifted in-game/live number, not the pregame closing line). **The backfill
  must snapshot per-game, close to that specific game's own commence_time**,
  exactly like the live seed jobs already do (`build_odds_lookup` in
  `jobs/mlb_seed_yesterdays_games_odds_api.py`, `get_historical_odds_for_date`
  in the NHL/NFL/NBA jobs) — never a single per-day snapshot.
- **Team-name matching confirmed clean** on real historical data (11 games on
  2021-12-15, including a Clippers game) using `convert_team_name` — the
  Clippers fix from the main migration (`'LA Clippers': 'Clippers'`) also
  benefits this backfill, since Odds API's team names for older seasons use
  the same `"Los Angeles Clippers"` / ESPN-style naming conventions.
- **No `odds_event_id` on most rows in range**: only rows inserted by the new
  job (go-forward from today) have it populated; the ~7,991 rows in this
  backfill's range are virtually all pre-migration, with `odds_event_id`
  NULL. Matching must be done by `(game_date, home_team_name, away_team_name)`
  via `convert_team_name`, not by event id.
- **No stored commence_time for historical rows**: `nba_games_1.start_time`
  exists but isn't reliably populated for SDQL-era rows (confirmed via the
  main migration's finding that even the new job doesn't populate it).
  Commence times must come from Odds API itself, not our own table.
- **Estimated API cost**: 1,315 unique `game_date`s in range. Discovering
  each day's schedule (event ids + commence_times) via the historical
  `events` endpoint is 1 call/day. Fetching each game's pregame odds snapshot
  is up to 1 call per unique commence_time (shared across games with
  identical start times, same batching as the live jobs) — worst case ~7,991
  additional calls if no two games ever share an exact start time. Total
  estimate: roughly 1,315 + up to 7,991 ≈ **under 10,000 API calls**, a small
  fraction of the account's multi-million-request budget (confirmed healthy
  during the NHL migration's own research).

## Decisions made during design review

- **Scope**: all 7,991 rows, `game_date >= 2020-07-01`, not just the 204
  confirmed-wrong ones.
- **In-place update**: `UPDATE nba_games_1 SET total = :new_total WHERE
  game_id = :id` directly, no temporary column.
- **Lenient update policy**: only update a row when a real total value was
  found and matched; never null out or touch a row's existing `total` if no
  match is found (coverage gap, unmatched team name, bookmaker never posted
  a totals market for that game).
- **Per-game snapshot timing** (see Research findings): snapshot ~1 hour
  before each unique commence_time, batched by shared commence_time within
  a day, mirroring the live jobs' established convention exactly.
- **One-off script, not a Heroku Scheduler job**: this runs once (manually,
  from a local machine or `heroku run`), not on a recurring schedule. No
  Scheduler entry needed.
- **Resumable/idempotent**: commit per `game_date` processed, so an
  interrupted run can be restarted; re-running is safe (re-applies the same
  update to already-correct rows, a no-op in effect).
- **Bookmaker selection**: same convention as the live job — prefer
  DraftKings per market, fall back to the first bookmaker in response order
  that has a `totals` market.

## Components

- New one-off script `jobs/backfill_nba_totals.py`:
  1. Query `nba_games_1` for all distinct `game_date` values `>= '2020-07-01'`,
     ordered chronologically.
  2. For each `game_date`: fetch that day's schedule via the historical
     `events` endpoint at a fixed daily anchor snapshot (e.g., `18:00:00Z`,
     safely before any NBA games start) to get each event's `id`,
     `commence_time`, `home_team`, `away_team` — no `markets` param needed,
     cheaper than a full odds call.
  3. Group events by unique `commence_time`; for each group, fetch one
     historical `odds` list snapshot at `commence_time - 1 hour`
     (`markets=totals`), matching the live jobs' timing convention exactly.
  4. For each event, parse the `totals` market via the same
     DraftKings-preferred-with-fallback logic already proven in the live
     seed job; match to our DB row via
     `shared_utils.convert_team_name(home_team)`/`convert_team_name(away_team)`
     against `nba_games_1 WHERE game_date = :d AND home_team_name = :h AND
     away_team_name = :a`.
  5. If a row is found and a total was parsed: `UPDATE ... SET total =
     :new_total`. If no row matches, or no total was found: skip, log, move
     on — never touch an existing value speculatively.
  6. Commit after each `game_date`'s updates; print running progress
     (`processed`, `updated`, `skipped — no DB match`, `skipped — no odds
     found`).
  7. At the end: re-run the exact-match diagnostic query
     (`home_points + away_points = total`) and print the before/after count,
     so the result is immediately verifiable against the 204 baseline.

## Explicitly out of scope

- Rows before 2020-07-01 (SDQL-only history, unrecoverable via Odds API).
- Any other column besides `total`.
- Making this a recurring/scheduled job — it runs once.
- Re-deriving `start_time` for historical rows (separate, already-known gap).
