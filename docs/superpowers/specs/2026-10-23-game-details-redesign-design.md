# Game Details Page Redesign

## Context

The Game Details page (`pages/GameDetailsPage.tsx` + `components/GameDetails.tsx`)
currently mixes several visual languages: `GameOdds.tsx` (a translucent card with
hardcoded blues), `TrendAnalysisSection.tsx`/`TrendInsightCard.tsx` (a gradient banner
plus a flat list of green/red "tag"-style trend cards with confidence-pill badges),
`PlayerStreaksStrip.tsx` (rows of emoji pills, one per player streak, with "+N more"
chips), and `HistoricalGames.tsx` (MUI tables with win/loss/cover cell colors plus an
info-icon legend tooltip explaining them).

A high-fidelity design handoff (`~/Downloads/design_handoff_game_details/`, option 3a
desktop / 3b mobile in `Game Details.dc.html`, detailed in that folder's `README.md`)
replaces this with a single consistent visual system: white cards with a shared
border/radius/shadow language, team-color identity (a colored circle with the team's
abbreviation, in the team's own brand colors) used in place of plain team names, and
green/red reserved strictly for hit/miss results — not for team identity or for "lean"
indicators, which use the team's own color instead. The redesign is a visual-layer
restyle: section order, data sources, and interactions stay as they are today; only the
presentation changes, plus the two content simplifications below that the handoff's
README calls for explicitly ("those tags were too much" — fewer, denser summary cards
instead of a long flat list of individually-badged trend cards).

The mock is drawn for MLB (pitcher lines, batter/pitcher prop tables), but Game Details
also serves NFL/NBA/NHL/NCAAF/NCAAB today. Per discussion, this redesign's shell applies
to all sports on the page; sport-specific content (pitcher line, which prop columns
exist) stays conditional exactly as it is today, just re-skinned.

## Decisions made during design review

- **Team-color identity only for the 4 pro leagues initially.** A new team-color/abbr
  lookup table (`utils/teamColors.ts`) is hand-populated for MLB/NFL/NBA/NHL (~30-32
  teams each, well-known brand colors). NCAAF (~130 teams) and NCAAB (~180 teams) in
  `teamSlugUtils.ts` are far too many to hand-curate accurately in this pass — they
  render a neutral gray `TeamLogo` (abbreviation, no brand color) until colors are
  supplied separately.
- **Shared components that other pages also use are not edited in place.** `GameOdds`
  (used by `GamesPage`, `TeamPage`) and `HistoricalGames` (used by `TeamPage`,
  `BlogPostPage`) keep their current look everywhere else. New, Game-Details-only
  components (`MatchupOddsCard`, `GameLogTable`) are added instead, reading the same
  data those shared components already consume. `PlayerPropsTable` /
  `MLBPlayerPropsTable` / `NFLPlayerPropsTable` are used only by `GameDetails.tsx`, so
  those are restyled in place.
- **Trend content is simplified, not deleted.** The mock's "Game Trends" (3 cards) +
  "Trend vs. Trend Collision" (1 card) replace today's gradient summary banner, but the
  rest of today's flat trend list (H2H trends not already surfaced by the collision
  card, home/away-venue-specific trends, team streak trends) still renders below, in
  the new card styling, under a plain "More trends" heading. Same logic applies to
  player streaks: the mock's single highlighted streak line sits above the existing
  `PlayerStreaksStrip` (all players, both teams), which stays, restyled.
- **"View all player prop trends" button is rendered but hidden.** No listing page
  exists for it yet; building one is out of scope here. The button's markup/styling
  lands now so turning it on later is a one-line change, but it does not render.
- **Top nav and breadcrumb.** The mock's top nav (dark bar, search, date picker) is a
  different, already-shared nav component (`TabsNavigation.tsx`) and is explicitly out
  of scope — not touched. The breadcrumb ("MLB › Games › Brewers vs Rays") does not
  exist today and is added, as page-specific markup in `GameDetailsPage.tsx`, not a new
  shared component.
- **Styling convention stays inline MUI `sx` with hex values** — matching the rest of
  the codebase (no theme usage, no CSS modules elsewhere) — but the new tokens (colors,
  radii, the team-color table) live in shared constant files so the ~6 new/restyled
  components don't each retype the same values.

## Components

### 1. `utils/teamColors.ts` + `components/TeamLogo.tsx`

`teamColors.ts` exports a lookup keyed by sport (`mlb`/`nfl`/`nba`/`nhl`) → short team
name (same short names `teamNameConverter.ts`/`teamSlugUtils.ts` already produce, e.g.
`"Brewers"`) → `{ primary: string; secondary: string; abbr: string }`. A
`getTeamColors(sport, teamName)` helper returns the looked-up entry or a neutral
fallback (`{ primary: '#4a5361', secondary: '#ffffff', abbr: <first 3 letters
uppercased> }`) for any sport/team not in the table (NCAAF, NCAAB, soccer, unknown
names).

`TeamLogo.tsx` props: `{ sport: string; team: string; size: number }`. Renders a
`Box` circle (`width/height: size`, `borderRadius: '50%'`, `background: primary`,
`color: secondary`, `fontWeight: 800`, centered abbreviation at a font size scaled to
`size`). Pure/presentational, no data fetching — safe to drop in anywhere a team is
rendered, per the "usable everywhere" goal, though only Game Details adopts it in this
pass.

### 2. `components/MatchupOddsCard.tsx`

New component, used only inside `GameDetails.tsx` in place of `<GameOdds game={...}
pitcherData={...} sport={...} />`. Props mirror `GameOddsProps` (`game`, `pitcherData`,
`sport`) minus `detailsLink`/`onViewDetails`/`sx` (not needed on the detail page
itself). Renders the mock's header grid (`1fr auto 1fr`): each side shows a `TeamLogo`
(60px desktop / 44px mobile) + team name (linked via `getTeamPageLink`, same as today)
+ pitcher line (when `pitcherData` has it) + record/ERA/Home-Away meta line; center
shows date/time/venue + a "Scheduled"/score status pill. Below, the 3 odds rows
(moneyline/spread/total) reuse the existing `formatOdds`/`formatH2H`/
`formatOpeningSpread`/`formatOpeningH2H` logic pattern from `GameOdds.tsx` (copied in,
since the two components now diverge visually) — each row keeping the "Opened …"
sub-line and movement indicator already present in `game.opening`.

### 3. `TrendAnalysisSection.tsx` restyle

Same props as today (`gameTrends`, `loading`, `game`, `minTrendLength`,
`dataSinceYear`). Internal structure changes:

1. **3 market cards** (`MarketTrendCard`, new sub-component), one each for
   `gameTrends.marketOverview.moneyline` / `.spread` / `.total`, grid
   `repeat(3, 1fr)` (mobile: same row, gap 8). Each card: title ("Moneyline Trends"
   etc.), big `%` (`Math.round(entry.probability * 100)`), label (`"${entry.lean} win"`
   for moneyline, `"${entry.lean} cover ${spreadPoint}"` for spread — spread point
   comes from `game`'s current line for `entry.lean`'s side, `"Over"/"Under"` for
   total), record computed as `wins = Math.round(entry.probability * entry.sample_size)`
   / `losses = entry.sample_size - wins`, progress bar colored with
   `getTeamColors(sport, entry.lean).primary` (moneyline/spread) or neutral `#4a5361`
   (total). Card only renders for a market whose `marketOverview` entry exists; if none
   exist, the 3-card row doesn't render (same null-handling as today's banner).
