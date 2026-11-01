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

**Decision (confirmed with the user, given both findings): full migration**
— fix the real naming bugs, migrate all 259 teams. FBS games get full Odds
API lines; FCS games get ESPN scores with odds fields left NULL wherever
Odds API has no line for that specific game (which is most FCS games — Odds
API's NCAAF coverage is overwhelmingly FBS, with only occasional marquee FCS
games like North Dakota State carrying a market).

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
  Dakota State) — consistent with "FCS games mostly get NULL odds fields"
  being the expected, not exceptional, outcome for this sport.
- **Field-by-field gap check**: every column the current SDQL job writes has
  a confirmed Odds API or ESPN equivalent for FBS games; for FCS games,
  score/quarter-score fields still come from ESPN, odds-derived fields are
  expected to be NULL more often than not (lenient policy, not a gap to
  "fix" — this is a real, permanent characteristic of FCS betting-market
  coverage, not a bug).

| `ncaaf_games` column | Old (SDQL) source | New source |
|---|---|---|
| `home_points`/`away_points` | SDQL | Odds API `scores` (FBS); ESPN boxscore score (FCS fallback — see Decisions) |
| `home_line`/`away_line` | SDQL | Odds API `spreads` market (FBS only in practice) |
| `total` | SDQL | Odds API `totals` market `point` (FBS only in practice) |
| `home_money_line`/`away_money_line` | SDQL | Odds API `h2h` market (FBS only in practice) |
| `home/away_quarter_scores` | SDQL | ESPN `linescores` |
| `home/away_first/second_half_points` | computed | same computation (ESPN-sourced) |
| `home/away_overtime_points` | SDQL 5th quarter value | ESPN 5th `linescores` entry (same pattern proven for NFL/NBA; college OT can have 2+ periods — same accepted limitation as NFL/NBA: only the first OT period is captured) |
| `playoffs` | SDQL | ESPN `season.type == 3` |
| `game_site` (`'home'`/`'neutral'`) | SDQL | ESPN `neutralSite` flag (same as NFL) |
| `start_time` | SDQL's own HHMM string | Odds API `commence_time` (ISO8601 UTC → ET) |
| `total_points`, `total_margin` | computed | same computation |
| `odds_event_id` | column doesn't exist today | Odds API event `id` (new column, this migration) |

**Open question for FBS games where Odds API has the score but ESPN
enrichment fails to match**: same lenient policy as NFL — insert with score/
lines from Odds API, leave quarter-scores/playoffs/game_site NULL. **Open
question for games that only appear on ESPN's `groups=81` broad scoreboard
and have NO Odds API score at all (most FCS games)**: ESPN's own
`competitor.score` field (confirmed available directly on scoreboard/summary
responses, same field used in the original `DELETE_afcon_espn_scoreboard_example.py`
reference) becomes the only score source for these games — this is a new
code path NFL/NBA never needed, since Odds API's `scores` endpoint was
always sufficient there.

## Decisions made during design review

- **Full migration, all 259 teams** (user-confirmed, given the findings above).
- **New migration**: add `ncaaf_games.odds_event_id` (nullable `String(100)`
  + unique constraint), same shape as NBA's.
- **Scope via existing teams roster, not ESPN's group semantics**: pull
  `groups=90` + `groups=81` scoreboard results, filter to games where both
  teams resolve (via a corrected `convert_team_name`) to an existing row in
  `teams WHERE sport='NCAAF'`. Unmatched-team games are silently skipped.
- **Dual-source scores**: Odds API `scores` for games it covers (effectively
  all FBS); ESPN's own `competitor.score` for games Odds API has no line for
  (effectively most FCS games) — this is the one real structural addition
  beyond the NFL/NBA job template.
- **Neutral-site handling**: derive `game_site` from ESPN's `neutralSite`
  flag, same as NFL (not NBA's hardcoded `'home'`).
- **Bundle the team-name mapping fixes into this migration's own task** —
  they block correct matching for both the Odds API and ESPN paths equally.
- **Lenient insert/matching policies**: same as NFL/NBA — never drop a game
  over missing odds or failed ESPN enrichment.
- **The 2026-10-24 data gap is explicitly out of scope** — flagged for
  separate follow-up, not fixed as part of this migration.
- **Go-forward only** — no backfill of existing `ncaaf_games` rows.

## Explicitly out of scope

- NCAAB migration — separate future work.
- The 2026-10-24 ingestion gap — separate follow-up investigation.
- Any UI change.
- Full historical backfill/replace of existing `ncaaf_games` rows.
- Rotating/revoking the SDQL credential.
