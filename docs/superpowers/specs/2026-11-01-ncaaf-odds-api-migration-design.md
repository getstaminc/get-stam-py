# NCAAF: Switch Games from SDQL to Odds API + ESPN

## Context

NCAAF games currently come from SDQL (`jobs/ncaaf_seed_yesterdays_games.py`),
via a hardcoded username/token embedded directly in the job file. This is
the third of four remaining SDQL-dependent sports (NFL, NBA done; NCAAF
here; NCAAB next). Unlike NFL/NBA/NHL, this migration surfaced two
NCAAF-specific complications that don't exist for the pro sports:

1. **Scope**: `ncaaf_games`/`teams WHERE sport='NCAAF'` covers all of NCAA
   Division I football — both FBS (~134 teams) and FCS (~128 teams), 259
   teams total, confirmed via direct query. ESPN's scoreboard `groups`
   parameter doesn't cleanly separate these: `groups=90` is clean FBS, but
   `groups=81` (initially assumed to be "FCS") actually returns a much
   broader bucket including Division II, Division III, NAIA, and even
   Canadian college teams alongside real FCS schools — confirmed live by
   sampling real scoreboard results across 7 Saturdays.
2. **A large pre-existing team-name mapping problem** in
   `shared_utils.convert_team_name`'s NCAAF section (250+ entries): it was
   built against some other naming convention (SDQL's, or an older ESPN
   convention) and has never actually been exercised against ESPN's current
   names, since the old SDQL job never called `convert_team_name` at all —
   same root cause as the NBA migration's Hawks/Clippers bugs, just a larger
   blast radius here.

**Decision (revised after live verification — see below): two-job hybrid,
not a full source cutover.** The original plan ("full migration, FCS odds
fields go NULL where Odds API has no line") was tested directly against 6
real FCS-vs-FCS games already in `ncaaf_games` (Dartmouth/Harvard,
Cornell/Lehigh, Princeton/Cornell, etc.) — **none of the six even appeared
in Odds API's game list at all**, not merely "no market." SDQL currently
provides real `home_line`/`away_line`/`total` for virtually every FCS game,
including small-conference matchups (Ivy League, SWAC) Odds API doesn't
track at all. A full cutover would be a confirmed, substantial regression
for FCS, not a theoretical one.

Chosen design: **fix the naming bugs and migrate scores/enrichment to
Odds API + ESPN as the primary source for everything (same as NFL/NBA)**,
but add a second, later-scheduled job that queries SDQL for the same date
and **fills in only whatever is still NULL** after the first job ran — never
overwrites a value the first job already got from Odds API/ESPN. This
keeps Odds API/ESPN authoritative wherever they have data (effectively all
of FBS, plus whatever FCS games either source happens to cover) and uses
SDQL strictly as a fallback for the gaps, mostly FCS lines.

This does **not** reduce SDQL call frequency — the fallback job still needs
the same daily "fetch all of yesterday's games" SDQL call the current job
already makes, since SDQL doesn't support querying for only specific
missing games. What changes is SDQL's role: primary source for everything
→ fallback source only for whatever the free sources couldn't cover.

**Scheduling, two separate daily jobs** (per user: data availability differs
by time of day for each source):
- `jobs/ncaaf_odds_api_seed_yesterdays_games.py` — Odds API + ESPN, primary
  insert. Scheduled ~10:00 AM UTC (4am local).
- `jobs/ncaaf_sdql_fallback_fill.py` — SDQL fallback fill, runs after the
  first job and only updates NULL columns on existing rows (or inserts a
  game from scratch if even ESPN's broad `groups=81` scoreboard missed it
  entirely — expected to be rare). Scheduled ~6:00 PM UTC (noon local).

**Separately discovered, NOT part of this migration's scope**: a real,
current data gap — `ncaaf_games` has zero rows for 2026-10-24, a Saturday
sandwiched between two days with real data, while every other Saturday that
month has 86-101 games. This is an active SDQL ingestion failure on a
specific date, unrelated to the source migration itself. Flagged for
separate investigation/backfill, not addressed here.

## Research findings (live-verified 2026-11-01)

- **`ncaaf_games` has no `odds_event_id` column** (confirmed via
  `information_schema.columns`) — unlike NFL (which already had one), this
  migration needs a new migration, same shape as NBA's
  `fd711e7e2b11_add_odds_event_id_to_nba_games_1.py`.
- **`ncaaf_games` has real neutral-site games historically** — the current
  SDQL job's own query includes `(site='home' or site='neutral')`, same as
  NFL (bowl games, season-opening neutral-site matchups are common in
  college football). This needs the same ESPN-`neutralSite`-derived
  `game_site` handling NFL uses, NOT NBA's simpler hardcoded-`'home'`
  approach.
- **ESPN scoreboard `groups` parameter is reliable on `/scoreboard`, NOT on
  `/teams`**: confirmed `groups=90`/`groups=81` correctly filter
  `/scoreboard` results (verified against real game data across 7
  Saturdays), but the same parameter on `/teams` returns an apparently
  unfiltered ~400-team list for *either* group value (confirmed: Iowa
  Hawkeyes, a major FBS program, was entirely absent from a `groups=90`
  `/teams` call) — do not use `/teams` for NCAAF schedule/name discovery.
- **Chosen scope strategy**: don't try to derive "which division counts"
  from ESPN's group semantics at all. Pull scoreboard results from both
  `groups=90` and `groups=81`, then filter by whether the team is already
  recognized in our existing `teams WHERE sport='NCAAF'` roster (via
  `convert_team_name`) — our 259-team roster already *is* the authoritative
  scope definition. A team ESPN returns that isn't in our roster (the
  Division II/NAIA leakage from `groups=81`) is silently skipped, same
  lenient pattern used for every other unmatched-team case.
