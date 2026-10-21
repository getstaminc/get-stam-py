# Line Movement (Open vs. Now) for NFL, NHL, MLB, NCAAF

## Context

Today, scheduled-game odds (`GET /api/odds/<sport>` and `/api/odds/<sport>/<game_id>`)
are fetched live from the-odds-api.com on every request via `get_odds_data()`
(`api/external_requests/odds_api.py`) and never persisted. The only persisted odds are
the *closing* line captured by each sport's seed job (`jobs/*_seed_yesterdays_games*.py`),
snapshotted roughly 1 hour before kickoff, after the game is in `nfl_games` / `nhl_games`
/ `mlb_games`. There is no "opening line" stored anywhere.

The goal is an ESPN-style Open vs. Now comparison (see
`https://www.espn.com/nfl/game/_/gameId/401873010/patriots-bears`) for spread, total, and
moneyline, for NFL, NHL, MLB, and NCAAF.

The-odds-api.com's historical/snapshot endpoint
(`/v4/historical/sports/{sport}/odds`) is already paid for and in production use (e.g.
`jobs/mlb_seed_yesterdays_games_odds_api.py:77` `get_historical_odds_at_time`), which
makes it possible to reconstruct an opening line after the fact without running a
continuously-polling job.

## Decisions made during design review

- **Capture via Historical Odds API, not continuous polling.** A nightly job scans
  backward from kickoff to find the real opening snapshot, rather than running a
  live-odds poller. Cheaper, no new always-on infrastructure, and reusable for games
  that already exist by the time this ships.
- **No mass backfill of games already completed/stored in `nfl_games`/`nhl_games`/
  `mlb_games`.** Only upcoming games get an opening line captured, going forward from
  deployment. Backfilling tens of thousands of old rows was explicitly ruled out —
  not worth the API call volume/runtime for this phase.
- **Nightly pre-warm job, not lazy per-request computation.** Because "Open" is shown
  everywhere `GameOdds` renders (including list/scoreboard pages with many games at
  once), computing it lazily on first view would mean either blocking page load or a
  visible per-card pop-in while a multi-call backward scan runs. A nightly job
  pre-computes and caches it, so by the time anyone views a game it's already
  available (or not yet, if the market hadn't opened by last night's run — no live
  scan ever happens in the request path).
- **Opening-line precision is sport-appropriate, not exact-to-the-minute.** NFL scans
  in daily steps up to 21 days back (lines can post over a week ahead); MLB/NHL scan
  in 12-hour steps up to 3 days back (lines post close to game day). This trades a bit
  of precision for a bounded number of historical-API calls per game, spent once and
  cached permanently.
- **"Opening" rows only render where current odds already render.** `GameOdds.tsx`
  already hides the odds block once a game is live or final (`!isGameOver && !isLive`).
  Line movement doesn't change that visibility rule — it only adds an "Open" row
  alongside the existing pregame odds rows. No change to completed-game display.
- **NFL, NHL, MLB, and NCAAF.** Not NBA (still on SDQL, not the Odds API, per
  `jobs/nba_seed_yesterdays_games.py`), not soccer/NCAAB. NCAAF's *completed*-game
  seed job (`jobs/ncaaf_seed_yesterdays_games.py`) is also still SDQL-based and has no
  `odds_event_id` — irrelevant here since this feature only reads live/upcoming odds
  from the Odds API and never touches the `*_games` tables (no backfill, per below).
  NCAAF's live odds already come from the Odds API today
  (`americanfootball_ncaaf` in `SPORT_URL_TO_API_KEY`), same as NFL.

## Components

### 1. Data model

New table `game_opening_lines`, one immutable row per captured game:

| column | type | notes |
|---|---|---|
| `id` | serial PK | |
| `sport` | varchar | `nfl` / `nhl` / `mlb` / `ncaaf` — matches existing DB sport-key convention |
| `odds_event_id` | varchar | the Odds API event id; unique together with `sport` |
| `home_team` | varchar | Odds-API full name, for debugging |
| `away_team` | varchar | Odds-API full name, for debugging |
| `commence_time` | timestamp | |
| `opening_snapshot_time` | timestamp | when the backward scan actually found odds — not a fixed offset |
| `home_spread_point` | float | |
| `home_spread_price` | integer | |
| `away_spread_point` | float | |
| `away_spread_price` | integer | |
| `home_moneyline` | integer | |
| `away_moneyline` | integer | |
| `total_point` | float | |
| `over_price` | integer | |
| `under_price` | integer | |
| `created_at` | timestamp | server default now() |

