# NFL: Switch Games from SDQL to Odds API + ESPN

## Context

NFL games currently come from SDQL (`jobs/nfl_seed_yesterdays_games.py`), a paid
third-party sports database, via a hardcoded username/token embedded directly
in the job file. This is the first of four remaining SDQL-dependent sports
(NFL, NBA, NCAAF, NCAAB) being migrated off SDQL toward Odds API + ESPN, the
two sources the rest of the app already standardizes on. NHL went through
this exact migration already (`docs/superpowers/specs/2026-10-20-nhl-odds-api-switch-design.md`)
and is the structural template here; `jobs/mlb_seed_yesterdays_games_odds_api.py`
(already live) is the template for the idempotent-insert convention.

Unlike NHL, NFL already has most of the surrounding infrastructure in place:
- `nfl_games.odds_event_id` already exists with a unique constraint
  (`uq_nfl_games_odds_event_id`, migration `a7c2e9f4b1d3`, added 2026-08-10
  explicitly "laying the groundwork" for this switch) — but it's never been
  populated, since no seed job writes to it yet. This is also the exact bug
  the new data-integrity-report job surfaced: NFL's prop-completeness check
  was a no-op because this column was always NULL.
- `nfl_player_props` already exists and is already sourced from Odds API/ESPN
  — this migration only touches the games table, not player props.
- No new migration or ORM model is needed. `nfl_games` stays raw-SQL-only,
  consistent with the rest of this codebase's query conventions.

## Research findings (live-verified 2026-10-30)

- **Odds API scores** (`/v4/sports/americanfootball_nfl/scores`, live;
  `/v4/historical/sports/americanfootball_nfl/scores` for past dates) returns
  final home/away score only — no quarter breakdown, no neutral-site flag,
  no playoffs flag. Same gap pattern as NHL.
- **Odds API historical odds** (`/v4/historical/sports/americanfootball_nfl/events/<id>/odds`)
  confirmed live to return all three markets needed: `h2h` (moneyline),
  `spreads` (point spread + price), `totals` (over/under point + price).
  Confirmed against a real event (Bears @ Patriots, 2026-10-23) across
  multiple bookmakers (DraftKings, Caesars).
- **ESPN NFL** (`site.api.espn.com/apis/site/v2/sports/football/nfl/...`,
  free, same host already used for NFL player-prop actuals) confirmed live:
  - `scoreboard?dates=YYYYMMDD` → each event's `competitions[0].neutralSite`
    (boolean, confirmed `false` on a normal game) and `status.type.name`
    (`STATUS_FINAL`).
  - `summary?event=<id>&enable=boxscore` → `header.competitions[0].competitors[].linescores`
    (one entry per quarter, `{"displayValue": "N"}`), `header.season.type`
    (1=preseason, 2=regular, 3=postseason — same convention as NHL),
    `header.competitions[0].status.type.detail` (e.g. `"Final/OT"`).
  - **Overtime period confirmed live**: a real OT game (Buccaneers @ Steelers,
    2026-10-18, event 401873002, detail `"Final/OT"`) has a 5th `linescores`
    entry per competitor (`0` / `7`) — confirms the existing SDQL job's
    `quarter_scores[4] if len > 4 else None` logic carries over directly onto
    ESPN's `linescores` with no loss of fidelity.
- **Field-by-field gap check**: every column the current SDQL job writes has
  a confirmed Odds API or ESPN equivalent (see table below) — no field-level
  gap for NFL, unlike MLB's confirmed SDQL-only F5/starting-pitcher/
  inning-by-inning gap (separate, unrelated issue, out of scope here).

| `nfl_games` column | Old (SDQL) source | New source |
|---|---|---|
| `home_points`/`away_points` | SDQL | Odds API `scores` |
| `home_line`/`away_line` | SDQL | Odds API `spreads` market |
| `total` (over/under line) | SDQL | Odds API `totals` market `point` |
| `home_money_line`/`away_money_line` | SDQL | Odds API `h2h` market |
| `home/away_quarter_scores` | SDQL | ESPN `linescores` |
| `home/away_first/second_half_points` | computed from quarter scores | same computation (ESPN-sourced) |
| `home/away_overtime_points` | SDQL 5th quarter value | ESPN 5th `linescores` entry (live-confirmed above) |
| `playoffs` | SDQL | ESPN `season.type == 3` |
| `game_site` (`'home'`/`'neutral'`) | SDQL | ESPN `neutralSite` flag |
| `start_time` | SDQL's own HHMM string | Odds API `commence_time` (ISO8601 UTC → ET) |
| `total_points`, `total_margin` | computed from points | same computation |
| `odds_event_id` | not populated today | Odds API event `id` (now actually populated) |