2. **Collision card** (`CollisionCard`, new sub-component): takes
   `gameTrends.collisionTrends?.[0]` (already sorted by sample size — see
   `trend_enrichment.py:293`). Needs `home_trend`/`away_trend`/`continuation_rate`
   fields added to the `TrendResult` TS interface in `utils/trendAnalysis.ts` (the API
   already returns them per `_build_collision_entry` in
   `api/services/historical/trend_enrichment.py:168-180`; they're just untyped on the
   frontend today). Renders: icon + "Trend vs. Trend Collision" header, two
   `TeamLogo`s with each side's trend text (derived from `home_trend.type`/`count`/
   `venue` the same way `_collision_phrase` derives it server-side, e.g. `"Won 5
   straight at home"`), a "VS" pill between them, then the split bar
   (`continuation_rate` for `home_trend.team`'s color, remainder in that team's
   secondary color) and `"${sample_size} historical meetings"`. Renders nothing if
   `collisionTrends` is empty.
3. **Remaining trends list**: everything `allTrends` computes today (lines 203-213 of
   current `TrendAnalysisSection.tsx`) minus whatever's already shown in the collision
   card, under a plain `"More trends"` `Typography`, each as today's `TrendDetailCard`
   but restyled: card bg `#fff`, border `#e6e7e3`, radius 16; hit colors `bg #e3f4ea /
   text #14713d`, miss colors `bg #fbe7e7 / text #b42f2f` (replacing `#dcfce7/#16a34a`
   and `#fee2e2/#dc2626`); same progress bar, same prose. The `GameSummaryBanner`
   component is removed (superseded by the 3 market cards).

### 4. Player Prop Trends highlight

New small component (`PlayerStreakHighlight.tsx` or inlined in `GameDetails.tsx`) sits
above the existing `PlayerStreaksStrip` block. Picks the single highest-confidence
streak across both teams' `playerStreaksByTeam` groups (max `continuation_rate`, tying
broken by `sample_size`), and renders: "HOT" pill (`bg #e3f4ea`, `text #14713d`), player
name (link, `#1f5fd6`), `"${streak_count} straight ${label}"`, `"continues
${pct}% (${continued}/${sample_size})"` — all from fields `PlayerStreaksStrip` already
has. Footnote copied verbatim from the mock. "View all player prop trends →" button
renders with `display: 'none'` (see decisions above). `PlayerStreaksStrip` itself keeps
rendering below, restyled to the new card tokens (replacing its emoji-pill look with
flatter rounded chips matching the new borders/colors) but with the same data and
"+N more" behavior.

