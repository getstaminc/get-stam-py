# NBA: Switch Games from SDQL to Odds API + ESPN

## Context

NBA games currently come from SDQL (`jobs/nba_seed_yesterdays_games.py`), a paid
third-party sports database, via a hardcoded username/token embedded directly
in the job file. This is the second of four remaining SDQL-dependent sports
(NFL done, NBA here, NCAAF/NCAAB still to come) being migrated off SDQL toward
Odds API + ESPN. The NFL migration
(`docs/superpowers/specs/2026-10-30-nfl-odds-api-migration-design.md`) is the
structural template; `jobs/nfl_odds_api_seed_yesterdays_games.py` is the
reference implementation.

Unlike NFL, `nba_games_1` (the live table — `nba_games` is dead legacy code,
confirmed unused) has no `odds_event_id` column today, so this migration
includes a new migration adding one, matching NFL/NHL/MLB's convention
exactly (a nullable `String(100)` column with a unique constraint) rather than
reusing the existing game_date+team-id dedup check. Chosen deliberately over
the lower-effort option (skip the migration, keep the old dedup check) for
consistency with the rest of the codebase: a stable external event id is a
cleaner idempotency key, and it sets up a future cleanup opportunity for the
data integrity report's NBA prop-check, which currently uses a `team_id_join`
workaround specifically because this column doesn't exist yet.

NBA already has `nba_player_props`, already sourced from Odds API/ESPN — this
migration only touches the games table, not player props. No SDQL dead-code
cleanup is needed this time (the shared SDQL helper cluster — `sdql_queries.py`,
`historical_odds.py`, `single_game_data.py`, `utils.py` — was already deleted
during the NFL migration).

## Research findings (live-verified 2026-10-31)

- **Odds API scores** (`/v4/sports/basketball_nba/scores`, live;
  `/v4/historical/sports/basketball_nba/odds` for past-dated odds) returns
  final home/away score only — no quarter breakdown, no playoffs flag. Same
  gap pattern as NFL/NHL.
- **Odds API historical odds**, fetched via the list endpoint at a snapshot
  shortly before the game's `commence_time` (not the single-event-by-id
  endpoint, which 404s outside a narrow window) — confirmed live to return
  all three needed markets: `h2h` (moneyline), `spreads` (point spread +
  price), `totals` (over/under point + price). Confirmed against a real
  event (Pistons vs. Hornets, 2026-10-28) across multiple bookmakers
  (DraftKings, lowvig).
- **ESPN NBA** (`site.api.espn.com/apis/site/v2/sports/basketball/nba/...`,
  free, same host NBA player-prop actuals already use) confirmed live:
  - `scoreboard?dates=YYYYMMDD` → each event's `competitions[0].neutralSite`
    and `status.type.name`.
  - `summary?event=<id>&enable=boxscore` → `header.competitions[0].competitors[].linescores`
    (one entry per quarter), `header.season.type` (3 = postseason, same
    convention as NFL/NHL), `status.type.detail` (e.g. `"Final/OT"`).
  - **Overtime period confirmed live**: a real OT game (Jazz vs. Spurs,
    2026-10-28, event 401909890, detail `"Final/OT"`) has a 5th `linescores`
    entry per competitor (`6` / `12`) — confirms the existing SDQL job's
    `quarter_scores[4] if len > 4 else None` logic carries over directly.
- **No neutral-site concept needed**: the current SDQL job's query is
  hardcoded `site='home'` — this table has never stored a `'neutral'` value
  for NBA (unlike NFL, which has real neutral-site games). `game_site` will
  be hardcoded `'home'` going forward, same precedent as NHL's migration.
- **Field-by-field gap check**: every column the current SDQL job writes has
  a confirmed Odds API or ESPN equivalent — no field-level gap for NBA.

| `nba_games_1` column | Old (SDQL) source | New source |
|---|---|---|
| `home_points`/`away_points` | SDQL | Odds API `scores` |
| `home_line`/`away_line` | SDQL | Odds API `spreads` market |
| `total` | SDQL | Odds API `totals` market `point` |
| `home_money_line`/`away_money_line` | SDQL | Odds API `h2h` market |
| `home/away_quarter_scores` | SDQL | ESPN `linescores` |
| `home/away_first/second_half_points` | computed from quarter scores | same computation (ESPN-sourced) |
| `home/away_overtime_points` | SDQL 5th quarter value | ESPN 5th `linescores` entry (live-confirmed above) |
| `playoffs` | SDQL | ESPN `season.type == 3` |
| `game_site` | always `'home'` in practice (SDQL query hardcodes it) | hardcoded `'home'` (no behavior change) |
| `total_points`, `total_margin` | computed from points | same computation |
| `odds_event_id` | column doesn't exist today | Odds API event `id` (new column, this migration) |

## Decisions made during design review

- **Go-forward only** — matches NFL/NHL. Switch the daily job; existing
  SDQL-sourced historical rows in `nba_games_1` stay untouched, no backfill.
- **New migration**: add `nba_games_1.odds_event_id` (nullable `String(100)`
  + unique constraint), mirroring NFL's `a7c2e9f4b1d3` exactly. Deliberately
  chosen over skipping it (see Context) — current alembic head is
  `9d14f3a7c2e8`.
- **No dead-code cleanup this time** — already done in the NFL migration.
- **`game_site` hardcoded `'home'`** — no neutral-site concept in this data
  historically; matches NHL's precedent.
- **Lenient insert policy** (same as NFL): always insert a game once the
  final score is known; leave odds-derived columns NULL if a market is
  unavailable, never skip the whole game over missing pricing.
- **Lenient ESPN-matching policy** (same as NFL): if an Odds-API-sourced
  game can't be matched to an ESPN event for that date, insert what Odds
  API gave us with `home/away_quarter_scores`/`playoffs` left NULL rather
  than dropping the game.

## Components

### Games pipeline

- New job `jobs/nba_odds_api_seed_yesterdays_games.py`, replacing
  `jobs/nba_seed_yesterdays_games.py` (deleted as part of this work — also
  removes its embedded plaintext SDQL credential from the working tree).
- Flow: identical structure to `jobs/nfl_odds_api_seed_yesterdays_games.py`:
  1. Odds API live `scores` (last 3 days, filtered to Eastern-date match) for
     the final score.
  2. Odds API historical `odds` list for the date, matched by `event["id"]`,
     for moneyline/spread/total (DraftKings preferred, fallback to first
     bookmaker in response order that carries each market independently).
  3. ESPN `scoreboard`+`summary` for quarter scores, playoffs, OT detail.
  4. Idempotent insert via `SELECT 1 FROM nba_games_1 WHERE odds_event_id = :id OR (game_date = :d AND home_team_id = :h AND away_team_id = :a)`.
- Team lookup via `convert_team_name` against `teams WHERE sport = 'NBA'`,
  same as every other sport's job.

## Explicitly out of scope

- NCAAF, NCAAB migrations — separate future work.
- Any UI change — this only touches the ingestion job and `nba_games_1` rows.
- Full historical backfill/replace of existing `nba_games_1` rows.
- Rotating/revoking the SDQL credential.
