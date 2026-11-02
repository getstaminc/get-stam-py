# NCAAB: Switch Games from SDQL to Odds API + ESPN

## Context

NCAAB games currently come from SDQL (`jobs/ncaab_seed_yesterdays_games.py`),
via a hardcoded username/token embedded directly in the job file. This is
the fourth and final SDQL-dependent sport (NFL, NBA, NCAAF already done).

Same two-job hybrid pattern as NCAAF, confirmed by the user: Odds API+ESPN
as primary source, a later-scheduled SDQL job that fills only still-NULL
columns. Two differences from NCAAF, both favorable:

1. **Odds API's D-I coverage is strong here**, unlike NCAAF's FCS gap — a
   real mid-season date (2026-01-15) showed an exact game-count match (49
   Odds-API games vs. 49 DB rows) and 84% of team names matched on first
   pass. The remaining 16% are naming-convention gaps in the existing
   `convert_team_name_ncaab` function (e.g., `"Arkansas St Red Wolves"` vs.
   whatever full-word variant our dict has), the same class of bug already
   fixed twice (NBA, NCAAF), not a structural coverage gap.
2. **The old job already has the orientation-agnostic duplicate guard**
   that NCAAF's old job had and that I failed to carry forward when
   building NCAAF's new fallback job (a real bug caught and fixed during
   NCAAF's final review). This plan carries that guard into NCAAB's new
   fallback job from the start.

**Scope is larger than NCAAF's**, though: `teams WHERE sport='NCAAB'` has
**1,135 rows** — not just Division I (~362 teams) but all divisions (D-I,
D-II, D-III, NAIA). Odds API/ESPN realistically only cover D-I well; the
other ~770 teams depend on the SDQL fallback for essentially all their
data, not just betting lines (this is a bigger share of the roster than
NCAAF's FCS-only gap, though likely a much smaller share of total *rows*,
since lower-division programs play far fewer tracked games).