- **Real team-name mapping bugs confirmed via 7-Saturday live sample** (301
  distinct teams seen in real final games, 231 matched, 70 unmatched).
  Cross-referencing the 70 against our existing 259-team roster and dict,
  roughly 15-20 are genuine mapping bugs for teams we do track (the rest are
  the Division-II/NAIA leakage from `groups=81`, correctly left unmatched).
  Confirmed real fixes needed, each ESPN's current name → our existing
  short code:
  - `"Hawai'i Rainbow Warriors"` → `HAW` (dict has `'Hawaii Rainbow Warriors'`, missing the apostrophe)
  - `"Massachusetts Minutemen"` → `MAS` (dict only has `'UMass Minutemen'`)
  - `"Southern Miss Golden Eagles"` → `SMIS` (dict only has `'Southern Mississippi Golden Eagles'`)
  - `"Campbell Fighting Camels"` → `CAMP` (dict only has `'Campbell Camels'`)
  - `"Gardner-Webb Runnin' Bulldogs"` → `GARD` (dict only has `'Gardner-Webb Bulldogs'`)
  - `"Presbyterian Blue Hose"` → `PRES` (dict only has `'Presbyterian College Blue Hose'`)
  - `"Prairie View A&M Panthers"` → `PRVW` (dict only has `'Prairie View Panthers'`)
  - `"San José State Spartans"` → `SJST` (dict only has the no-accent `'San Jose State Spartans'`)
  - `"Southeast Missouri State Redhawks"` → `SEMST` (dict has the two-word `'Southeast Missouri State Red Hawks'`)
  - `"Florida International Panthers"` → `FINT` (dict only has `'Florida International Golden Panthers'` — team dropped "Golden" from its branding)
  - `"UConn Huskies"` → `CON` (dict only has `'Connecticut Huskies'`)
  - `"UAlbany Great Danes"` → `ALBS` (dict only has `'Albany Great Danes'`)
  - `"App State Mountaineers"` → `APP` (dict only has `'Appalachian State Mountaineers'` — ESPN uses the shortened branding)
  - `"Sam Houston Bearkats"` → `SHST` (dict only has `'Sam Houston State Bearkats'` — school dropped "State" from its branding)
  - `"East Texas A&M Lions"` → `TXAMC` (dict has the pre-rebrand `'Texas A&M-Commerce Lions'` — the school renamed itself)
  - `"Tarleton State Texans"` → `TARL` (dict only has `'Tarleton State'`, missing the mascot word, which matters because `convert_team_name` does exact full-string matching)
  - `"Miami (OH) RedHawks"` → the dict's own entry produces `'MIAOH'`, but this doesn't match whatever short code our `teams` table actually stores for this school — needs direct verification against the live `teams` row during implementation, not just the dict entry, since a typo could exist on either side.
  The implementation task must re-derive this list fresh against the current `shared_utils.py` and current `teams` table state (not just copy this list blindly), since this spec's research is a point-in-time snapshot.
- **Odds API NCAAF coverage confirmed FBS-heavy**: of 104 distinct teams seen
  in 3 days of live Odds API scores, 103 were FBS and only 1 was FCS (North
  Dakota State). Confirmed directly against 6 real FCS-vs-FCS games already
  in `ncaaf_games`: none appeared in Odds API's historical odds game list at
  all for their actual date. This gap is exactly what job 2's SDQL fallback
  exists to close — see the revised Decision above.
- **Field-by-field gap check**: every column the current SDQL job writes has
  a confirmed Odds API or ESPN equivalent for FBS games. For FCS games where
  Odds API/ESPN come up short, job 2's SDQL fallback is expected to supply
  real values for most of them — matching current data richness rather than
  accepting a permanent gap.

