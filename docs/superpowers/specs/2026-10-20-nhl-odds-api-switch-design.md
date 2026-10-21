# NHL: Switch Games to Odds API + Add Player Props Import

## Context

NHL games currently come from SDQL (`jobs/nhl_seed_yesterdays_games.py`), a paid
third-party sports database. `nhl_games` has 15,407 rows back to 2015-01-02. A
prior attempt to prototype an Odds-API-based games job exists at
`jobs/nhl_odds_api_yesterday.py` but is a hardcoded-date debug script, never
wired into production, and gets deleted as part of this work.

NHL has no player-props pipeline at all today. NFL, NBA, and MLB each have one,
following similar but not identical patterns. This work:

1. Switches the daily NHL games job from SDQL to the Odds API (go-forward only
   — existing historical rows stay as-is).
2. Adds a brand-new `nhl_player_props` import pipeline, modeled on NFL's.

## Research findings (live-verified 2026-10-20)

- **Odds API scores** (`/v4/sports/icehockey_nhl/scores/`) only returns final
  home/away goals — no period scores, starting goalies, powerplay goals, or
  overtime/shootout/playoffs flags. SDQL currently provides all six.
- **ESPN NHL** (`site.api.espn.com/apis/site/v2/sports/hockey/nhl/...`,
  free, same host NFL/NBA/MLB actuals already use) has a `summary` endpoint
  with `boxscore` (skaters: goals/assists/shots-on-goal; goalies: saves) and
  `plays` (play-by-play, including `strength.text` e.g. "Power Play") —
  confirmed via live pings against a real completed game
  (2026-10-18, CBJ @ MIN, event 401892533).
- **Period goals**: each competitor in `header.competitions[0].competitors`
  has a `linescores` array (one entry per period, plus a bonus entry for a
  shootout-deciding goal) — confirmed live.
- **Overtime / shootout**: `header.competitions[0].status.type.detail` is
  literally `"Final/OT"` or `"Final/SO"` (plain `"Final"` otherwise) —
  confirmed against several real OT/SO games. In one case (DET 4 @ SJ 3,
  2026-10-17) SDQL's own `overtime`/`shoot_out` flags looked wrong — its
  period-score sum didn't match the final score — while ESPN's `linescores`
  and `status.detail` were internally consistent, so this is likely more
  reliable than SDQL here, not less.
- **Playoffs**: `header.season.type` field confirmed present (1=preseason,
  2=regular, 3=postseason per ESPN convention); not yet verified against an
  actual playoff game since the NHL postseason doesn't start until spring.
- **Starting goalie**: verified via play-by-play, not boxscore. The
  boxscore's `starter` field on goalie entries exists but came back `null`
  on every game checked. Instead, the first period-1 `plays` entry of type
  `"Shot"` (or `"Goal"`) for each team has a `participants` entry with
  `type: "saver"` naming the *opposing* goalie who faced it — that's the
  opposing team's starting goalie. Verified against a real goalie-change
  game (FLA @ BUF, 2026-10-12, event 401892485): this correctly identified
  Buffalo's starter as Colten Ellis (not reliever Ukko-Pekka Luukkonen) and
  Florida's starter as Jacob Markstrom (not Akira Schmid) — both teams
  pulled their starter that game, confirming the method survives the exact
  case it needs to handle.
- **`game_site`** (home/neutral) isn't being carried forward — not needed:
  `home_team_id`/`away_team_id` already disambiguate home vs. away, so a
  hardcoded `'home'` going forward is fine.
- **Odds API NHL player-prop markets confirmed live** (current season, 8
  bookmakers): `player_goals`, `player_assists`, `player_points`,
  `player_shots_on_goal`, `player_total_saves`, `player_goal_scorer_anytime`,
  `player_power_play_points`. `player_blocked_shots` was not returned.
- **Historical player-prop coverage** confirmed back to 2023-10-11 (fewer
  bookmakers: draftkings/betonlineag/betmgm), well past the 2023 season start.
- **`services/player_resolver.py`** ("PlayerResolver") is NBA-only despite its
  generic name — hardcoded to `nba_players` tables. NFL never used it; NFL's
  `jobs/nfl_historical_player_odds_import.py` has its own embedded
  `resolve_player_simple()` operating directly on `nfl_players` /
  `nfl_player_aliases`. This is the pattern NHL mirrors, with this week's
  NFL alias-preservation-across-merge fixes already baked in from the start.
- `nhl_games.sdql_game_id` is 100% NULL today (the seed job never actually
  sets it) — dead column, left alone.
- `shared_utils.convert_team_name` already maps `'Utah Mammoth': 'Mammoth'`
  and the NHL teams table has all 32 current teams.
- Odds API account has ~4.8M requests remaining — ample for a full 3-season
  historical player-props backfill.

## Decisions made during design review

- Games: Odds API becomes the source for goals/moneyline/total; ESPN backfills
  the 6 columns Odds API can't provide (period goals, starting goalies,
  powerplay goals, overtime, shoot_out, playoffs). Go-forward only, no rewrite
  of existing history.