## Decisions made during design review

- **Go-forward only** — matches NHL. Switch the daily job; existing
  SDQL-sourced historical rows in `nfl_games` stay untouched, no backfill.
- **Bundle dead-code cleanup into this task**: delete `jobs/nfl_seed_yesterdays_games.py`
  (removes its embedded plaintext SDQL credentials from the working tree —
  they remain in git history, not scrubbed; separately, consider revoking
  the SDQL token at the provider once NBA/NCAAF/NCAAB are also migrated off
  it), `sdql_queries.py`, `historical_odds.py`, `single_game_data.py`, and
  the unused `check_for_trends` function in `utils.py` — all confirmed zero
  live callers in the original cross-codebase SDQL audit.
- **Leave `nfl_games.sdql_game_id` column alone** — unused going forward,
  same precedent as NHL's migration (not worth a schema change for this task).
- **Lenient insert policy** (a deliberate change from current behavior): the
  current SDQL job skips an entire game if `total`, `margin`, or either
  `line` is missing. The new job always inserts a game once the final score
  is known, leaving odds-derived columns NULL if a particular bookmaker
  market is thin for that game — a completed game should never be dropped
  from the table purely over incomplete pricing, since `home_line`/`away_line`/
  `total`/`home_money_line`/`away_money_line` are all nullable columns.
- **Lenient ESPN-matching policy**: if an Odds-API-sourced game can't be
  matched to an ESPN event for that date, insert what Odds API gave us
  (score, lines, moneyline, `odds_event_id`) with `home/away_quarter_scores`,
  `game_site`, and `playoffs` left NULL, and log it — don't drop the game.
- **No new migration or model** — `odds_event_id`'s column and unique
  constraint already exist; `nfl_games` stays raw-SQL, no new `models/nfl_game.py`.

## Components

### Games pipeline

- New job `jobs/nfl_odds_api_seed_yesterdays_games.py`, replacing
  `jobs/nfl_seed_yesterdays_games.py` (deleted as part of this work).
- Flow:
  1. Odds API historical `events` for the target date (yesterday, matching
     the current job's day-granularity) → for each event, look up
     `home_team_id`/`away_team_id` via `convert_team_name` against `teams
     WHERE sport = 'NFL'` (same lookup shape as the current job and as
     NHL's job).
  2. Odds API historical `odds` for each matched event
     (`markets=h2h,spreads,totals`, `regions=us`) → extract moneyline
     (`h2h`), line (`spreads`, home team's `point`), total (`totals` `point`).
     Prefer DraftKings (matching the convention already used in
     `jobs/nfl_historical_player_odds_import.py` and the NHL migration): for
     each of the three markets independently, use DraftKings's value if its
     `bookmakers` entry carries that market, otherwise fall back to the first
     bookmaker in the API response's `bookmakers` array (response order, not
     alphabetical) that carries it. A game can end up with, say, its
     moneyline from DraftKings and its total from a different bookmaker if
     DraftKings didn't post one — that's acceptable; each field is still a
     real line from a real book, not a fabricated value.
  3. ESPN `scoreboard?dates=YYYYMMDD` for the same date → match by team
     identity to find each game's ESPN event ID; `summary?event=<id>&enable=boxscore`
     → quarter scores (`linescores`), neutral-site flag, season type
     (playoffs), OT/final detail.
  4. Compute `total_points`, `total_margin`, first/second-half points,
     overtime points — same arithmetic as the current job, just fed from the
     new sources.
  5. Idempotent insert: `SELECT 1 FROM nfl_games WHERE odds_event_id = :id`
     skip-if-exists (replacing the old job's "has either team already played
     today" dedup hack, which only existed because SDQL had no stable event
     ID) — then `INSERT` with `odds_event_id` populated.
- `start_time`: derive from Odds API's `commence_time` (UTC ISO8601),
  converted to US/Eastern, formatted as `HH:MM:SS` — more reliable than the
  current job's manual 3-4-digit-string parsing of SDQL's format.

## Explicitly out of scope

- NBA, NCAAF, NCAAB migrations — separate future work, one sport at a time.
- MLB's F5/starting-pitcher/inning-by-inning gap — unrelated, pre-existing,
  not addressed here.
- Any UI change (game-details page, trend streaks) — this only touches the
  ingestion job and `nfl_games` rows.
- Full historical backfill/replace of existing `nfl_games` rows.
- Rotating or revoking the SDQL credential, or rewriting git history to
  scrub the currently-committed plaintext token — flagged as a follow-up
  consideration, not acted on in this task.