| `ncaaf_games` column | Old (SDQL) source | New primary source | Fallback (job 2, SDQL) |
|---|---|---|---|
| `home_points`/`away_points` | SDQL | Odds API `scores`; ESPN `competitor.score` if Odds API lacks the game | SDQL, only if the row/column is still NULL |
| `home_line`/`away_line` | SDQL | Odds API `spreads` market | SDQL fills NULL (expected for most FCS games) |
| `total` | SDQL | Odds API `totals` market `point` | SDQL fills NULL |
| `home_money_line`/`away_money_line` | SDQL | Odds API `h2h` market | SDQL fills NULL |
| `home/away_quarter_scores` | SDQL | ESPN `linescores` | SDQL fills NULL if ESPN also missed it |
| `home/away_first/second_half_points` | computed | same computation (ESPN-sourced) | recomputed in job 2 if SDQL supplied quarter scores job 1 didn't have |
| `home/away_overtime_points` | SDQL 5th quarter value | ESPN 5th `linescores` entry (college OT can have 2+ periods — same accepted limitation as NFL/NBA: only the first OT period is captured) | same recompute path as above |
| `playoffs` | SDQL | ESPN `season.type == 3` | SDQL fills NULL |
| `game_site` (`'home'`/`'neutral'`) | SDQL | ESPN `neutralSite` flag (same as NFL) | SDQL fills NULL |
| `start_time` | SDQL's own HHMM string | Odds API `commence_time` (ISO8601 UTC → ET) | SDQL's own HHMM parsing (same conversion the old job already does), only if still NULL |
| `total_points`, `total_margin` | computed | same computation | recomputed in job 2 if job 1 left points NULL and SDQL supplied them |
| `odds_event_id` | column doesn't exist today | Odds API event `id` (new column, this migration) | never set by job 2 — SDQL has no equivalent id, this column simply stays NULL for SDQL-only games |

**Lenient policy, both jobs**: never drop a game over missing data in either
direction. Job 1 inserts whatever Odds API/ESPN found, NULL elsewhere. Job 2
never overwrites a non-NULL value — it only fills gaps, and only inserts a
brand-new row if the game is missing entirely after job 1 (expected to be
rare, since ESPN's broad `groups=81` scoreboard should catch nearly
everything SDQL would have found too).

## Decisions made during design review

- **Two-job hybrid, all 259 teams** — not a full SDQL cutover (see Decision
  above). Odds API + ESPN are the primary source for every team; SDQL is a
  scheduled-later fallback that only fills NULLs, never overwrites.
- **New migration**: add `ncaaf_games.odds_event_id` (nullable `String(100)`
  + unique constraint), same shape as NBA's.
- **Scope via existing teams roster, not ESPN's group semantics**: pull
  `groups=90` + `groups=81` scoreboard results, filter to games where both
  teams resolve (via a corrected `convert_team_name`) to an existing row in
  `teams WHERE sport='NCAAF'`. Unmatched-team games are silently skipped.
  The SDQL fallback job matches the same way SDQL always has (its own
  short-name strings against the `teams` table directly, no `convert_team_name`
  involved on that side — unchanged from the current job).
- **Dual-source scores in job 1**: Odds API `scores` for games it covers;
  ESPN's own `competitor.score` for games Odds API has no line for at all —
  this is the one real structural addition beyond the NFL/NBA job template.
- **Neutral-site handling**: derive `game_site` from ESPN's `neutralSite`
  flag, same as NFL (not NBA's hardcoded `'home'`); SDQL fallback uses its
  own `site` field exactly as the current job does, only when still NULL.
- **Bundle the team-name mapping fixes into job 1's task** — they block
  correct matching for both the Odds API and ESPN paths equally. SDQL's own
  matching (direct short-name string match) is unaffected and unchanged.
- **Scheduling**: job 1 (`ncaaf_odds_api_seed_yesterdays_games.py`) at
  ~10:00 AM UTC (4am local); job 2 (`ncaaf_sdql_fallback_fill.py`) at
  ~6:00 PM UTC (noon local) — per the user's operational knowledge that
  Odds API's data is reliably available earlier in the day than SDQL's.
- **The 2026-10-24 data gap is explicitly out of scope** — flagged for
  separate follow-up, not fixed as part of this migration.
- **Go-forward only** — no backfill of existing `ncaaf_games` rows.
- **SDQL is not retired for NCAAF** — its daily call frequency is unchanged
  from today (still fetches the full day's games, since SDQL has no
  "only these specific games" query mode); only its *role* changes, from
  primary source to fallback-for-gaps.

## Explicitly out of scope

- NCAAB migration — separate future work.
- The 2026-10-24 ingestion gap — separate follow-up investigation.
- Any UI change.
- Full historical backfill/replace of existing `ncaaf_games` rows.
- Rotating/revoking the SDQL credential.