- Player props markets: **skater scoring** (goals, assists, points, shots on
  goal), **goalie saves** (total_saves), **anytime goal scorer**. Power-play
  points was considered and explicitly dropped — ESPN's standard boxscore
  doesn't break out PP points per player, and play-by-play parsing for it was
  judged not worth the complexity for this build.
- Backfill scope: full historical backfill from 2023 season start
  (2023-10-10) through present, matching NFL's depth.
- UI wiring (game-details page, trend streaks) is explicitly out of scope —
  a separate follow-on phase once the pipeline is proven, same as how NFL's
  consumer landed after its import pipeline.

## Components

### 1. Games pipeline

- New job `jobs/nhl_odds_api_seed_yesterdays_games.py`, replacing
  `jobs/nhl_seed_yesterdays_games.py` (SDQL). Delete the stale prototype
  `jobs/nhl_odds_api_yesterday.py`.
- Flow: Odds API historical `scores` (goals) + historical `odds` (h2h for
  moneyline, totals for total) for the target date, matched by team name via
  `convert_team_name`, same matching shape as the existing prototype. Then
  ESPN `scoreboard?dates=YYYYMMDD` + `summary?event=<id>&enable=boxscore,plays`
  to fill: period goals (`linescores` per competitor), starting goalies
  (first period-1 `plays` entry of type "Shot"/"Goal", `saver` participant
  identifies the opposing team's starter), powerplay goals (count `plays`
  where `strength.text == "Power Play"`, grouped by scoring team),
  overtime/shootout (`status.type.detail` contains "OT"/"SO"), playoffs
  (`header.season.type == 3`). `game_site` is hardcoded `'home'` going
  forward — not needed since `home_team_id`/`away_team_id` already
  disambiguate.
- Migration adds a nullable, unique `odds_event_id` column to `nhl_games` for
  idempotent dedup on re-run (the existing `sdql_game_id` unique index stays,
  untouched, still unused going forward).
- New `models/nhl_game.py` — first ORM model for `nhl_games` (table currently
  has none; all access today is raw SQL/`text()`), including the new column.

### 2. Player props schema

New tables/models mirroring the `nfl_player*` set structurally:

- `models/nhl_player.py`, `models/nhl_player_alias.py`,
  `models/nhl_player_name_mismatch.py`, `models/nhl_player_prop.py`.
- `nhl_player_props` columns:
  - Bookkeeping (same shape as `nfl_player_props`): `player_id`,
    `normalized_name`, `game_date`, `odds_event_id`, `espn_event_id`,
    `odds_source`, `bookmaker`, player/opponent/odds-side team info,
    `did_not_play`, `actuals_unavailable_reason`, timestamps.
  - Skater scoring: `odds_player_goals`, `odds_player_assists`,
    `odds_player_points`, `odds_player_shots_on_goal` (+ over/under price
    pairs each) and matching `actual_player_*` columns.
  - Goalie: `odds_player_total_saves` (+ prices) / `actual_player_total_saves`.
  - Anytime goal: `odds_player_goal_scorer_anytime` (+ price, yes-only like
    NFL's `anytime_td`) / `actual_player_goal_scorer_anytime` (bool).
  - Same unique constraint (`player_id`, `odds_event_id`) and indexes as NFL.
- `api/routes/internal/nhl_mismatch.py` — admin tool for manual player-match
  fixes, mirroring NFL's, built from the start rather than retrofitted.

### 3. Import jobs

- `jobs/nhl_historical_player_odds_import.py` — Odds API historical events +
  odds (draftkings primary bookmaker, matching NFL) for markets
  `player_goals,player_assists,player_points,player_shots_on_goal,player_total_saves,player_goal_scorer_anytime`.
  Player resolution via an embedded `resolve_player_simple()` ported from
  NFL's, operating on `nhl_players`/`nhl_player_aliases`: exact
  normalized-name match first, alias recorded on every resolution, fuzzy
  match, placeholder player as last resort — with alias preservation across
  any later mismatch-merge (the fix NFL needed after the fact, included here
  from day one).
- `jobs/nhl_historical_player_actuals_import_reverse.py` — ESPN NHL
  `scoreboard` + `summary?enable=boxscore` (free). Skaters group → goals/
  assists/shots-on-goal directly; points = goals+assists; goalies group →
  saves; anytime-goal actual derived from goals > 0.
- `jobs/nhl_historical_import_orchestrator_reverse.py START [END]` — runs
  both jobs for a date range. No defense-props job (NHL has no team D/ST
  market). Idempotent (safe to re-run; step 1 re-pays Odds API credits).
- Initial backfill: 2023-10-10 through present.

## Explicitly out of scope

- Wiring `nhl_player_props` into the game-details page or trend-streak UI.
- Power-play points market (odds or actuals).
- Any change to historical `nhl_games` rows already in the database.