**Bonus, user-confirmed**: `ncaab_games` already has
`home/away_quarter_scores`, `home/away_first_half_points`,
`home/away_second_half_points`, `home/away_overtime_points` columns in its
schema that the *old* SDQL job never populates at all (SDQL's own NCAABB
query doesn't even fetch quarter/half scores). ESPN enrichment will
populate these for the first time — pure addition, not a parity concern.

## Research findings (live-verified 2026-11-01/02)

- **`ncaab_games.game_site` is `NOT NULL`** (confirmed via
  `information_schema.columns`) — same crash-risk class already hit once
  for NFL and once (in the plan, caught pre-emptively) for NCAAF. This
  plan's job 1 code uses the proven-safe `"neutral" if neutral_site else
  "home"` form from the start.
- **`ncaab_games` has no `odds_event_id` column** — needs a new migration,
  same shape as NBA's/NCAAF's.
- **ESPN scoreboard `groups=50`** is the Division I filter for men's
  college basketball (already used and proven in the existing
  `jobs/send_data_integrity_report.py`, confirmed again live here: 145
  `STATUS_FINAL` events on a real Saturday, all recognizable D-I programs).
  Unlike NCAAF's `groups=81` (which leaked Division II/III/NAIA noise),
  `groups=50` is a clean D-I-only filter — **no second "broad" group is
  needed here**; D-II/D-III/NAIA games are expected to come from SDQL
  fallback only, not discovered via any ESPN group.
- **ESPN linescores are 2 periods (halves), not 4 quarters**: confirmed
  live (`UCF 38+39=77`, `Arizona 41+43=84`, real game 2026-01-17) — each
  entry has `displayValue`, `value` (float), and `period` keys.
  `home/away_first_half_points` map directly to `linescores[0]`/`[1]`
  (no summing, unlike the football sports' 4-quarter-into-2-halves
  pattern); `home/away_overtime_points` map to `linescores[2]` if present
  (index 2, not football's index 4).
- **Odds API NCAAB coverage confirmed strong for D-I**: live historical
  odds for 2026-01-15 returned 49 games exactly matching our DB's 49 rows
  for that date; 82 of 98 team-slots matched via the existing
  `convert_team_name_ncaab` function on first pass.
- **Field-by-field gap check**: every column the old SDQL job writes has a
  confirmed Odds API/ESPN source for D-I games. For non-D-I games, all
  fields come from SDQL (same as the old job, unchanged) via the fallback
  job — no regression, since SDQL remains the only source for those teams
  either way.

| `ncaab_games` column | Old (SDQL) source | New primary source | Fallback (job 2, SDQL) |
|---|---|---|---|
| `home_points`/`away_points` | SDQL | Odds API `scores`; ESPN `competitor.score` if Odds API lacks the game | SDQL fills NULL |
| `home_line`/`away_line` | SDQL | Odds API `spreads` market | SDQL fills NULL |
| `total` | SDQL | Odds API `totals` market `point` | SDQL fills NULL |
| `home_money_line`/`away_money_line` | SDQL | Odds API `h2h` market | SDQL fills NULL |
| `home/away_quarter_scores` | never populated | ESPN `linescores` array, stored as-is per team (new capability) | SDQL has no equivalent — stays NULL if ESPN also missed it |
| `home/away_first_half_points` | never populated | each team's own `linescores[0]` directly (no summing) | same as above |
| `home/away_second_half_points` | never populated | each team's own `linescores[1]` directly (no summing) | same as above |
| `home/away_overtime_points` | never populated | each team's own `linescores[2]` if present, else `None` | same as above |
| `playoffs` | SDQL | ESPN `season.type == 3` | SDQL fills NULL |
| `game_site` (`'home'`/`'neutral'`, NOT NULL) | SDQL | ESPN `neutralSite` flag, `"neutral" if neutral_site else "home"` (never `None`) | SDQL's own `site` field, only if a fresh-insert path is needed |
| `start_time` | fetched by SDQL but never inserted by the old job (dead field) | Odds API `commence_time` (ISO8601 UTC → ET) | not filled by job 2 (old job never populated it either; not a regression) |
| `total_points`, `total_margin` | computed | same computation | recomputed if job 2 supplies points job 1 didn't have |
| `odds_event_id` | column doesn't exist today | Odds API event `id` (new column, this migration) | never set by job 2 |

## Decisions made during design review

- **Two-job hybrid, all 1,135 teams** — same pattern as NCAAF, confirmed by
  the user. Odds API + ESPN primary for D-I; SDQL fallback for everything
  else (the ~770 non-D-I teams depend on it for all fields, not just lines).
- **New migration**: add `ncaab_games.odds_event_id` (nullable
  `String(100)` + unique constraint), same shape as NBA's/NCAAF's.
- **Single ESPN group (`groups=50`, D-I only)** — no second broad-group
  call needed, unlike NCAAF. Scope filtering still happens via our existing
  `teams WHERE sport='NCAAB'` roster (via `convert_team_name_ncaab`), not
  ESPN's group semantics, for consistency with every other sport's design
  — but in practice `groups=50` should already resolve cleanly against our
  D-I subset without the Division-II/III leakage NCAAF's `groups=81` had.
- **Quarter-scores/half-points/OT enrichment is a net-new capability**
  (user-confirmed) — these columns exist unused today; ESPN fills them for
  the first time. First/second-half points come directly from
  `linescores[0]`/`[1]`, not a sum of quarters.
- **Orientation-agnostic duplicate guard preserved from the start** in
  job 2 (the fallback job) — the old job already has this
  (`(home=:a AND away=:b) OR (home=:b AND away=:a)`), and job 2 must
  dedupe SDQL's mirrored neutral-site rows the same way NCAAF's job 2 was
  fixed to do, from the first implementation, not as an after-the-fact fix.
- **`game_site` NOT-NULL-safe from the start**: `"neutral" if neutral_site
  else "home"` in job 1; `game.get('site') or 'home'` on job 2's
  fresh-insert path.
- **Type-safe numeric parsing from the start** in job 2 (money lines,
  spread/total lines) — guard against non-numeric SDQL sentinels
  (`'NL'`, `'-'`, stray floats) with an `isinstance(x, (int, float))`
  check before binding, same fix already applied to NCAAF's job 2.
- **Bundle the `convert_team_name_ncaab` naming fixes into job 1's task** —
  same reasoning as NCAAF: they block correct matching for Odds API
  results against our roster.
- **Lenient insert/matching policies**: same as every prior sport — never
  drop a game over missing odds or failed ESPN enrichment.
- **Scheduling**: same two-job timing pattern as NCAAF — job 1
  (`ncaab_odds_api_seed_yesterdays_games.py`) at ~10:00 AM UTC (4am local);
  job 2 (`ncaab_sdql_fallback_fill.py`) at ~6:00 PM UTC (noon local).
- **Go-forward only** — no backfill of existing `ncaab_games` rows.
- **SDQL is not retired for NCAAB** — same as NCAAF, its role changes from
  primary to fallback; call frequency is unchanged (still fetches the full
  day's games daily).

## Explicitly out of scope

- Any UI change.
- Full historical backfill/replace of existing `ncaab_games` rows.
- Rotating/revoking the SDQL credential.
- Investigating whether any `ncaab_games` dates have a gap analogous to
  NCAAF's 2026-10-24 gap — not checked for this sport, not part of this
  migration's scope.