### 5. `components/GameLogTable.tsx` (Recent Performance tabbed panel)

New component replacing the 7x `<HistoricalGames>` usages inside `GameDetails.tsx`'s
"Recent Performance" tab. Takes the same `HistoricalData`/game-row props
`HistoricalGames` takes today (`title`, `games`, `loading`, `teamName`,
`isHeadToHead`, `sportType`, `sport`) so the calling code in `GameDetails.tsx` barely
changes — only the component name and internal rendering differ. Renders:

- Collapsible header (`#fafbf8` bg): `TeamLogo` (28px; H2H shows both, overlapped -8px,
  2px border), title, summary (`"5-0 · Over 3-2"` computed the same way the existing
  win/loss and O/U derivation already works), chevron (MUI `ExpandMoreIcon`/
  `ExpandLessIcon`, swapped for the mock's custom chevron per the README's note to use
  "the codebase's icon set").
- Fixed-width columns matching the mock (Date 100 · Site 70 · Team 1fr · Runs/Points/
  Goals 90 · Line 80 · Opponent 1fr · Opponent score 110 · Betting Total 120), each
  sport's existing fields (`home_runs`/`home_points`/`home_goals`, etc., per
  `BaseGame`/`MLBGame`/`NFLGame`/`SoccerGame` in `types/gameTypes.ts`) mapped the same
  way `HistoricalGames.tsx` already maps them.
- Team cell: full-cell fill, hit green / miss red (new tokens) instead of today's
  lighter win/loss cell shading — derived the same way (`win = runs > oppRuns`).
  Betting Total cell: full-cell fill for Over/Under, neutral for a push, line on the
  left + `"O · 10"`/`"U · 9"` on the right.
- No info-icon legend tooltip (the mock's full-cell fills are self-explanatory;
  dropping `MoneylineLegend`/`SpreadLegend`/`TotalLegend` usage for this component
  only — `HistoricalGames.tsx` keeps its legend for other pages).
- Desktop default: all 3 tables (team1/team2/H2H) open. Mobile default: only the first
  open, others collapsed, matching the mock's `openTables` state.

The segmented "Last 5 / {Home team} Home Last 5 / {Away team} Away Last 5" control
replaces the current MUI `Tabs` sub-tab UI in `GameDetails.tsx` (same `historicalSubTab`
state, same 3 branches already there) with the mock's segmented-control look (track
`#f1f3ef`, active item white + `0 1px 2px rgba(0,0,0,.12)` shadow).

### 6. Player Props sub-tables

`PlayerPropsTable.tsx` (NBA), `MLBPlayerPropsTable.tsx`, `NFLPlayerPropsTable.tsx` —
each used only by `GameDetails.tsx`, restyled in place to the mock's column layout:
Player · Prop · Streak · Continues · Last 5 (dot strip, 9px dots, `#1f9d55` for a hit).
Each sport's existing per-player fields map to these 5 columns (prop label and streak
direction vary slightly per sport, same as today); no new data needed.

### 7. Breadcrumb

Plain markup added in `GameDetailsPage.tsx` above `MatchupOddsCard`/`GameDetails`:
`"{SPORT} › Games › {away} vs {home}"` (12px, `#5d636b`, last segment `#14171c`/600),
desktop only per the mock (hidden on mobile, matching section 1's "Breadcrumb (desktop
only)" note). Built from data `GameDetailsPage.tsx` already has (sport, team names) —
no new fetch.

## Design tokens

Pulled directly from the handoff README's "Design tokens" section (colors, type scale,
radii, shadows) into a shared `gameDetailsTokens.ts` (or similar) constants file —
not reproduced here in full; implementers should read values straight from
`~/Downloads/design_handoff_game_details/README.md`'s token tables rather than
re-deriving them, since that document is the source of truth for exact hex/px values.
Key values used across multiple components above: card radius 16px, border `#e6e7e3`,
hit `#e3f4ea`/`#14713d`, miss `#fbe7e7`/`#b42f2f`, link/accent `#1f5fd6`, text
`#14171c`/`#5d636b`/`#8a9097`/`#9aa0a6`, `font-variant-numeric: tabular-nums` on all
odds/stat figures.

## Explicitly out of scope

- The top nav (`TabsNavigation.tsx`) and any other page that already renders
  `GameOdds`/`HistoricalGames`/`TeamLogo`-less team names — those keep their current
  look.
- A "view all player prop trends" listing page/route.
- NCAAF/NCAAB team colors (neutral fallback until colors are supplied separately).
- Any change to the trends/collision data model or API responses — this is a
  frontend-only restyle; the one addition is typing 3 already-returned fields on
  `TrendResult` that the frontend didn't previously declare.
- Changing section order, adding/removing sections, or altering what data is fetched.