Unique index on (`sport`, `odds_event_id`). Rows are write-once: once a game has an
opening line captured, it is never updated.

New model `models/game_opening_line.py` (SQLAlchemy, for the migration — direct
psycopg2 is used for the actual read/write paths, consistent with the rest of the
codebase's query style per `CLAUDE.md`).

Migration: new table only, no changes to existing `*_games` tables.

### 2. Capture job

New `jobs/capture_opening_lines.py`, intended to run nightly via Heroku Scheduler
(same deployment pattern as the existing `*_seed_yesterdays_games*` jobs — run
manually documented in this repo's command docs, scheduled via the Heroku Scheduler
add-on).

For each of `nfl`, `nhl`, `mlb`, `ncaaf`:

1. Fetch upcoming games in that sport's lookahead window via the existing live odds
   flow (`get_odds_data` / `GameService.get_games_for_date`-equivalent):
   - NFL, NCAAF: next 21 days
   - MLB, NHL: next 3 days
2. Skip any event already present in `game_opening_lines` for that sport.
3. For the remainder, skip any event whose live odds are currently all-null (market
   not open yet — it'll be picked up on a future night once it is).
4. For the rest, scan backward from `commence_time` using the Historical Odds API
   (`/v4/historical/sports/{sport_key}/odds`, same shape as
   `get_historical_odds_at_time` in `jobs/mlb_seed_yesterdays_games_odds_api.py`):
   - NFL, NCAAF: daily steps, starting at `commence_time - 21d`, stepping forward
     until a snapshot contains odds for this event (draftkings bookmaker,
     `h2h,spreads,totals` markets — same bookmaker/market set the rest of the codebase
     already uses for these sports).
   - MLB/NHL: 12-hour steps, starting at `commence_time - 3d`.
   - The first snapshot where the event has bookmaker data is the opening line.
     Record `opening_snapshot_time` as that snapshot's timestamp.
   - If no snapshot in the window has data (shouldn't happen given step 3 confirmed
     odds exist now, but guards against a transient gap), skip and retry next night.
5. Upsert the result into `game_opening_lines` (`ON CONFLICT (sport, odds_event_id) DO
   NOTHING` — write-once).

Idempotent and safe to re-run: already-captured events are skipped in step 2.

### 3. API changes

`GameService.get_games_for_date` and `GameService.get_single_game`
(`api/services/game_service.py`) batch-fetch matching `game_opening_lines` rows for
all event ids in the response (single `IN (...)` query, not N queries), and attach an
`opening` object to each formatted game when a row exists:

```json
"opening": {
  "home": { "spread_point": -3.0, "spread_price": -110, "h2h": -155 },
  "away": { "spread_point": 3.0, "spread_price": -110, "h2h": 135 },
  "totals": { "over_point": 47.5, "over_price": -110, "under_point": 47.5, "under_price": -110 },
  "snapshot_time": "2026-10-07T17:00:00Z"
}
```

Omitted entirely when no row exists yet (not yet opened, or not yet captured by a
nightly run) — frontend treats absence as "no Open row to show," not an error.

Scoped to `sport in {nfl, nhl, mlb, ncaaf}`; other sports' formatted games never get
an `opening` key.

### 4. Frontend

`GameOdds.tsx`: add an "Open" sub-row under each of H2H, Spread, and Total, inside the
existing `!isGameOver && !isLive` block (pregame odds block), reading
`game.opening?.home/.away/.totals`. Rendered wherever `GameOdds` renders today — both
list/scoreboard cards and the detail page — per the approved design. When
`game.opening` is absent, the block renders exactly as it does today (no layout gap,
no placeholder row).

No new frontend fetch — `opening` rides along in the existing `/api/odds/...`
responses `GameOdds` already consumes.

## Explicitly out of scope

- NBA, soccer, NCAAB.
- Backfilling opening lines for games already completed/stored in `nfl_games` /
  `nhl_games` / `mlb_games` before this ships.
- A full movement timeline/chart (multiple snapshots over time) — only Open vs. Now,
  two points.
- Showing line movement once a game is live or final (matches existing `GameOdds`
  visibility rules, unchanged).
- Any change to the existing closing-line capture in the `*_seed_yesterdays_games*`
  jobs.
