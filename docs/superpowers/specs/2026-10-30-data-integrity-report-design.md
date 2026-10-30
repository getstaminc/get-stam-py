# Daily Data Integrity Report (Games + Player Props vs. ESPN)

## Context

The user wants a recurring check that catches ingestion gaps: did yesterday's
games actually land in our DB for every sport, and for the sports with a
player-props pipeline, did props actually get imported for those games. This
sits alongside (not instead of) `jobs/send_player_mismatch_report.py`, which
already checks name-matching quality — this new job checks *completeness*.

ESPN was chosen as the ground-truth source (free, no API-credit cost, already
used elsewhere in the codebase for actuals/enrichment) rather than Odds API
(credits cost money) or re-deriving truth from our own ingestion pipeline
(circular — wouldn't catch a pipeline-wide failure).

Delivery: daily email to the admin inbox via the existing Brevo
`EmailService.send_digest_to_one`, following the exact precedent of
`jobs/send_player_mismatch_report.py` (single recipient, not the subscriber
list; subject-line failure prefix; non-fatal per-sport error handling so one
sport's API hiccup doesn't kill the whole report).

## Research findings (live-verified 2026-10-30)

**ESPN scoreboard slugs confirmed working for every sport we track**, including
three sports this codebase has never called ESPN for before (NCAAF, NCAAB,
soccer leagues):

| Sport | ESPN slug | Final-status string | Live-verified |
|---|---|---|---|
| NBA | `basketball/nba` | `STATUS_FINAL` | already used in `jobs/nba_historical_player_actuals_import_reverse.py` |
| NFL | `football/nfl` | `STATUS_FINAL` | already used in `jobs/nfl_historical_player_actuals_import_reverse.py` |
| MLB | `baseball/mlb` | `STATUS_FINAL` | already used in `jobs/mlb_historical_player_actuals_import_reverse.py` |
| NHL | `hockey/nhl` | `STATUS_FINAL` | already used in `jobs/nhl_odds_api_seed_yesterdays_games.py` |
| NCAAF | `football/college-football` | `STATUS_FINAL` | new — confirmed live, 2 events on 2026-10-28 |
| NCAAB | `basketball/mens-college-basketball` | `STATUS_FINAL` | new — confirmed live, 20 events on 2026-11-06 (season hadn't started 10-28); pass `groups=50` to restrict to Division I, matching what SDQL/our DB covers |
| Soccer (EPL/La Liga/Bundesliga/Ligue1/Serie A) | `soccer/eng.1`, `soccer/esp.1`, `soccer/ger.1`, `soccer/fra.1`, `soccer/ita.1` | **`STATUS_FULL_TIME`** (not `STATUS_FINAL`) | new — confirmed live, 5 events on 2026-10-25 for `eng.1`/`ita.1` |
| UCL | `soccer/uefa.champions` | `STATUS_FULL_TIME` | slug confirmed to resolve (0 events on test date — no fixtures that day, not an error) |

Request shape is identical to the existing pattern in
`jobs/nba_historical_player_actuals_import_reverse.py:35-42`:
```python
url = f"https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard"
params = {"dates": "YYYYMMDD", "limit": 50}  # NCAAB also needs groups=50
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
```

**Operational risk carried forward, not re-solved here:** `jobs/nfl_daily_player_team_assignment_job.py:16` notes ESPN's *roster* endpoint 403s from Heroku's datacenter IPs and must run locally. The *scoreboard* endpoint is not confirmed blocked — several existing jobs already call it from Heroku Scheduler successfully (`jobs/nba_daily_player_props_import_job.py`, `jobs/mlb_daily_player_team_assignment_job.py`) — but this has never been exercised from Heroku for the three new sports/slugs. Task 1 below includes running the new job once for real from `heroku run` as the verification step, specifically to catch this before it's relied on daily.

**Why count-based comparison, not per-game identity matching:** our DB tables
don't store ESPN event IDs, and team-name formats diverge wildly between
ESPN and our DB per sport (ESPN NCAAB uses "Duke Blue Devils"; our DB's SDQL-era
NCAAB names use codes like "DUKE" via `convert_team_name_ncaab` in
`shared_utils.py`; soccer club names differ by abbreviation convention too).
Building a reliable name-matching layer for 8 more sport/league combinations
is a separate, much larger effort. Comparing **counts** (ESPN finished-game
count for date X vs. our DB's row count for date X, per sport) catches the
actual failure mode this check exists for — an ingestion job silently
skipping a day or dropping games — without needing per-game identity
matching. When counts mismatch, the email includes ESPN's raw matchup list
(away @ home) for that date so a human can eyeball which game is likely
missing; it does not attempt to auto-resolve which specific DB row is absent.

**Game table per sport (name, date column) — confirmed via migrations/models:**

| Sport | Table | Date column |
|---|---|---|
| NBA | `nba_games_1` (NOT `nba_games` — that's dead legacy code, confirmed unused) | `game_date` |
| NFL | `nfl_games` | `game_date` |
| MLB | `mlb_games` | `game_date` |
| NHL | `nhl_games` | `game_date` |
| NCAAF | `ncaaf_games` | `game_date` |
| NCAAB | `ncaab_games` | `game_date` |
| EPL/La Liga/Bundesliga/Ligue1/Serie A/UCL | `soccer_games`, filtered by `league` column. Confirmed exact stored values (`jobs/*_seed_yesterdays_games.py`): `'EPL'`, `'LA LIGA'`, `'BUNDESLIGA'`, `'LIGUE 1'`, `'SERIE A'`, `'UCL'` | `game_date` |

**Player-prop tables — only exist for NBA, NFL, MLB, NHL** (confirmed via
repo-wide grep: no `ncaaf_player_props`/`ncaab_player_props`/
`soccer_player_props` tables exist anywhere). So the player-props-completeness
check only runs for these four sports; NCAAF/NCAAB/soccer get the games-count
check only.

| Sport | Prop table(s) | Join key back to games table |
|---|---|---|
| NFL | `nfl_player_props` | `odds_event_id` — `nfl_games.odds_event_id` matches directly |
| MLB | `mlb_batter_props`, `mlb_pitcher_props` (check both — a game can have one without the other, per existing convention in `jobs/backfill_postponed_game_reason.py`) | `odds_event_id` — `mlb_games.odds_event_id` matches directly |
| NHL | `nhl_player_props` | `odds_event_id` — `nhl_games.odds_event_id` matches directly |
| NBA | `nba_player_props` | **No `odds_event_id` on `nba_games_1`.** `nba_player_props` has `odds_home_team_id`/`odds_away_team_id` (Integer, FK `teams.team_id`) which line up directly with `nba_games_1.home_team_id`/`away_team_id` (confirmed via `migrations/versions/9fff514ec21c_new_nba_games_table.py` and `models/nba_player_prop.py`) — join on `game_date` + both team IDs, no name matching needed. |

Existing precedent query for "do props exist for this game" —
`jobs/nba_missing_odds_events_report.py:44-49`:
```python
def check_event_in_db(conn, event_id):
    result = conn.execute(text("SELECT COUNT(*) FROM nba_player_props WHERE odds_event_id = :event_id"), {"event_id": event_id})
    return result.scalar() > 0
```
This job inverts the direction (DB game → does a prop row exist) but reuses
the same `COUNT(*) ... WHERE odds_event_id = :id` shape for NFL/MLB/NHL.

**Scheduling:** Heroku Scheduler invokes `python jobs/<name>.py` directly, no
wrapper script, no `app.json` scheduler config in-repo (confirmed — it's a
manual dashboard step, same as every other scheduled job here). Convention
for the docstring header, copied from `jobs/send_daily_trends_digest.py:1-5`:
```
"""
<Job Name>
Runs every morning via Heroku Scheduler:
  python jobs/send_data_integrity_report.py
"""
```
Pick a run time **after** the existing nightly seed jobs would have run for
"yesterday" (the seed jobs themselves run on a schedule not captured in the
repo — the user will need to confirm the actual Heroku Scheduler run times
for the seed jobs and set this new job to run after all of them, so it isn't
checking for games an earlier job hasn't had a chance to insert yet).

## Non-goals (explicitly out of scope for this version)

- Per-game identity matching / auto-resolving exactly which game is missing
  (count mismatch + ESPN's raw matchup list is sufficient per user's stated
  need: "confirm they are in our database").
- Building ESPN name-matching for NCAAF/NCAAB/soccer (count-only for those).
- Historical backfill or re-running past dates — this checks "yesterday"
  only, once a day, same cadence as the existing seed jobs it's auditing.
- Changing or fixing any ingestion job — this is a detection-only report.
