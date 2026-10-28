# Game Details Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the Game Details page (matchup/odds card, trend cards, player-streak highlight, recent-performance tables, player-props tables, breadcrumb) to the high-fidelity design handoff in `~/Downloads/design_handoff_game_details/`, and introduce a reusable team-color `TeamLogo` component, without touching components shared with other pages (`GameOdds`, `HistoricalGames`) or changing any data fetching.

**Architecture:** New, Game-Details-only presentational components (`TeamLogo`, `MatchupOddsCard`, `GameLogTable`, `PlayerStreakHighlight`) replace in-place usages inside `GameDetails.tsx`/`GameDetailsPage.tsx`. Components used only by Game Details today (`TrendAnalysisSection`, `PlayerStreaksStrip`, `MLBPlayerPropsTable`, `NFLPlayerPropsTable`, `PlayerPropsTable`) are restyled directly. All new visual constants (colors, radii, team brand colors) live in two shared files (`utils/gameDetailsTokens.ts`, `utils/teamColors.ts`) so no hex value is retyped across components.

**Tech Stack:** React 18 + TypeScript, MUI v7 (`sx` prop styling, no theme usage — matches existing codebase convention), Jest + React Testing Library (`react-scripts test`).

**Spec:** `docs/superpowers/specs/2026-10-23-game-details-redesign-design.md`

## Global Constraints

- Do not modify `GameOdds.tsx` or `HistoricalGames.tsx` — both are rendered on other pages (`GamesPage`, `TeamPage`, `BlogPostPage`) that must keep their current look.
- Styling convention: inline MUI `sx` with literal hex values, pulled from `utils/gameDetailsTokens.ts` / `utils/teamColors.ts` constants — no theme tokens, no CSS modules (matches the rest of the codebase).
- Green/red are reserved for hit/miss results only. Team identity and "lean" bars use the team's own brand color (`utils/teamColors.ts`), never green/red.
- NCAAF and NCAAB teams get the neutral fallback color (`utils/teamColors.ts`'s `NEUTRAL_FALLBACK`) — no hand-curated entries for those two sports in this plan.
- The "View all player prop trends →" button and the chevron ("›") affordances on trend/collision cards render but are **not** links — no destination route exists; do not add one.
- No backend/API changes. The one data-shape change is adding already-returned-but-untyped fields (`home_trend`, `away_trend`) to the frontend `TrendResult` TypeScript interface (Task 4).
- Test runner: `CI=true npx react-scripts test <relative/path/to/File.test.tsx> --watchAll=false` from `getstam-react/`.

---

## Task 1: Shared design tokens, team colors, and `TeamLogo`

**Files:**
- Create: `getstam-react/src/utils/gameDetailsTokens.ts`
- Create: `getstam-react/src/utils/teamColors.ts`
- Create: `getstam-react/src/components/TeamLogo.tsx`
- Test: `getstam-react/src/components/TeamLogo.test.tsx`

**Interfaces:**
- Produces: `gameDetailsTokens` (default export, `const` object) — fields used by later tasks: `cardBg`, `cardBorder`, `cardRadius`, `tableRadius`, `subtlePanelBg`, `chipTrackBg`, `trackBg2`, `borders.light`, `borders.lighter`, `text.primary` / `.secondary` / `.tertiary` / `.muted`, `link`, `linkHover`, `collisionIcon`, `hit.bg` / `.text` / `.dot`, `miss.bg` / `.text`, `neutralBar`, `shadowHover`, `shadowActiveSegment`.
- Produces: `getTeamColors(dbSport: string, teamName: string): { primary: string; secondary: string; abbr: string }` from `utils/teamColors.ts`.
- Produces: `TeamLogo` component, props `{ sportKey: string; teamName: string; size: number; border?: string }`, default export from `components/TeamLogo.tsx`.
- Consumes: `convertTeamNameBySport` (`utils/teamNameConverter.ts`, existing), `getSportType` (`types/gameTypes.ts`, existing).

- [ ] **Step 1: Write the failing test for `getTeamColors`**

Create `getstam-react/src/utils/teamColors.test.ts`:

```ts
import { getTeamColors } from './teamColors';

describe('getTeamColors', () => {
  it('returns the known entry for an MLB team', () => {
    expect(getTeamColors('mlb', 'Brewers')).toEqual({ primary: '#13294B', secondary: '#FFC52F', abbr: 'MIL' });
    expect(getTeamColors('mlb', 'Rays')).toEqual({ primary: '#092C5C', secondary: '#8FBCE6', abbr: 'TB' });
  });

  it('falls back to a neutral gray entry for an unknown sport/team', () => {
    expect(getTeamColors('ncaaf', 'Michigan Wolverines')).toEqual({
      primary: '#4a5361',
      secondary: '#ffffff',
      abbr: 'MIC',
    });
  });

  it('falls back for a known sport with an unrecognized team name', () => {
    const result = getTeamColors('mlb', 'Totally Made Up Team');
    expect(result.primary).toBe('#4a5361');
    expect(result.secondary).toBe('#ffffff');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/utils/teamColors.test.ts --watchAll=false`
Expected: FAIL — `Cannot find module './teamColors'`

- [ ] **Step 3: Write `utils/gameDetailsTokens.ts`**

```ts
// Shared design tokens for the Game Details page redesign.
// Source of truth for exact values: the design handoff README
// (~/Downloads/design_handoff_game_details/README.md, "Design tokens" section).
export const gameDetailsTokens = {
  cardBg: '#ffffff',
  cardBorder: '#e6e7e3',
  cardRadius: 16,
  tableRadius: 12,
  subtlePanelBg: '#fafbf8',
  chipTrackBg: '#f1f3ef',
  trackBg2: '#eceee9',
  borders: {
    light: '#f1f2ee',
    lighter: '#f4f5f2',
  },
  text: {
    primary: '#14171c',
    secondary: '#5d636b',
    tertiary: '#8a9097',
    muted: '#9aa0a6',
  },
  link: '#1f5fd6',
  linkHover: '#163f8f',
  collisionIcon: '#5b3fd6',
  hit: {
    bg: '#e3f4ea',
    text: '#14713d',
    dot: '#1f9d55',
  },
  miss: {
    bg: '#fbe7e7',
    text: '#b42f2f',
  },
  neutralBar: '#4a5361',
  shadowHover: '0 4px 14px rgba(0,0,0,.06)',
  shadowActiveSegment: '0 1px 2px rgba(0,0,0,.12)',
};

export default gameDetailsTokens;
```

- [ ] **Step 4: Write `utils/teamColors.ts`**

```ts
// Team brand colors for the TeamLogo component. Keys are the SHORT team names
// already produced by utils/teamNameConverter.ts / utils/teamSlugUtils.ts
// (e.g. "Brewers", not "Milwaukee Brewers"). Only the 4 pro leagues are
// hand-curated here — NCAAF/NCAAB (hundreds of schools) fall back to the
// neutral entry until colors are supplied separately.

export interface TeamColorEntry {
  primary: string;
  secondary: string;
  abbr: string;
}

export const NEUTRAL_FALLBACK = { primary: '#4a5361', secondary: '#ffffff' };

const MLB_COLORS: Record<string, TeamColorEntry> = {
  Diamondbacks: { primary: '#A71930', secondary: '#E3D4AD', abbr: 'ARI' },
  Braves: { primary: '#13274F', secondary: '#FFFFFF', abbr: 'ATL' },
  Orioles: { primary: '#DF4601', secondary: '#000000', abbr: 'BAL' },
  'Red Sox': { primary: '#BD3039', secondary: '#FFFFFF', abbr: 'BOS' },
  Cubs: { primary: '#0E3386', secondary: '#FFFFFF', abbr: 'CHC' },
  'White Sox': { primary: '#27251F', secondary: '#C4CED4', abbr: 'CWS' },
  Reds: { primary: '#C6011F', secondary: '#FFFFFF', abbr: 'CIN' },
  Guardians: { primary: '#0C2340', secondary: '#FFFFFF', abbr: 'CLE' },
  Rockies: { primary: '#333366', secondary: '#C4CED4', abbr: 'COL' },
  Tigers: { primary: '#0C2340', secondary: '#FA4616', abbr: 'DET' },
  Astros: { primary: '#002D62', secondary: '#EB6E1F', abbr: 'HOU' },
  Royals: { primary: '#004687', secondary: '#BD9B60', abbr: 'KC' },
  Angels: { primary: '#BA0021', secondary: '#FFFFFF', abbr: 'LAA' },
  Dodgers: { primary: '#005A9C', secondary: '#FFFFFF', abbr: 'LAD' },
  Marlins: { primary: '#00A3E0', secondary: '#FFFFFF', abbr: 'MIA' },
  Brewers: { primary: '#13294B', secondary: '#FFC52F', abbr: 'MIL' },
  Twins: { primary: '#002B5C', secondary: '#FFFFFF', abbr: 'MIN' },
  Mets: { primary: '#002D72', secondary: '#FF5910', abbr: 'NYM' },
  Yankees: { primary: '#0C2340', secondary: '#FFFFFF', abbr: 'NYY' },
  Athletics: { primary: '#003831', secondary: '#EFB21E', abbr: 'ATH' },
  Phillies: { primary: '#E81828', secondary: '#FFFFFF', abbr: 'PHI' },
  Pirates: { primary: '#27251F', secondary: '#FDB827', abbr: 'PIT' },
  Padres: { primary: '#2F241D', secondary: '#FFC425', abbr: 'SD' },
  Giants: { primary: '#27251F', secondary: '#FD5A1E', abbr: 'SF' },
  Mariners: { primary: '#0C2C56', secondary: '#C4CED4', abbr: 'SEA' },
  Cardinals: { primary: '#C41E3A', secondary: '#FFFFFF', abbr: 'STL' },
  Rays: { primary: '#092C5C', secondary: '#8FBCE6', abbr: 'TB' },
  Rangers: { primary: '#003278', secondary: '#FFFFFF', abbr: 'TEX' },
  'Blue Jays': { primary: '#134A8E', secondary: '#FFFFFF', abbr: 'TOR' },
  Nationals: { primary: '#14225A', secondary: '#FFFFFF', abbr: 'WSH' },
};

const NFL_COLORS: Record<string, TeamColorEntry> = {
  Cardinals: { primary: '#97233F', secondary: '#FFFFFF', abbr: 'ARI' },
  Falcons: { primary: '#A71930', secondary: '#FFFFFF', abbr: 'ATL' },
  Ravens: { primary: '#241773', secondary: '#9E7C0C', abbr: 'BAL' },
  Bills: { primary: '#00338D', secondary: '#FFFFFF', abbr: 'BUF' },
  Panthers: { primary: '#0085CA', secondary: '#FFFFFF', abbr: 'CAR' },
  Bears: { primary: '#0B162A', secondary: '#C83803', abbr: 'CHI' },
  Bengals: { primary: '#FB4F14', secondary: '#000000', abbr: 'CIN' },
  Browns: { primary: '#311D00', secondary: '#FF3C00', abbr: 'CLE' },
  Cowboys: { primary: '#041E42', secondary: '#869397', abbr: 'DAL' },
  Broncos: { primary: '#002244', secondary: '#FB4F14', abbr: 'DEN' },
  Lions: { primary: '#0076B6', secondary: '#B0B7BC', abbr: 'DET' },
  Packers: { primary: '#203731', secondary: '#FFB612', abbr: 'GB' },
  Texans: { primary: '#03202F', secondary: '#FFFFFF', abbr: 'HOU' },
  Colts: { primary: '#002C5F', secondary: '#A2AAAD', abbr: 'IND' },
  Jaguars: { primary: '#101820', secondary: '#D7A22A', abbr: 'JAX' },
  Chiefs: { primary: '#E31837', secondary: '#FFB81C', abbr: 'KC' },
  Raiders: { primary: '#000000', secondary: '#A5ACAF', abbr: 'LV' },
  Chargers: { primary: '#0080C6', secondary: '#FFC20E', abbr: 'LAC' },
  Rams: { primary: '#003594', secondary: '#FFA300', abbr: 'LAR' },
  Dolphins: { primary: '#008E97', secondary: '#FC4C02', abbr: 'MIA' },
  Vikings: { primary: '#4F2683', secondary: '#FFC62F', abbr: 'MIN' },
  Patriots: { primary: '#002244', secondary: '#FFFFFF', abbr: 'NE' },
  Saints: { primary: '#101820', secondary: '#D3BC8D', abbr: 'NO' },
  Giants: { primary: '#0B2265', secondary: '#FFFFFF', abbr: 'NYG' },
  Jets: { primary: '#125740', secondary: '#FFFFFF', abbr: 'NYJ' },
  Eagles: { primary: '#004C54', secondary: '#A5ACAF', abbr: 'PHI' },
  Steelers: { primary: '#101820', secondary: '#FFB612', abbr: 'PIT' },
  Fortyniners: { primary: '#AA0000', secondary: '#B3995D', abbr: 'SF' },
  Seahawks: { primary: '#002244', secondary: '#69BE28', abbr: 'SEA' },
  Buccaneers: { primary: '#D50A0A', secondary: '#FFFFFF', abbr: 'TB' },
  Titans: { primary: '#0C2340', secondary: '#4B92DB', abbr: 'TEN' },
  Commanders: { primary: '#5A1414', secondary: '#FFB612', abbr: 'WAS' },
};

const NBA_COLORS: Record<string, TeamColorEntry> = {
  Hawks: { primary: '#E03A3E', secondary: '#C1D32F', abbr: 'ATL' },
  Celtics: { primary: '#007A33', secondary: '#BA9653', abbr: 'BOS' },
  Nets: { primary: '#000000', secondary: '#FFFFFF', abbr: 'BKN' },
  Hornets: { primary: '#1D1160', secondary: '#00788C', abbr: 'CHA' },
  Bulls: { primary: '#CE1141', secondary: '#FFFFFF', abbr: 'CHI' },
  Cavaliers: { primary: '#6F263D', secondary: '#FFB81C', abbr: 'CLE' },
  Mavericks: { primary: '#00538C', secondary: '#B8C4CA', abbr: 'DAL' },
  Nuggets: { primary: '#0E2240', secondary: '#FEC524', abbr: 'DEN' },
  Pistons: { primary: '#C8102E', secondary: '#FFFFFF', abbr: 'DET' },
  Warriors: { primary: '#1D428A', secondary: '#FFC72C', abbr: 'GSW' },
  Rockets: { primary: '#CE1141', secondary: '#FFFFFF', abbr: 'HOU' },
  Pacers: { primary: '#002D62', secondary: '#FDBB30', abbr: 'IND' },
  Clippers: { primary: '#1D428A', secondary: '#FFFFFF', abbr: 'LAC' },
  Lakers: { primary: '#552583', secondary: '#FDB927', abbr: 'LAL' },
  Grizzlies: { primary: '#12173F', secondary: '#F5B112', abbr: 'MEM' },
  Heat: { primary: '#98002E', secondary: '#F9A01B', abbr: 'MIA' },
  Bucks: { primary: '#00471B', secondary: '#EEE1C6', abbr: 'MIL' },
  Timberwolves: { primary: '#0C2340', secondary: '#78BE20', abbr: 'MIN' },
  Pelicans: { primary: '#0C2340', secondary: '#85714D', abbr: 'NOP' },
  Knicks: { primary: '#006BB6', secondary: '#F58426', abbr: 'NYK' },
  Thunder: { primary: '#007AC1', secondary: '#EF3B24', abbr: 'OKC' },
  Magic: { primary: '#0077C0', secondary: '#C4CED4', abbr: 'ORL' },
  Seventysixers: { primary: '#006BB6', secondary: '#FFFFFF', abbr: 'PHI' },
  Suns: { primary: '#1D1160', secondary: '#E56020', abbr: 'PHX' },
  Trailblazers: { primary: '#000000', secondary: '#E03A3E', abbr: 'POR' },
  Kings: { primary: '#5A2D81', secondary: '#63727A', abbr: 'SAC' },
  Spurs: { primary: '#000000', secondary: '#C4CED4', abbr: 'SAS' },
  Raptors: { primary: '#CE1141', secondary: '#FFFFFF', abbr: 'TOR' },
  Jazz: { primary: '#002B5C', secondary: '#F9A01B', abbr: 'UTA' },
  Wizards: { primary: '#002B5C', secondary: '#FFFFFF', abbr: 'WAS' },
};

const NHL_COLORS: Record<string, TeamColorEntry> = {
  Ducks: { primary: '#F47A38', secondary: '#000000', abbr: 'ANA' },
  Coyotes: { primary: '#8C2633', secondary: '#E2D6B5', abbr: 'ARI' },
  Bruins: { primary: '#000000', secondary: '#FFB81C', abbr: 'BOS' },
  Sabres: { primary: '#002654', secondary: '#FCB514', abbr: 'BUF' },
  Flames: { primary: '#C8102E', secondary: '#F1BE48', abbr: 'CGY' },
  Hurricanes: { primary: '#CC0000', secondary: '#FFFFFF', abbr: 'CAR' },
  Blackhawks: { primary: '#000000', secondary: '#CF0A2C', abbr: 'CHI' },
  Avalanche: { primary: '#6F263D', secondary: '#A2AAAD', abbr: 'COL' },
  'Blue Jackets': { primary: '#002654', secondary: '#FFFFFF', abbr: 'CBJ' },
  Stars: { primary: '#006847', secondary: '#8F8F8C', abbr: 'DAL' },
  'Red Wings': { primary: '#CE1126', secondary: '#FFFFFF', abbr: 'DET' },
  Oilers: { primary: '#041E42', secondary: '#FF4C00', abbr: 'EDM' },
  Panthers: { primary: '#C8102E', secondary: '#B9975B', abbr: 'FLA' },
  Kings: { primary: '#111111', secondary: '#A2AAAD', abbr: 'LAK' },
  Wild: { primary: '#154734', secondary: '#DDCBA4', abbr: 'MIN' },
  Canadiens: { primary: '#AF1E2D', secondary: '#FFFFFF', abbr: 'MTL' },
  Predators: { primary: '#041E42', secondary: '#FFB81C', abbr: 'NSH' },
  Devils: { primary: '#CE1126', secondary: '#FFFFFF', abbr: 'NJD' },
  Islanders: { primary: '#00539B', secondary: '#F47D30', abbr: 'NYI' },
  Rangers: { primary: '#0038A8', secondary: '#FFFFFF', abbr: 'NYR' },
  Senators: { primary: '#C52032', secondary: '#C2912C', abbr: 'OTT' },
  Flyers: { primary: '#F74902', secondary: '#000000', abbr: 'PHI' },
  Penguins: { primary: '#000000', secondary: '#FCB514', abbr: 'PIT' },
  Sharks: { primary: '#006D75', secondary: '#EA7200', abbr: 'SJS' },
  Kraken: { primary: '#001628', secondary: '#99D9D9', abbr: 'SEA' },
  Blues: { primary: '#002F87', secondary: '#FCB514', abbr: 'STL' },
  Lightning: { primary: '#002868', secondary: '#FFFFFF', abbr: 'TBL' },
  'Maple Leafs': { primary: '#00205B', secondary: '#FFFFFF', abbr: 'TOR' },
  Mammoth: { primary: '#0F0F0F', secondary: '#71C5E8', abbr: 'UTA' },
  Canucks: { primary: '#00205B', secondary: '#00843D', abbr: 'VAN' },
  Knights: { primary: '#333F42', secondary: '#B4975A', abbr: 'VGK' },
  Capitals: { primary: '#041E42', secondary: '#FFFFFF', abbr: 'WSH' },
  Jets: { primary: '#041E42', secondary: '#FFFFFF', abbr: 'WPG' },
};

const COLOR_TABLES: Record<string, Record<string, TeamColorEntry>> = {
  mlb: MLB_COLORS,
  nfl: NFL_COLORS,
  nba: NBA_COLORS,
  nhl: NHL_COLORS,
};

export function getTeamColors(dbSport: string, teamName: string): TeamColorEntry {
  const table = COLOR_TABLES[dbSport];
  const entry = table?.[teamName];
  if (entry) return entry;

  const abbr = (teamName || '').replace(/[^A-Za-z]/g, '').slice(0, 3).toUpperCase() || '?';
  return { ...NEUTRAL_FALLBACK, abbr };
}
```

- [ ] **Step 5: Run test to verify `getTeamColors` passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/utils/teamColors.test.ts --watchAll=false`
Expected: PASS

- [ ] **Step 6: Write the failing test for `TeamLogo`**

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import TeamLogo from './TeamLogo';

describe('TeamLogo', () => {
  it('renders the team abbreviation in its brand colors', () => {
    render(<TeamLogo sportKey="baseball_mlb" teamName="Milwaukee Brewers" size={60} />);
    const logo = screen.getByText('MIL');
    expect(logo).toBeInTheDocument();
    expect(logo).toHaveStyle({ backgroundColor: '#13294B', color: '#FFC52F' });
  });

  it('falls back to a neutral abbreviation circle for an unrecognized team', () => {
    render(<TeamLogo sportKey="basketball_ncaab" teamName="Some College Team" size={40} />);
    const logo = screen.getByText('SOM');
    expect(logo).toHaveStyle({ backgroundColor: '#4a5361' });
  });
});
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TeamLogo.test.tsx --watchAll=false`
Expected: FAIL — `Cannot find module './TeamLogo'`

- [ ] **Step 8: Write `components/TeamLogo.tsx`**

```tsx
import React from 'react';
import { Box } from '@mui/material';
import { convertTeamNameBySport } from '../utils/teamNameConverter';
import { getSportType } from '../types/gameTypes';
import { getTeamColors } from '../utils/teamColors';

interface TeamLogoProps {
  // Odds-API-style ("baseball_mlb") or short db-style ("mlb") sport key — both work,
  // since convertTeamNameBySport/getSportType already support either.
  sportKey: string;
  // Full odds-API team name ("Milwaukee Brewers") or an already-short name
  // ("Brewers") — convertTeamNameBySport passes short names through unchanged.
  teamName: string;
  size: number;
  border?: string;
}

const TeamLogo: React.FC<TeamLogoProps> = ({ sportKey, teamName, size, border }) => {
  const dbSport = getSportType(sportKey);
  const shortName = convertTeamNameBySport(sportKey, teamName);
  const { primary, secondary, abbr } = getTeamColors(dbSport, shortName);

  return (
    <Box
      sx={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: '50%',
        display: 'grid',
        placeItems: 'center',
        backgroundColor: primary,
        color: secondary,
        fontWeight: 800,
        fontSize: Math.round(size * 0.3),
        border,
      }}
    >
      {abbr}
    </Box>
  );
};

export default TeamLogo;
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TeamLogo.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
cd getstam-react && git add src/utils/gameDetailsTokens.ts src/utils/teamColors.ts src/utils/teamColors.test.ts src/components/TeamLogo.tsx src/components/TeamLogo.test.tsx
git commit -m "$(cat <<'EOF'
Add shared design tokens, team color table, and TeamLogo component

Foundational pieces for the Game Details redesign: a team-color
lookup for the 4 pro leagues and a reusable colored-circle team logo,
plus the new design's shared hex/radius/shadow constants.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `MatchupOddsCard`

**Files:**
- Create: `getstam-react/src/components/MatchupOddsCard.tsx`
- Test: `getstam-react/src/components/MatchupOddsCard.test.tsx`

**Interfaces:**
- Consumes: `TeamLogo` (Task 1), `gameDetailsTokens` (Task 1), `GameWithDraw`/`TeamOdds`/`TotalsData` (`types/gameTypes.ts`, existing), `getTeamPageLink` (`utils/teamSlugUtils.ts`, existing).
- Produces: `MatchupOddsCard` component, props `{ game: GameWithDraw; pitcherData?: { home_pitcher?: string; away_pitcher?: string; home_pitcher_stats?: string; away_pitcher_stats?: string }; sport?: string }`, default export. This is the only consumer; `GameOdds.tsx` itself is untouched (Global Constraints).

- [ ] **Step 1: Write the failing test**

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MatchupOddsCard from './MatchupOddsCard';
import { GameWithDraw } from '../types/gameTypes';

const game: GameWithDraw = {
  game_id: 'evt1',
  commence_time: '2026-10-24T23:10:00Z',
  completed: false,
  home: { team: 'Milwaukee Brewers', score: null, odds: { h2h: -187, spread_point: -1.5, spread_price: 129 }, record: { wins: 16, losses: 5, ties: 0 } },
  away: { team: 'Tampa Bay Rays', score: null, odds: { h2h: 154, spread_point: 1.5, spread_price: -156 }, record: { wins: 15, losses: 6, ties: 0 } },
  totals: { over_point: 7.5, over_price: -110, under_point: 7.5, under_price: -110 },
};

function renderCard() {
  return render(
    <MemoryRouter>
      <MatchupOddsCard game={game} sport="mlb" pitcherData={{ home_pitcher: 'J. Misiorowski', away_pitcher: 'N. Martinez' }} />
    </MemoryRouter>
  );
}

describe('MatchupOddsCard', () => {
  it('shows each team name, a TeamLogo abbreviation, and the pitcher line', () => {
    renderCard();
    expect(screen.getByText('Milwaukee Brewers')).toBeInTheDocument();
    expect(screen.getByText('Tampa Bay Rays')).toBeInTheDocument();
    expect(screen.getByText('MIL')).toBeInTheDocument();
    expect(screen.getByText('TB')).toBeInTheDocument();
    expect(screen.getByText('J. Misiorowski')).toBeInTheDocument();
    expect(screen.getByText('N. Martinez')).toBeInTheDocument();
  });

  it('shows the moneyline, spread, and total odds rows', () => {
    renderCard();
    expect(screen.getByText('-187')).toBeInTheDocument();
    expect(screen.getByText('+154')).toBeInTheDocument();
    expect(screen.getByText('-1.5 (+129)')).toBeInTheDocument();
    expect(screen.getByText('Over +7.5 (-110)')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/MatchupOddsCard.test.tsx --watchAll=false`
Expected: FAIL — `Cannot find module './MatchupOddsCard'`

- [ ] **Step 3: Write `components/MatchupOddsCard.tsx`**

```tsx
import React from 'react';
import { Link } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import { GameWithDraw } from '../types/gameTypes';
import { getTeamPageLink } from '../utils/teamSlugUtils';
import TeamLogo from './TeamLogo';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';

interface MatchupOddsCardProps {
  game: GameWithDraw;
  pitcherData?: {
    home_pitcher?: string;
    away_pitcher?: string;
    home_pitcher_stats?: string;
    away_pitcher_stats?: string;
  };
  sport?: string;
}

const formatH2H = (h2h: number | null | undefined): string => {
  if (h2h === null || h2h === undefined) return 'N/A';
  return `${h2h > 0 ? '+' : ''}${h2h}`;
};

const formatOdds = (point: number | null, price: number | null): string => {
  if (point === null && price === null) return 'N/A';
  if (point === null) return price !== null ? `${price > 0 ? '+' : ''}${price}` : 'N/A';
  const pointStr = `${point > 0 ? '+' : ''}${point}`;
  if (price === null) return pointStr;
  return `${pointStr} (${price > 0 ? '+' : ''}${price})`;
};

const formatOpeningPoint = (point: number | null | undefined): string | null => {
  if (point === null || point === undefined) return null;
  return `${point > 0 ? '+' : ''}${point}`;
};

const formatRecord = (record?: { wins: number; losses: number; ties: number }): string | null => {
  if (!record) return null;
  const { wins, losses, ties } = record;
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
};

const MatchupOddsCard: React.FC<MatchupOddsCardProps> = ({ game, pitcherData, sport }) => {
  const { home, away, totals, draw, opening } = game as GameWithDraw;
  const hasScore = home.score !== null && home.score !== undefined && away.score !== null && away.score !== undefined;
  const statusLabel = hasScore ? `${home.score} - ${away.score}` : 'Scheduled';
  const sportKeyForLogo = sport || 'mlb';

  const commenceDate = game.commence_time ? new Date(game.commence_time as string) : null;
  const dateLabel = commenceDate
    ? commenceDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : null;
  const timeLabel = commenceDate
    ? commenceDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    : null;

  const TeamHeader: React.FC<{ side: 'home' | 'away' }> = ({ side }) => {
    const team = side === 'home' ? home : away;
    const pitcher = side === 'home' ? pitcherData?.home_pitcher : pitcherData?.away_pitcher;
    const pitcherStats = side === 'home' ? pitcherData?.home_pitcher_stats : pitcherData?.away_pitcher_stats;
    const record = formatRecord(team.record);
    const metaParts = [record, pitcherStats, side === 'home' ? 'Home' : 'Away'].filter(Boolean);

    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          justifyContent: side === 'away' ? 'flex-end' : 'flex-start',
          textAlign: side === 'away' ? 'right' : 'left',
          flexDirection: side === 'away' ? 'row-reverse' : 'row',
        }}
      >
        <TeamLogo sportKey={sportKeyForLogo} teamName={team.team} size={60} />
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <Typography sx={{ fontSize: '1.25rem', fontWeight: 700 }}>
            {sport ? (
              <Link to={getTeamPageLink(sport, team.team)} style={{ textDecoration: 'none', color: 'inherit' }}>
                {team.team}
              </Link>
            ) : (
              team.team
            )}
          </Typography>
          {pitcher && (
            <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600, color: tokens.link }}>{pitcher}</Typography>
          )}
          {metaParts.length > 0 && (
            <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary }}>
              {metaParts.join(' · ')}
            </Typography>
          )}
        </Box>
      </Box>
    );
  };

  const OddsRow: React.FC<{
    label: string;
    homeValue: string;
    awayValue: string;
    homeOpened?: string | null;
    awayOpened?: string | null;
    centerExtra?: React.ReactNode;
  }> = ({ label, homeValue, awayValue, homeOpened, awayOpened, centerExtra }) => (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr 76px 1fr', sm: '1fr 140px 1fr' },
        gap: 1,
        alignItems: 'center',
        px: { xs: 2, sm: 3 },
        py: 1.5,
        borderTop: `1px solid ${tokens.borders.light}`,
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      <Box>
        <Typography sx={{ fontSize: { xs: '0.875rem', sm: '1.0625rem' }, fontWeight: 700 }}>{homeValue}</Typography>
        {homeOpened && (
          <Typography sx={{ fontSize: { xs: '0.625rem', sm: '0.75rem' }, color: tokens.text.tertiary }}>
            Opened {homeOpened}
          </Typography>
        )}
      </Box>
      <Box sx={{ textAlign: 'center' }}>
        <Typography
          sx={{
            fontSize: { xs: '0.5625rem', sm: '0.6875rem' },
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: tokens.text.secondary,
          }}
        >
          {label}
        </Typography>
        {centerExtra}
      </Box>
      <Box sx={{ textAlign: 'right' }}>
        <Typography sx={{ fontSize: { xs: '0.875rem', sm: '1.0625rem' }, fontWeight: 700 }}>{awayValue}</Typography>
        {awayOpened && (
          <Typography sx={{ fontSize: { xs: '0.625rem', sm: '0.75rem' }, color: tokens.text.tertiary }}>
            Opened {awayOpened}
          </Typography>
        )}
      </Box>
    </Box>
  );

  return (
    <Box sx={{ bgcolor: tokens.cardBg, border: `1px solid ${tokens.cardBorder}`, borderRadius: `${tokens.cardRadius}px`, overflow: 'hidden' }}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr auto 1fr' },
          gap: 3,
          alignItems: 'center',
          px: { xs: 2, sm: 3 },
          py: 2.5,
        }}
      >
        <TeamHeader side="home" />
        <Box sx={{ textAlign: 'center', px: 1 }}>
          {dateLabel && <Typography sx={{ fontSize: '0.9375rem', fontWeight: 700 }}>{dateLabel}</Typography>}
          {timeLabel && !hasScore && <Typography sx={{ fontSize: '0.875rem', color: tokens.text.secondary }}>{timeLabel}</Typography>}
          <Typography
            sx={{
              display: 'inline-block',
              mt: 0.5,
              fontSize: '0.6875rem',
              fontWeight: 700,
              px: '9px',
              py: '4px',
              borderRadius: '999px',
              bgcolor: tokens.chipTrackBg,
              color: tokens.text.secondary,
            }}
          >
            {statusLabel}
          </Typography>
        </Box>
        <TeamHeader side="away" />
      </Box>

      {!hasScore && (
        <Box>
          <OddsRow
            label="H2H"
            homeValue={formatH2H(home.odds?.h2h)}
            awayValue={formatH2H(away.odds?.h2h)}
            homeOpened={opening ? formatOpeningPoint(opening.home.h2h) : null}
            awayOpened={opening ? formatOpeningPoint(opening.away.h2h) : null}
            centerExtra={
              draw?.h2h != null ? (
                <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600, mt: 0.25 }}>Draw {formatH2H(draw.h2h)}</Typography>
              ) : null
            }
          />
          <OddsRow
            label="Spread"
            homeValue={formatOdds(home.odds?.spread_point ?? null, home.odds?.spread_price ?? null)}
            awayValue={formatOdds(away.odds?.spread_point ?? null, away.odds?.spread_price ?? null)}
            homeOpened={opening ? formatOpeningPoint(opening.home.spread_point) : null}
            awayOpened={opening ? formatOpeningPoint(opening.away.spread_point) : null}
          />
          <OddsRow
            label="Total"
            homeValue={totals?.over_point != null ? `Over ${formatOdds(totals.over_point, totals.over_price ?? null)}` : 'N/A'}
            awayValue={totals?.under_point != null ? `Under ${formatOdds(totals.under_point, totals.under_price ?? null)}` : 'N/A'}
            homeOpened={opening && opening.totals.over_point != null ? `Over ${formatOpeningPoint(opening.totals.over_point)}` : null}
            awayOpened={opening && opening.totals.under_point != null ? `Under ${formatOpeningPoint(opening.totals.under_point)}` : null}
          />
        </Box>
      )}
    </Box>
  );
};

export default MatchupOddsCard;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/MatchupOddsCard.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd getstam-react && git add src/components/MatchupOddsCard.tsx src/components/MatchupOddsCard.test.tsx
git commit -m "$(cat <<'EOF'
Add MatchupOddsCard for the Game Details redesign

A Game-Details-only matchup/odds card matching the new design,
built alongside (not instead of) GameOdds, which stays unchanged for
GamesPage/TeamPage.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Game Trends — 3 market cards

**Files:**
- Modify: `getstam-react/src/components/TrendAnalysisSection.tsx`
- Test: Create `getstam-react/src/components/TrendAnalysisSection.test.tsx`

**Interfaces:**
- Consumes: `TeamLogo`, `gameDetailsTokens`, `getTeamColors` (Task 1); `convertTeamNameBySport`, `getSportType` (existing).
- Produces: `TrendAnalysisSectionProps` gains a new optional prop `sportKey?: string` (default `'baseball_mlb'` when omitted, so the component is testable/renderable standalone before `GameDetailsPage.tsx` is updated to pass the real value in Task 12). `MarketTrendCard` becomes an internal (non-exported) sub-component.
- Removes: `GameSummaryBanner` component and its usage (superseded by the 3 cards).

- [ ] **Step 1: Write the failing test**

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import TrendAnalysisSection from './TrendAnalysisSection';
import { GameWithTrends } from '../utils/trendAnalysis';

const game = {
  home: { team: 'Milwaukee Brewers', score: null, odds: { spread_point: -1.5 } },
  away: { team: 'Tampa Bay Rays', score: null, odds: { spread_point: 1.5 } },
  totals: {},
};

const gameTrends: GameWithTrends = {
  game,
  homeTeamTrends: [],
  awayTeamTrends: [],
  headToHeadTrends: [],
  marketOverview: {
    moneyline: { lean: 'Milwaukee Brewers', probability: 0.64, trend_count: 1, sample_size: 25, supporting_description: '' },
    spread: { lean: 'Milwaukee Brewers', probability: 0.58, trend_count: 1, sample_size: 24, supporting_description: '' },
    total: { lean: 'Over', probability: 0.6, trend_count: 1, sample_size: 20, supporting_description: '' },
  },
  hasTrends: true,
};

describe('TrendAnalysisSection market cards', () => {
  it('renders a card per market with percent, label, and W-L record', () => {
    render(
      <TrendAnalysisSection gameTrends={gameTrends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );

    expect(screen.getByText('Moneyline Trends')).toBeInTheDocument();
    expect(screen.getByText('64%')).toBeInTheDocument();
    expect(screen.getByText('Milwaukee Brewers win')).toBeInTheDocument();
    expect(screen.getByText('16-9 (25 games)')).toBeInTheDocument();

    expect(screen.getByText('Spread Trends')).toBeInTheDocument();
    expect(screen.getByText('Milwaukee Brewers cover -1.5')).toBeInTheDocument();

    expect(screen.getByText('Total Trends')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText('Over')).toBeInTheDocument();
  });

  it('no longer renders the old "What the numbers suggest" banner', () => {
    render(
      <TrendAnalysisSection gameTrends={gameTrends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );
    expect(screen.queryByText('What the numbers suggest')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TrendAnalysisSection.test.tsx --watchAll=false`
Expected: FAIL — "Moneyline Trends" text not found (banner still renders "What the numbers suggest" and old market copy)

- [ ] **Step 3: Replace `GameSummaryBanner` with `MarketTrendCard` in `TrendAnalysisSection.tsx`**

Remove the `MARKET_PLAIN_LABELS`, `COIN_FLIP_THRESHOLD`, `marketSentence`, and `GameSummaryBanner` definitions (lines 119–184 of the current file) and the `gameTrends.marketOverview && <GameSummaryBanner .../>` usage. Add imports and the new sub-component just above the `TrendAnalysisSection` definition:

```tsx
import TeamLogo from './TeamLogo';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';
import { getTeamColors } from '../utils/teamColors';
import { convertTeamNameBySport } from '../utils/teamNameConverter';
import { getSportType } from '../types/gameTypes';

const MARKET_CARD_TITLES: Record<'moneyline' | 'spread' | 'total', string> = {
  moneyline: 'Moneyline Trends',
  spread: 'Spread Trends',
  total: 'Total Trends',
};

const formatSigned = (n: number): string => `${n > 0 ? '+' : ''}${n}`;

const spreadPointForTeam = (game: any, teamName: string): number | null => {
  if (game?.home?.team === teamName) return game?.home?.odds?.spread_point ?? null;
  if (game?.away?.team === teamName) return game?.away?.odds?.spread_point ?? null;
  return null;
};

const marketCardLabel = (marketKey: 'moneyline' | 'spread' | 'total', entry: MarketOverviewEntry, game: any): string => {
  if (marketKey === 'moneyline') return `${entry.lean} win`;
  if (marketKey === 'total') return entry.lean;
  const point = spreadPointForTeam(game, entry.lean);
  return point != null ? `${entry.lean} cover ${formatSigned(point)}` : `${entry.lean} cover the spread`;
};

const MarketTrendCard: React.FC<{
  marketKey: 'moneyline' | 'spread' | 'total';
  entry: MarketOverviewEntry;
  game: any;
  sportKey: string;
}> = ({ marketKey, entry, game, sportKey }) => {
  const pct = Math.round(entry.probability * 100);
  const wins = Math.round(entry.probability * entry.sample_size);
  const losses = entry.sample_size - wins;
  const dbSport = getSportType(sportKey);
  const barColor =
    marketKey === 'total'
      ? tokens.neutralBar
      : getTeamColors(dbSport, convertTeamNameBySport(sportKey, entry.lean)).primary;

  return (
    <Box
      sx={{
        bgcolor: tokens.cardBg,
        border: `1px solid ${tokens.cardBorder}`,
        borderRadius: `${tokens.cardRadius}px`,
        p: '18px 18px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        '&:hover': { borderColor: '#c9ccc5', boxShadow: tokens.shadowHover },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600, color: tokens.text.secondary }}>
          {MARKET_CARD_TITLES[marketKey]}
        </Typography>
        <Typography sx={{ fontSize: '1.125rem', color: tokens.link }}>›</Typography>
      </Box>
      <Typography sx={{ fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>
        {pct}%
      </Typography>
      <Typography sx={{ fontSize: '0.9375rem', fontWeight: 600 }}>{marketCardLabel(marketKey, entry, game)}</Typography>
      <Typography sx={{ fontSize: '0.8125rem', color: tokens.text.secondary }}>
        {wins}-{losses} ({entry.sample_size} games)
      </Typography>
      <Box sx={{ height: 6, borderRadius: '3px', bgcolor: tokens.trackBg2, overflow: 'hidden', mt: 0.5 }}>
        <Box sx={{ height: '100%', width: `${pct}%`, bgcolor: barColor, borderRadius: '3px' }} />
      </Box>
    </Box>
  );
};
```

In the `TrendAnalysisSection` component itself, add the `sportKey` prop (with default) and render the 3-card grid in place of the removed `GameSummaryBanner`:

```tsx
interface TrendAnalysisSectionProps {
  gameTrends: GameWithTrends | null;
  loading: boolean;
  game: any;
  minTrendLength: number;
  dataSinceYear?: number | null;
  sportKey?: string;
}
```

```tsx
const TrendAnalysisSection: React.FC<TrendAnalysisSectionProps> = ({
  gameTrends,
  loading,
  game,
  minTrendLength,
  dataSinceYear,
  sportKey = 'baseball_mlb',
}) => {
  // ...loading/null checks unchanged...

  const marketRows = (['moneyline', 'spread', 'total'] as const)
    .map((key) => ({ key, entry: gameTrends.marketOverview?.[key] }))
    .filter((r): r is { key: 'moneyline' | 'spread' | 'total'; entry: MarketOverviewEntry } => !!r.entry);

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', px: { xs: 2, sm: 3 }, pt: 4, mb: 2 }}>
      {marketRows.length > 0 && (
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', mb: 3 }}>
          {marketRows.map(({ key, entry }) => (
            <MarketTrendCard key={key} marketKey={key} entry={entry} game={game} sportKey={sportKey} />
          ))}
        </Box>
      )}
      {/* ...existing "Trend Analysis" heading + allTrends list, unchanged for now (Tasks 4 & 5 touch this next)... */}
    </Box>
  );
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TrendAnalysisSection.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd getstam-react && git add src/components/TrendAnalysisSection.tsx src/components/TrendAnalysisSection.test.tsx
git commit -m "$(cat <<'EOF'
Replace trend summary banner with 3 market trend cards

Moneyline/Spread/Total now render as the new design's %-and-progress-bar
cards (team-colored bars) instead of the gradient "What the numbers
suggest" prose banner.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Trend vs. Trend Collision card

**Files:**
- Modify: `getstam-react/src/utils/trendAnalysis.ts` (type extension)
- Modify: `getstam-react/src/components/TrendAnalysisSection.tsx`
- Modify: `getstam-react/src/components/TrendAnalysisSection.test.tsx`

**Interfaces:**
- Produces: `CollisionTeamTrend` interface (`utils/trendAnalysis.ts`): `{ team: string; type: TrendType; count: number; venue: 'general' | 'venue_specific' }`. `TrendResult` gains optional `home_trend?: CollisionTeamTrend` and `away_trend?: CollisionTeamTrend`.
- Produces: `CollisionCard` internal sub-component in `TrendAnalysisSection.tsx`.
- Consumes: `TeamLogo`, `gameDetailsTokens`, `getTeamColors` (Task 1).

- [ ] **Step 1: Write the failing test**

Add to `TrendAnalysisSection.test.tsx`:

```tsx
describe('TrendAnalysisSection collision card', () => {
  const collisionTrend = {
    type: 'win_streak' as const,
    count: 5,
    description: "Brewers' 5-game win streak at home meets Rays' 3-game loss streak on the road — ...",
    continuation_rate: 0.72,
    sample_size: 18,
    home_trend: { team: 'Milwaukee Brewers', type: 'win_streak' as const, count: 5, venue: 'venue_specific' as const },
    away_trend: { team: 'Tampa Bay Rays', type: 'loss_streak' as const, count: 3, venue: 'venue_specific' as const },
  };

  it('renders both teams, their streak text, and the split percentage', () => {
    const trends: GameWithTrends = {
      ...gameTrends,
      collisionTrends: [collisionTrend],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    expect(screen.getByText('Trend vs. Trend Collision')).toBeInTheDocument();
    expect(screen.getByText('Won 5 straight at home')).toBeInTheDocument();
    expect(screen.getByText('Lost 3 straight on the road')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
    expect(screen.getByText('28%')).toBeInTheDocument();
    expect(screen.getByText('18 historical meetings')).toBeInTheDocument();
  });

  it('renders nothing for the collision card when there are no collision trends', () => {
    render(<TrendAnalysisSection gameTrends={gameTrends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);
    expect(screen.queryByText('Trend vs. Trend Collision')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TrendAnalysisSection.test.tsx --watchAll=false`
Expected: FAIL — "Trend vs. Trend Collision" not found; TS error on `home_trend`/`away_trend` not existing on `TrendResult`

- [ ] **Step 3: Extend `TrendResult` in `utils/trendAnalysis.ts`**

```ts
export interface CollisionTeamTrend {
  team: string;
  type: TrendType;
  count: number;
  venue: 'general' | 'venue_specific';
}

export interface TrendResult {
  type: TrendType;
  count: number;
  description: string;
  continuation_rate?: number;
  sample_size?: number;
  secondary_rates?: SecondaryRate[];
  // Only present on entries from collisionTrends — see
  // api/services/historical/trend_enrichment.py:_build_collision_entry,
  // which already returns these fields; this just types what's already there.
  home_trend?: CollisionTeamTrend;
  away_trend?: CollisionTeamTrend;
}
```

- [ ] **Step 4: Add `CollisionCard` to `TrendAnalysisSection.tsx`**

```tsx
import { TrendType, CollisionTeamTrend } from '../utils/trendAnalysis';

const COLLISION_PHRASE: Record<TrendType, (n: number) => string> = {
  win_streak: (n) => `Won ${n} straight`,
  loss_streak: (n) => `Lost ${n} straight`,
  cover_streak: (n) => `Covered ${n} straight spreads`,
  no_cover_streak: (n) => `Failed to cover ${n} straight spreads`,
  over_streak: (n) => `Hit the OVER ${n} straight`,
  under_streak: (n) => `Hit the UNDER ${n} straight`,
};

const describeCollisionSide = (trend: CollisionTeamTrend | undefined, side: 'home' | 'away'): string => {
  if (!trend) return '';
  const venueSuffix = trend.venue === 'venue_specific' ? (side === 'home' ? ' at home' : ' on the road') : '';
  return `${COLLISION_PHRASE[trend.type](trend.count)}${venueSuffix}`;
};

const CollisionCard: React.FC<{ trend: TrendResult; sportKey: string }> = ({ trend, sportKey }) => {
  const { home_trend, away_trend, continuation_rate, sample_size } = trend;
  if (!home_trend || !away_trend || continuation_rate == null || sample_size == null) return null;

  const pct = Math.round(continuation_rate * 100);
  const otherPct = 100 - pct;
  const dbSport = getSportType(sportKey);
  const homeColor = getTeamColors(dbSport, convertTeamNameBySport(sportKey, home_trend.team));
  const awayColor = getTeamColors(dbSport, convertTeamNameBySport(sportKey, away_trend.team));

  return (
    <Box
      sx={{
        bgcolor: tokens.cardBg,
        border: `1px solid ${tokens.cardBorder}`,
        borderRadius: `${tokens.cardRadius}px`,
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: '1.1fr 1fr auto' },
        overflow: 'hidden',
        mb: 3,
      }}
    >
      <Box sx={{ p: '18px 22px' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <Box sx={{ width: 32, height: 32, borderRadius: '50%', bgcolor: tokens.collisionIcon, display: 'grid', placeItems: 'center' }}>
            <Box sx={{ width: 10, height: 10, bgcolor: '#fff', transform: 'rotate(45deg)' }} />
          </Box>
          <Box>
            <Typography sx={{ fontSize: '1rem', fontWeight: 700 }}>Trend vs. Trend Collision</Typography>
            <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary }}>When both teams' trends meet</Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: 1, mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
            <TeamLogo sportKey={sportKey} teamName={home_trend.team} size={40} />
            <Box>
              <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{home_trend.team}</Typography>
              <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary }}>
                {describeCollisionSide(home_trend, 'home')}
              </Typography>
            </Box>
          </Box>
          <Typography
            sx={{
              fontSize: '0.6875rem',
              fontWeight: 700,
              color: tokens.text.muted,
              bgcolor: tokens.chipTrackBg,
              borderRadius: '999px',
              px: 1,
              py: 0.5,
              textAlign: 'center',
            }}
          >
            VS
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, justifyContent: 'flex-end', textAlign: 'right' }}>
            <Box>
              <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{away_trend.team}</Typography>
              <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary }}>
                {describeCollisionSide(away_trend, 'away')}
              </Typography>
            </Box>
            <TeamLogo sportKey={sportKey} teamName={away_trend.team} size={40} />
          </Box>
        </Box>
      </Box>

      <Box sx={{ bgcolor: tokens.subtlePanelBg, borderLeft: { md: `1px solid ${tokens.borders.light}` }, p: '18px 22px' }}>
        <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary, mb: 1 }}>
          Historically when this collision has happened
        </Typography>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'nowrap', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75 }}>
            <Typography sx={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>
              {pct}%
            </Typography>
            <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600 }}>{home_trend.team} win</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75 }}>
            <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600 }}>{away_trend.team} win</Typography>
            <Typography sx={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>
              {otherPct}%
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', height: 8, borderRadius: '4px', overflow: 'hidden', gap: '2px', mt: 1 }}>
          <Box sx={{ width: `${pct}%`, bgcolor: homeColor.primary }} />
          <Box sx={{ flex: 1, bgcolor: awayColor.secondary }} />
        </Box>
        <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary, mt: 1 }}>{sample_size} historical meetings</Typography>
      </Box>

      <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center', px: 2, color: tokens.link, fontSize: '1.375rem' }}>›</Box>
    </Box>
  );
};
```

In `TrendAnalysisSection`, after the market-cards grid, pick and render the top collision trend:

```tsx
const topCollisionTrend = (gameTrends.collisionTrends || [])[0] ?? null;
```

```tsx
{topCollisionTrend && <CollisionCard trend={topCollisionTrend} sportKey={sportKey} />}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TrendAnalysisSection.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd getstam-react && git add src/utils/trendAnalysis.ts src/components/TrendAnalysisSection.tsx src/components/TrendAnalysisSection.test.tsx
git commit -m "$(cat <<'EOF'
Add Trend vs. Trend Collision card

Types the home_trend/away_trend fields the backend already returns on
collisionTrends entries, and renders the new design's two-team split-bar
card from the top collision trend.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Restyle the remaining trend list

**Files:**
- Modify: `getstam-react/src/components/TrendAnalysisSection.tsx`
- Modify: `getstam-react/src/components/TrendAnalysisSection.test.tsx`

**Interfaces:**
- Consumes: `gameDetailsTokens` (Task 1). No new exports.
- Changes: `allTrends` excludes whichever trend object `topCollisionTrend` (Task 4) points to, so it isn't shown twice. `TrendDetailCard`'s colors switch from the old green/red (`#16a34a`/`#dc2626`, `#dcfce7`/`#fee2e2`) to `gameDetailsTokens.hit`/`gameDetailsTokens.miss`. The list renders under a plain "More trends" heading instead of "Trend Analysis".

- [ ] **Step 1: Write the failing test**

Add to `TrendAnalysisSection.test.tsx`:

```tsx
describe('TrendAnalysisSection remaining trends list', () => {
  it('shows a "More trends" heading and does not repeat the collision trend', () => {
    const collisionTrend = {
      type: 'win_streak' as const,
      count: 5,
      description: 'collision description',
      continuation_rate: 0.72,
      sample_size: 18,
      home_trend: { team: 'Milwaukee Brewers', type: 'win_streak' as const, count: 5, venue: 'venue_specific' as const },
      away_trend: { team: 'Tampa Bay Rays', type: 'loss_streak' as const, count: 3, venue: 'venue_specific' as const },
    };
    const otherTrend = {
      type: 'cover_streak' as const,
      count: 4,
      description: 'Brewers covered 4 straight spreads',
      continuation_rate: 0.6,
      sample_size: 10,
    };
    const trends: GameWithTrends = {
      ...gameTrends,
      collisionTrends: [collisionTrend],
      homeTeamTrends: [otherTrend],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    expect(screen.getByText('More trends')).toBeInTheDocument();
    expect(screen.getAllByText(/Brewers covered 4 straight spreads|collision description/).length).toBe(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TrendAnalysisSection.test.tsx --watchAll=false`
Expected: FAIL — heading still reads "Trend Analysis", and the collision trend's own description also appears in the list (2 matches instead of 1)

- [ ] **Step 3: Update `allTrends` filtering, heading, and `TrendDetailCard` colors**

```tsx
const allTrends: TrendResult[] = [
  ...(gameTrends.headToHeadTrends || []),
  ...(gameTrends.homeAtHomeH2HTrends || []),
  ...(gameTrends.collisionTrends || []),
  ...(gameTrends.homeTeamHomeTrends || []),
  ...(gameTrends.awayTeamAwayTrends || []),
  ...(gameTrends.homeTeamTrends || []).filter((t) => !homeSpecificTypes.has(t.type)),
  ...(gameTrends.awayTeamTrends || []).filter((t) => !awaySpecificTypes.has(t.type)),
]
  .filter((t) => t.count >= minTrendLength && t !== topCollisionTrend)
  .sort((a, b) => getConfidenceScore(b) - getConfidenceScore(a) || b.count - a.count);
```

```tsx
<Typography variant="h5" sx={{ fontWeight: 700, mb: 2, color: tokens.text.primary }}>
  More trends
</Typography>
```

In `TrendDetailCard`, replace the green/red constants:

```tsx
const positive = POSITIVE_TYPES.has(trend.type);
const trendColor = positive ? tokens.hit.text : tokens.miss.text;
const borderColor = tokens.cardBorder;
const bgColor = tokens.cardBg;
```

and the icon-circle background:

```tsx
background: positive ? tokens.hit.bg : tokens.miss.bg,
```

and the progress-bar track/fill:

```tsx
<Box sx={{ height: 7, borderRadius: '999px', bgcolor: positive ? tokens.hit.bg : tokens.miss.bg, overflow: 'hidden' }}>
  <Box sx={{ height: '100%', width: `${pct}%`, bgcolor: trendColor, borderRadius: '999px', transition: 'width 0.6s ease' }} />
</Box>
```

Wrap each `TrendDetailCard` with the new card radius (`tokens.cardRadius`) instead of the old `14px`, and give the card a plain `1px solid ${tokens.cardBorder}` border regardless of positive/negative (the hit/miss distinction now lives in the icon circle, badge text color, and progress bar only — the card shell itself stays neutral per the "white card, team/result color used only as accents" design language):

```tsx
<Box sx={{ px: 2, py: 2, background: tokens.cardBg, borderRadius: `${tokens.cardRadius}px`, border: `1px solid ${tokens.cardBorder}` }}>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TrendAnalysisSection.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 5: Run the full test file to confirm no regressions in earlier tasks' tests**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/TrendAnalysisSection.test.tsx --watchAll=false`
Expected: PASS (all describe blocks from Tasks 3–5)

- [ ] **Step 6: Commit**

```bash
cd getstam-react && git add src/components/TrendAnalysisSection.tsx src/components/TrendAnalysisSection.test.tsx
git commit -m "$(cat <<'EOF'
Restyle remaining trend list to new hit/miss tokens

The flat trend list below the market/collision cards keeps all its
content but switches to the new card shell and hit/miss color tokens,
and no longer repeats whichever trend the collision card already shows.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Player Prop Trends highlight

**Files:**
- Create: `getstam-react/src/components/PlayerStreakHighlight.tsx`
- Create: `getstam-react/src/components/PlayerStreakHighlight.test.tsx`
- Modify: `getstam-react/src/components/PlayerStreaksStrip.tsx`
- Modify: `getstam-react/src/components/GameDetails.tsx`

**Interfaces:**
- Consumes: `PlayerStreak`, `TeamStreaks` (`components/PlayerStreaksStrip.tsx`, existing), `gameDetailsTokens` (Task 1).
- Produces: `PlayerStreakHighlight` component, props `{ groups: TeamStreaks[] }`, default export.
- `GameDetails.tsx` renders `<PlayerStreakHighlight groups={groups} />` immediately above the existing `<PlayerStreaksStrip groups={groups} showAll />` (same `groups` value, computed once).

- [ ] **Step 1: Write the failing test**

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PlayerStreakHighlight from './PlayerStreakHighlight';
import { TeamStreaks } from './PlayerStreaksStrip';

const groups: TeamStreaks[] = [
  {
    team: 'Brewers',
    streaks: [
      { player_name: 'C. Yelich', stat: 'hits', streak_count: 5, continuation_rate: 0.57, sample_size: 7 },
    ],
  },
  {
    team: 'Rays',
    streaks: [
      { player_name: 'R. Arozarena', stat: 'hr', streak_count: 2, continuation_rate: 0.8, sample_size: 10 },
    ],
  },
];

describe('PlayerStreakHighlight', () => {
  it('shows the single best streak (highest continuation rate) with a HOT pill', () => {
    render(
      <MemoryRouter>
        <PlayerStreakHighlight groups={groups} />
      </MemoryRouter>
    );
    expect(screen.getByText('HOT')).toBeInTheDocument();
    expect(screen.getByText('R. Arozarena')).toBeInTheDocument();
    expect(screen.getByText(/2 straight 1\+ HR/)).toBeInTheDocument();
    expect(screen.getByText(/continues 80% \(8\/10\)/)).toBeInTheDocument();
  });

  it('renders nothing when there are no streaks', () => {
    const { container } = render(
      <MemoryRouter>
        <PlayerStreakHighlight groups={[{ team: 'Brewers', streaks: [] }]} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/PlayerStreakHighlight.test.tsx --watchAll=false`
Expected: FAIL — `Cannot find module './PlayerStreakHighlight'`

- [ ] **Step 3: Export a shared `getStatLabel` from `PlayerStreaksStrip.tsx`**

`getStatLabel` is currently private to `PlayerStreaksStrip.tsx` (line 41). Add `export` to its declaration so `PlayerStreakHighlight` can reuse the exact same label text instead of duplicating the stat/direction → label mapping:

```ts
export function getStatLabel(stat: string, line?: number, direction?: 'over' | 'under'): string {
```

- [ ] **Step 4: Write `components/PlayerStreakHighlight.tsx`**

```tsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { TeamStreaks, PlayerStreak, getStatLabel } from './PlayerStreaksStrip';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';

interface PlayerStreakHighlightProps {
  groups: TeamStreaks[];
}

const pickBestStreak = (groups: TeamStreaks[]): PlayerStreak | null => {
  let best: PlayerStreak | null = null;
  for (const group of groups) {
    for (const streak of group.streaks) {
      if (streak.continuation_rate == null) continue;
      if (
        !best ||
        streak.continuation_rate > (best.continuation_rate ?? 0) ||
        (streak.continuation_rate === best.continuation_rate && (streak.sample_size ?? 0) > (best.sample_size ?? 0))
      ) {
        best = streak;
      }
    }
  }
  return best;
};

const PlayerStreakHighlight: React.FC<PlayerStreakHighlightProps> = ({ groups }) => {
  const best = pickBestStreak(groups);
  if (!best || best.continuation_rate == null || best.sample_size == null) return null;

  const pct = Math.round(best.continuation_rate * 100);
  const continued = Math.round(best.continuation_rate * best.sample_size);
  const label = getStatLabel(best.stat, best.line, best.direction);

  return (
    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
      <Typography
        sx={{
          fontSize: '0.6875rem',
          fontWeight: 700,
          bgcolor: tokens.hit.bg,
          color: tokens.hit.text,
          borderRadius: '999px',
          px: '9px',
          py: '3px',
        }}
      >
        HOT
      </Typography>
      <Typography sx={{ fontSize: '0.875rem', fontWeight: 700, color: tokens.link }}>{best.player_name}</Typography>
      <Typography sx={{ fontSize: '0.875rem' }}>
        {best.streak_count} straight {label}
      </Typography>
      <Typography sx={{ fontSize: '0.875rem', color: tokens.text.secondary }}>
        · continues {pct}% ({continued}/{best.sample_size})
      </Typography>
      {/* "View all player prop trends →" has no destination route yet — rendered
          hidden so wiring it up later is a one-line change, per the design spec. */}
      <Box
        component="button"
        sx={{ display: 'none' }}
        aria-hidden="true"
      >
        View all player prop trends →
      </Box>
      <Typography sx={{ fontSize: '0.75rem', color: tokens.text.tertiary, width: '100%' }}>
        Continuation rate calculated from each player's own historical game records.
      </Typography>
    </Box>
  );
};

export default PlayerStreakHighlight;
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/PlayerStreakHighlight.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 6: Restyle `PlayerStreaksStrip.tsx` chip tokens**

In `StreakPill`, replace the hardcoded hex with the shared tokens:

```ts
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';
```

```ts
const bgcolor = isUnder ? tokens.miss.bg : isPositive ? tokens.hit.bg : tokens.cardBg;
const borderColor = isUnder ? '#fecaca' : isPositive ? '#bbf7d0' : tokens.cardBorder;
```

(The `#fecaca`/`#bbf7d0` border shades stay as-is — the design tokens list only specifies hit/miss `bg`/`text`, not a separate border shade, so keeping the existing border values alongside the new `bg` tokens matches what the handoff actually specifies.)

- [ ] **Step 7: Wire `PlayerStreakHighlight` into `GameDetails.tsx`**

In `components/GameDetails.tsx`, add the import:

```tsx
import PlayerStreakHighlight from "./PlayerStreakHighlight";
```

Immediately above the existing `<PlayerStreaksStrip groups={groups} showAll />` line (around line 409), add:

```tsx
<PlayerStreakHighlight groups={groups} />
```

- [ ] **Step 8: Run the full GameDetails test suite to confirm no regression**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameDetails.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
cd getstam-react && git add src/components/PlayerStreakHighlight.tsx src/components/PlayerStreakHighlight.test.tsx src/components/PlayerStreaksStrip.tsx src/components/GameDetails.tsx
git commit -m "$(cat <<'EOF'
Add Player Prop Trends highlight line above the player streaks strip

Surfaces the single best streak (HOT pill + player + continues %) above
the existing full streaks strip, which keeps showing every streak,
restyled to the new hit/miss tokens.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `GameLogTable` core rendering

**Files:**
- Create: `getstam-react/src/components/GameLogTable.tsx`
- Test: `getstam-react/src/components/GameLogTable.test.tsx`

**Interfaces:**
- Consumes: `TeamLogo`, `gameDetailsTokens` (Task 1); `BaseGame`/`NFLGame`/`MLBGame`/`SoccerGame`/`NHLGame`/`HistoricalGame`/`SportType`/`getSportType` (`types/gameTypes.ts`, existing); `dbNameToSlug` (`utils/teamSlugUtils.ts`, existing).
- Produces: `GameLogTable` component, default export, props:
  ```ts
  interface GameLogTableProps {
    title: string;
    games: HistoricalGame[];
    loading?: boolean;
    teamName?: string;
    isHeadToHead?: boolean;
    sportType: SportType;
    sport?: string;
    defaultExpanded?: boolean;
  }
  ```
  (Identical shape to `HistoricalGamesProps & { sport?: string }` plus one new optional `defaultExpanded`, so call sites in `GameDetails.tsx` barely change — see Task 8.)

- [ ] **Step 1: Write the failing test**

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GameLogTable from './GameLogTable';
import { MLBGame } from '../types/gameTypes';

const games: MLBGame[] = [
  {
    game_id: 1,
    game_date: '2026-10-15',
    start_time: '',
    team_side: 'away',
    home_team: 'Los Angeles Dodgers',
    away_team: 'Milwaukee Brewers',
    home_runs: 4,
    away_runs: 6,
    home_line: -130,
    away_line: 130,
    total: 7.5,
    playoffs: false,
  },
];

function renderTable(defaultExpanded = true) {
  return render(
    <MemoryRouter>
      <GameLogTable
        title="Milwaukee Brewers - Last 5 Games"
        games={games}
        teamName="Brewers"
        sportType="mlb"
        sport="mlb"
        defaultExpanded={defaultExpanded}
      />
    </MemoryRouter>
  );
}

describe('GameLogTable', () => {
  it('shows the header summary and a TeamLogo abbreviation when expanded', () => {
    renderTable(true);
    expect(screen.getByText('Milwaukee Brewers - Last 5 Games')).toBeInTheDocument();
    expect(screen.getByText('1-0 · Over 1-0')).toBeInTheDocument();
    expect(screen.getByText('MIL')).toBeInTheDocument();
    expect(screen.getByText('10/15/2026')).toBeInTheDocument();
    expect(screen.getByText('+130')).toBeInTheDocument();
  });

  it('starts collapsed and reveals rows on header click when defaultExpanded is false', async () => {
    renderTable(false);
    expect(screen.queryByText('10/15/2026')).not.toBeInTheDocument();
    const header = screen.getByRole('button', { name: /Milwaukee Brewers - Last 5 Games/i });
    header.click();
    expect(await screen.findByText('10/15/2026')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameLogTable.test.tsx --watchAll=false`
Expected: FAIL — `Cannot find module './GameLogTable'`

- [ ] **Step 3: Write `components/GameLogTable.tsx`**

```tsx
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { BaseGame, NFLGame, MLBGame, SoccerGame, HistoricalGame, SportType } from '../types/gameTypes';
import { dbNameToSlug } from '../utils/teamSlugUtils';
import TeamLogo from './TeamLogo';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';

interface GameLogTableProps {
  title: string;
  games: HistoricalGame[];
  loading?: boolean;
  teamName?: string;
  isHeadToHead?: boolean;
  sportType: SportType;
  sport?: string;
  defaultExpanded?: boolean;
}

type DerivedGameData = {
  homeTeam: string;
  awayTeam: string;
  homeScore: number | null;
  awayScore: number | null;
  homeLine: number | null;
  awayLine: number | null;
  totalScore: number | null;
  totalLine: number | null;
};

// Same per-sport field mapping as components/HistoricalGames.tsx's getGameData —
// duplicated here deliberately (see Task 7 Interfaces note / spec): GameLogTable
// is a separate, Game-Details-only component so HistoricalGames can stay
// untouched for TeamPage/BlogPostPage.
function getGameData(game: HistoricalGame, sportType: SportType): DerivedGameData {
  switch (sportType) {
    case 'nfl':
    case 'ncaaf':
    case 'nba': {
      const g = game as NFLGame;
      return {
        homeTeam: g.home_team_name,
        awayTeam: g.away_team_name,
        homeScore: g.home_points,
        awayScore: g.away_points,
        homeLine: g.home_line,
        awayLine: g.away_line,
        totalScore: g.total_points,
        totalLine: g.total ?? null,
      };
    }
    case 'mlb': {
      const g = game as MLBGame;
      return {
        homeTeam: g.home_team,
        awayTeam: g.away_team,
        homeScore: g.home_runs,
        awayScore: g.away_runs,
        homeLine: g.home_line,
        awayLine: g.away_line,
        totalScore: g.home_runs + g.away_runs,
        totalLine: g.total,
      };
    }
    case 'nhl': {
      const g = game as import('../types/gameTypes').NHLGame;
      return {
        homeTeam: g.home_team_name,
        awayTeam: g.away_team_name,
        homeScore: g.home_goals,
        awayScore: g.away_goals,
        homeLine: g.home_money_line,
        awayLine: g.away_money_line,
        totalScore:
          typeof g.home_goals === 'number' && typeof g.away_goals === 'number' ? g.home_goals + g.away_goals : null,
        totalLine: g.total,
      };
    }
    case 'worldcup':
    case 'soccer': {
      const g = game as SoccerGame;
      return {
        homeTeam: g.home_team_name,
        awayTeam: g.away_team_name,
        homeScore: g.home_goals,
        awayScore: g.away_goals,
        homeLine: g.home_spread,
        awayLine: g.away_spread,
        totalScore: g.total_goals,
        totalLine: g.total_over_point,
      };
    }
    default: {
      const g = game as NFLGame;
      return {
        homeTeam: g.home_team_name,
        awayTeam: g.away_team_name,
        homeScore: g.home_points,
        awayScore: g.away_points,
        homeLine: g.home_line,
        awayLine: g.away_line,
        totalScore: g.total_points,
        totalLine: g.total ?? null,
      };
    }
  }
}

function getTeamData(game: HistoricalGame, sportType: SportType, teamName: string) {
  const gd = getGameData(game, sportType);
  const isHome = gd.homeTeam === teamName;
  const isAway = gd.awayTeam === teamName;
  if (isHome) {
    return { site: 'home', teamPoints: gd.homeScore, teamLine: gd.homeLine, opponentName: gd.awayTeam, opponentPoints: gd.awayScore };
  }
  if (isAway) {
    return { site: 'away', teamPoints: gd.awayScore, teamLine: gd.awayLine, opponentName: gd.homeTeam, opponentPoints: gd.homeScore };
  }
  const side = (game as BaseGame).team_side === 'home' ? 'home' : 'away';
  return side === 'home'
    ? { site: 'home', teamPoints: gd.homeScore, teamLine: gd.homeLine, opponentName: gd.awayTeam, opponentPoints: gd.awayScore }
    : { site: 'away', teamPoints: gd.awayScore, teamLine: gd.awayLine, opponentName: gd.homeTeam, opponentPoints: gd.homeScore };
}

const getScoreLabel = (sportType: SportType): string => {
  if (sportType === 'mlb') return 'Runs';
  if (sportType === 'soccer' || sportType === 'nhl') return 'Goals';
  return 'Points';
};

const formatDate = (dateString: string): string => {
  const parts = dateString.split('-');
  if (parts.length !== 3) return dateString;
  const [year, month, day] = parts.map(Number);
  if (!month || !day || !year) return dateString;
  return `${month}/${day}/${year}`;
};

const formatSigned = (n: number | null): string => (n == null ? 'N/A' : `${n > 0 ? '+' : ''}${n}`);

const resultColors = (result: 'win' | 'loss' | 'push' | null) => {
  if (result === 'win') return { bgcolor: tokens.hit.bg, color: tokens.hit.text };
  if (result === 'loss') return { bgcolor: tokens.miss.bg, color: tokens.miss.text };
  if (result === 'push') return { bgcolor: tokens.trackBg2, color: tokens.text.secondary };
  return {};
};

const TeamCellLink: React.FC<{ name: string; sport?: string }> = ({ name, sport }) => {
  const slug = sport ? dbNameToSlug(name, sport) : null;
  if (!slug) return <>{name}</>;
  return (
    <Link to={`/team/${sport}/${slug}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      {name}
    </Link>
  );
};

const GameLogTable: React.FC<GameLogTableProps> = ({
  title,
  games,
  loading = false,
  teamName = '',
  isHeadToHead = false,
  sportType,
  sport,
  defaultExpanded = true,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (loading) {
    return (
      <Box sx={{ border: `1px solid ${tokens.borders.lighter}`, borderRadius: `${tokens.tableRadius}px`, p: 2 }}>
        <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{title}</Typography>
        <Typography sx={{ fontSize: '0.8125rem', color: tokens.text.secondary }}>Loading…</Typography>
      </Box>
    );
  }

  if (!games || games.length === 0) {
    return (
      <Box sx={{ border: `1px solid ${tokens.borders.lighter}`, borderRadius: `${tokens.tableRadius}px`, p: 2 }}>
        <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{title}</Typography>
        <Typography sx={{ fontSize: '0.8125rem', color: tokens.text.secondary }}>No games found</Typography>
      </Box>
    );
  }

  let wins = 0;
  let losses = 0;
  let overs = 0;
  let unders = 0;
  games.forEach((game) => {
    const gd = getGameData(game, sportType);
    const td = getTeamData(game, sportType, teamName);
    if (td.teamPoints != null && td.opponentPoints != null) {
      if (td.teamPoints > td.opponentPoints) wins++;
      else if (td.teamPoints < td.opponentPoints) losses++;
    }
    if (gd.totalScore != null && gd.totalLine != null) {
      if (gd.totalScore > gd.totalLine) overs++;
      else if (gd.totalScore < gd.totalLine) unders++;
    }
  });
  const summary = `${wins}-${losses} · Over ${overs}-${unders}`;

  const h2hOpponentName = isHeadToHead && games.length > 0 ? getTeamData(games[0], sportType, teamName).opponentName : null;

  return (
    <Box sx={{ border: `1px solid ${tokens.borders.lighter}`, borderRadius: `${tokens.tableRadius}px`, overflow: 'hidden' }}>
      <Box
        component="button"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
        sx={{
          all: 'unset',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: '100%',
          boxSizing: 'border-box',
          bgcolor: tokens.subtlePanelBg,
          px: '14px',
          py: '10px',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isHeadToHead && h2hOpponentName ? (
            <Box sx={{ display: 'flex' }}>
              <TeamLogo sportKey={sport || sportType} teamName={teamName} size={28} border="2px solid #fff" />
              <Box sx={{ ml: '-8px' }}>
                <TeamLogo sportKey={sport || sportType} teamName={h2hOpponentName} size={28} border="2px solid #fff" />
              </Box>
            </Box>
          ) : (
            <TeamLogo sportKey={sport || sportType} teamName={teamName} size={28} />
          )}
          <Box sx={{ textAlign: 'left' }}>
            <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{title}</Typography>
            <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary }}>{summary}</Typography>
          </Box>
        </Box>
        {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
      </Box>

      {expanded && (
        <TableContainer sx={{ overflowX: 'auto' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 100, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Date</TableCell>
                <TableCell sx={{ width: 70, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Site</TableCell>
                <TableCell sx={{ width: '1fr', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Team</TableCell>
                <TableCell sx={{ width: 90, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>{getScoreLabel(sportType)}</TableCell>
                <TableCell sx={{ width: 80, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Line</TableCell>
                <TableCell sx={{ width: '1fr', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Opponent</TableCell>
                <TableCell sx={{ width: 110, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Opp {getScoreLabel(sportType)}</TableCell>
                <TableCell sx={{ width: 120, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Betting Total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {games.map((game, index) => {
                const gd = getGameData(game, sportType);
                const td = getTeamData(game, sportType, teamName);
                const teamResult: 'win' | 'loss' | 'push' | null =
                  td.teamPoints == null || td.opponentPoints == null
                    ? null
                    : td.teamPoints > td.opponentPoints
                    ? 'win'
                    : td.teamPoints < td.opponentPoints
                    ? 'loss'
                    : 'push';
                const totalResult: 'win' | 'loss' | 'push' | null =
                  gd.totalScore == null || gd.totalLine == null
                    ? null
                    : gd.totalScore > gd.totalLine
                    ? 'win'
                    : gd.totalScore < gd.totalLine
                    ? 'loss'
                    : 'push';
                const ouLabel = totalResult === 'win' ? 'O' : totalResult === 'loss' ? 'U' : 'P';

                return (
                  <TableRow key={(game as BaseGame).game_id ?? index} sx={{ '&:hover': { bgcolor: tokens.subtlePanelBg } }}>
                    <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                      {formatDate((game as BaseGame).game_date)}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}`, textTransform: 'capitalize' }}>
                      {td.site}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', fontWeight: 700, borderTop: `1px solid ${tokens.borders.lighter}`, ...resultColors(teamResult) }}>
                      <TeamCellLink name={td.site === 'home' ? gd.homeTeam : gd.awayTeam} sport={sport} />
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', fontWeight: 700, borderTop: `1px solid ${tokens.borders.lighter}`, ...resultColors(teamResult) }}>
                      {td.teamPoints ?? 'N/A'}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}`, fontVariantNumeric: 'tabular-nums' }}>
                      {formatSigned(td.teamLine)}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                      <TeamCellLink name={td.opponentName} sport={sport} />
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                      {td.opponentPoints ?? 'N/A'}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', fontWeight: 700, borderTop: `1px solid ${tokens.borders.lighter}`, ...resultColors(totalResult) }}>
                      {gd.totalLine ?? 'N/A'} · {ouLabel} · {gd.totalScore ?? 'N/A'}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default GameLogTable;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameLogTable.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd getstam-react && git add src/components/GameLogTable.tsx src/components/GameLogTable.test.tsx
git commit -m "$(cat <<'EOF'
Add GameLogTable for the Recent Performance tabbed panel

A Game-Details-only game-log table (fixed-width columns, full-cell
win/loss and O/U fills, collapsible TeamLogo header) built alongside
HistoricalGames, which stays unchanged for TeamPage/BlogPostPage.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Segmented sub-tab control + wire `GameLogTable` into `GameDetails.tsx`

**Files:**
- Modify: `getstam-react/src/components/GameDetails.tsx`
- Modify: `getstam-react/src/components/GameDetails.test.tsx` (only if Step 6 surfaces a regression — see below)

**Interfaces:**
- Consumes: `GameLogTable` (Task 7).
- Changes: the 7 `<HistoricalGames ... />` call sites (all 3 `historicalSubTab` branches) become `<GameLogTable ... />` with the same props plus `defaultExpanded`. The MUI `Tabs` sub-tab control (lines ~469–519) becomes a 3-option segmented control driving the same `historicalSubTab` state. The main "Recent Performance" / "Player Props" `Tabs` (lines ~429–432) are untouched (same `role="tab"`, same accessible names — required by the existing `GameDetails.test.tsx` contract).

- [ ] **Step 1: Write the failing test**

Add to `GameDetails.test.tsx`:

```tsx
describe('GameDetails recent-performance panel', () => {
  it('renders the segmented Last 5 / Home / Away control and GameLogTable headers', () => {
    render(
      <MemoryRouter initialEntries={['/game-details/mlb/boston-red-sox-vs-athletics-2026-07-28']}>
        <GameDetails
          game={fakeMlbGame}
          sportKey="baseball_mlb"
          homeTeamHistory={{ games: [], count: 0, sport: 'mlb', limit: 5 }}
          awayTeamHistory={{ games: [], count: 0, sport: 'mlb', limit: 5 }}
          headToHeadHistory={{ games: [], count: 0, sport: 'mlb', limit: 5 }}
        />
      </MemoryRouter>
    );

    expect(screen.getByRole('button', { name: 'Last 5' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Home Last 5/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Away Last 5/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameDetails.test.tsx --watchAll=false`
Expected: FAIL — no element with role `button` named "Last 5" (still an MUI `Tab`, `role="tab"`, not `"button"`)

- [ ] **Step 3: Replace the `HistoricalGames` import and the 7 call sites**

```tsx
import GameLogTable from "./GameLogTable";
```

(remove `import HistoricalGames from "./HistoricalGames";`)

Each of the 7 `<HistoricalGames ... />` elements in the "Recent Performance" tab becomes `<GameLogTable ... />` with the identical prop list it already has, for example (first one, inside the `historicalSubTab === 0` branch):

```tsx
<GameLogTable
  title={`${homeTeamName} - Last ${gamesLimit} Games`}
  games={homeTeamHistory?.games || []}
  loading={homeTeamHistory === null}
  teamName={convertTeamNameBySport(sportKey, homeTeamName)}
  sportType={getSportType(sportKey)}
  sport={teamPageSport}
  defaultExpanded={true}
/>
```

Apply the same mechanical change (component name + `defaultExpanded`) to the other 6 call sites. `defaultExpanded` is `true` for the first table in each of the 3 branches' first position and for every H2H table (desktop-style "all open" default matches today's behavior, which already defaults every `HistoricalGames` instance to `expanded: true`); pass `defaultExpanded={true}` on all 7 for this task — Task 12 is where mobile-specific collapsing could be revisited if product asks for it later, but the spec's "Desktop default: all 3 open" is satisfied by leaving every instance's default as `true`, same as today.

- [ ] **Step 4: Replace the MUI `Tabs` sub-tab control with a segmented control**

Replace the `<Tabs value={historicalSubTab} onChange={handleHistoricalSubTabChange} ...>` block (the one with `<Tab label={`Last ${gamesLimit}`} />` etc.) with:

```tsx
<Box
  sx={{
    display: 'inline-flex',
    bgcolor: '#f1f3ef',
    borderRadius: '10px',
    p: '4px',
    gap: '4px',
    mb: 2,
  }}
>
  {[
    { value: 0, label: `Last ${gamesLimit}` },
    { value: 1, label: `${homeTeamName} Home Last ${gamesLimit}` },
    { value: 2, label: `${awayTeamName} Away Last ${gamesLimit}` },
  ].map((opt) => (
    <Box
      key={opt.value}
      component="button"
      onClick={() => setHistoricalSubTab(opt.value)}
      sx={{
        all: 'unset',
        cursor: 'pointer',
        fontSize: '0.75rem',
        fontWeight: 600,
        px: '14px',
        py: '7px',
        borderRadius: '7px',
        textAlign: 'center',
        bgcolor: historicalSubTab === opt.value ? '#fff' : 'transparent',
        boxShadow: historicalSubTab === opt.value ? '0 1px 2px rgba(0,0,0,.12)' : 'none',
      }}
    >
      {opt.label}
    </Box>
  ))}
</Box>
```

This replaces `handleHistoricalSubTabChange` usage with the inline `onClick` above — the `handleHistoricalSubTabChange` function (lines ~344-346) and the now-unused `Tabs`/`Tab` imports for this block can stay imported since `Tabs`/`Tab` are still used by the main Recent Performance/Player Props tabs elsewhere in the file; only remove `handleHistoricalSubTabChange` if nothing else references it (confirm with a grep before deleting).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameDetails.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 6: Run the full `GameDetails.test.tsx` file to confirm the pre-existing player-props test still passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameDetails.test.tsx --watchAll=false`
Expected: PASS — both the pre-existing "fetches MLB player props using game.game_id" test and the new segmented-control test pass, confirming the main `Tabs`/`Tab` (role="tab", name "Player Props") were left untouched.

- [ ] **Step 7: Commit**

```bash
cd getstam-react && git add src/components/GameDetails.tsx src/components/GameDetails.test.tsx
git commit -m "$(cat <<'EOF'
Wire GameLogTable and the segmented sub-tab control into GameDetails

Recent Performance now renders GameLogTable instead of HistoricalGames,
and the Last 5 / Home Last 5 / Away Last 5 sub-tab is a segmented
control instead of MUI Tabs, matching the new design. Main Recent
Performance / Player Props tabs are unchanged.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Shared prop-streak derivation + `MLBPlayerPropsTable` restyle

**Files:**
- Create: `getstam-react/src/utils/propStreaks.ts`
- Create: `getstam-react/src/components/PropStreakDots.tsx`
- Create: `getstam-react/src/utils/propStreaks.test.ts`
- Modify: `getstam-react/src/components/MLBPlayerPropsTable.tsx`
- Test: Create `getstam-react/src/components/MLBPlayerPropsTable.test.tsx`

**Interfaces:**
- Produces: `computePropStreak(historical: any[], actualKey: string, oddsKey: string): PropStreak | null` from `utils/propStreaks.ts`, where
  ```ts
  export interface PropStreak {
    direction: 'over' | 'under';
    count: number;
    continuation_rate: number;
    sample_size: number;
    recentHits: boolean[]; // up to 5, most-recent-first; true = matched `direction`
  }
  ```
- Produces: `PropStreakDots` component, props `{ hits: boolean[] }`, default export — renders up to 5 small dots, filled (`gameDetailsTokens.hit.dot`) for `true`, outlined gray for `false`.
- Consumes: `gameDetailsTokens` (Task 1). `MLBPlayerPropsTable`'s existing `players`/`tableType` props are unchanged.

- [ ] **Step 1: Write the failing test for `computePropStreak`**

```ts
import { computePropStreak } from './propStreaks';

describe('computePropStreak', () => {
  it('counts the current consecutive run in the most-recent direction', () => {
    const historical = [
      { actual_x: 2, odds_x: 1 }, // over
      { actual_x: 3, odds_x: 1 }, // over
      { actual_x: 0, odds_x: 1 }, // under (streak break)
      { actual_x: 2, odds_x: 1 }, // over
    ];
    const result = computePropStreak(historical, 'actual_x', 'odds_x');
    expect(result).toEqual({
      direction: 'over',
      count: 2,
      continuation_rate: 0.75,
      sample_size: 4,
      recentHits: [true, true, false, true],
    });
  });

  it('returns null when there is no usable historical data', () => {
    expect(computePropStreak([], 'actual_x', 'odds_x')).toBeNull();
    expect(computePropStreak([{ actual_x: null, odds_x: 1 }], 'actual_x', 'odds_x')).toBeNull();
  });

  it('returns null when the most recent game is an exact push', () => {
    expect(computePropStreak([{ actual_x: 1, odds_x: 1 }], 'actual_x', 'odds_x')).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/utils/propStreaks.test.ts --watchAll=false`
Expected: FAIL — `Cannot find module './propStreaks'`

- [ ] **Step 3: Write `utils/propStreaks.ts`**

```ts
export interface PropStreak {
  direction: 'over' | 'under';
  count: number;
  continuation_rate: number;
  sample_size: number;
  // Up to 5 entries, most-recent-first; true = that game matched `direction`.
  recentHits: boolean[];
}

type Direction = 'over' | 'under' | null;

const directionOf = (actual: any, odds: any): Direction => {
  if (actual == null || odds == null || isNaN(Number(actual)) || isNaN(Number(odds))) return null;
  if (Number(actual) > Number(odds)) return 'over';
  if (Number(actual) < Number(odds)) return 'under';
  return null; // push
};

// Derives a "streak" purely from historical rows already present on each
// player-prop response (no new data) — the current direction's run length,
// how often that direction has held across the full sample, and a last-5
// hit/miss strip for it.
export function computePropStreak(historical: any[], actualKey: string, oddsKey: string): PropStreak | null {
  const rows = historical.filter((h) => directionOf(h[actualKey], h[oddsKey]) != null);
  if (rows.length === 0) return null;

  const direction = directionOf(rows[0][actualKey], rows[0][oddsKey]);
  if (!direction) return null;

  let count = 0;
  for (const row of rows) {
    if (directionOf(row[actualKey], row[oddsKey]) === direction) count++;
    else break;
  }

  const matches = rows.filter((row) => directionOf(row[actualKey], row[oddsKey]) === direction).length;
  const recentHits = rows.slice(0, 5).map((row) => directionOf(row[actualKey], row[oddsKey]) === direction);

  return {
    direction,
    count,
    continuation_rate: matches / rows.length,
    sample_size: rows.length,
    recentHits,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/utils/propStreaks.test.ts --watchAll=false`
Expected: PASS

- [ ] **Step 5: Write `components/PropStreakDots.tsx`**

```tsx
import React from 'react';
import { Box } from '@mui/material';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';

interface PropStreakDotsProps {
  hits: boolean[];
}

const PropStreakDots: React.FC<PropStreakDotsProps> = ({ hits }) => (
  <Box sx={{ display: 'flex', gap: '4px' }}>
    {hits.map((hit, i) => (
      <Box
        key={i}
        sx={{
          width: 9,
          height: 9,
          borderRadius: '50%',
          bgcolor: hit ? tokens.hit.dot : 'transparent',
          border: hit ? 'none' : `1.5px solid ${tokens.text.muted}`,
        }}
      />
    ))}
  </Box>
);

export default PropStreakDots;
```

- [ ] **Step 6: Write the failing test for the restyled `MLBPlayerPropsTable`**

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import MLBPlayerPropsTable from './MLBPlayerPropsTable';

const players = {
  'C. Yelich': {
    batter_hits: { point: 0.5 },
    historical: [
      { short_game_date: '10/15', odds_batter_hits: 1, actual_batter_hits: 2 },
      { short_game_date: '10/14', odds_batter_hits: 1, actual_batter_hits: 2 },
      { short_game_date: '10/13', odds_batter_hits: 1, actual_batter_hits: 0 },
    ],
  },
};

describe('MLBPlayerPropsTable Player/Prop/Streak/Continues/Last 5 layout', () => {
  it('renders one row per player-prop with the derived streak and continuation rate', () => {
    render(<MLBPlayerPropsTable players={players} tableType="batter" />);
    expect(screen.getByText('C. Yelich')).toBeInTheDocument();
    expect(screen.getByText('Over 0.5 Hits')).toBeInTheDocument();
    expect(screen.getByText('2 straight Overs')).toBeInTheDocument();
    expect(screen.getByText('67% (2/3)')).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/MLBPlayerPropsTable.test.tsx --watchAll=false`
Expected: FAIL — "Over 0.5 Hits" / "2 straight Overs" not found (table still renders the old 3-market-columns-per-player layout)

- [ ] **Step 8: Rewrite `components/MLBPlayerPropsTable.tsx`**

```tsx
import React from 'react';
import { Box, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import { computePropStreak } from '../utils/propStreaks';
import PropStreakDots from './PropStreakDots';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';

type MLBPlayerPropsTableProps = {
  players: any;
  tableType: 'batter' | 'pitcher';
};

const BATTER_COLUMNS = [
  { label: 'Hits', marketKey: 'batter_hits', oddsKey: 'odds_batter_hits', actualKey: 'actual_batter_hits' },
  { label: 'HR', marketKey: 'batter_home_runs', oddsKey: 'odds_batter_home_runs', actualKey: 'actual_batter_home_runs' },
  { label: 'RBI', marketKey: 'batter_rbis', oddsKey: 'odds_batter_rbi', actualKey: 'actual_batter_rbi' },
];

const PITCHER_COLUMNS = [
  { label: 'Strikeouts', marketKey: 'pitcher_strikeouts', oddsKey: 'odds_pitcher_strikeouts', actualKey: 'actual_pitcher_strikeouts' },
  { label: 'Earned Runs', marketKey: 'pitcher_earned_runs', oddsKey: 'odds_pitcher_earned_runs', actualKey: 'actual_pitcher_earned_runs' },
  { label: 'Hits Allowed', marketKey: 'pitcher_hits_allowed', oddsKey: 'odds_pitcher_hits_allowed', actualKey: 'actual_pitcher_hits_allowed' },
];

const MLBPlayerPropsTable: React.FC<MLBPlayerPropsTableProps> = ({ players, tableType }) => {
  const columns = tableType === 'batter' ? BATTER_COLUMNS : PITCHER_COLUMNS;

  let playersData: { [key: string]: any };
  if (Array.isArray(players)) {
    playersData = {};
    players.forEach((player, index) => {
      const playerName = player.player_name || `Player ${index + 1}`;
      playersData[playerName] = player;
    });
  } else if (players && typeof players === 'object') {
    playersData = players;
  } else {
    playersData = {};
  }

  type Row = {
    player: string;
    propLabel: string;
    point: number;
    direction: 'over' | 'under';
    count: number;
    continuation_rate: number;
    sample_size: number;
    recentHits: boolean[];
  };

  const rows: Row[] = [];
  Object.entries(playersData).forEach(([player, data]: [string, any]) => {
    columns.forEach((col) => {
      const point = data?.[col.marketKey]?.point;
      const historical = Array.isArray(data?.historical) ? data.historical : [];
      if (point == null) return;
      const streak = computePropStreak(historical, col.actualKey, col.oddsKey);
      if (!streak) return;
      rows.push({
        player,
        propLabel: `${streak.direction === 'over' ? 'Over' : 'Under'} ${point} ${col.label}`,
        point,
        ...streak,
      });
    });
  });

  if (rows.length === 0) {
    return (
      <Paper elevation={2} sx={{ p: 2, mb: 2, border: `1px solid ${tokens.cardBorder}` }}>
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body1" color="text.secondary">No player data available</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This could be due to server issues or no historical data for these players
          </Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper elevation={0} sx={{ border: `1px solid ${tokens.cardBorder}`, borderRadius: `${tokens.cardRadius}px`, overflow: 'hidden' }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Player</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Prop</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Streak</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Continues</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Last 5</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={`${row.player}-${row.propLabel}-${i}`} sx={{ '&:hover': { bgcolor: tokens.subtlePanelBg } }}>
              <TableCell sx={{ fontSize: '0.8125rem', fontWeight: 600, borderTop: `1px solid ${tokens.borders.lighter}` }}>{row.player}</TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>{row.propLabel}</TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                {row.count} straight {row.direction === 'over' ? 'Overs' : 'Unders'}
              </TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                {Math.round(row.continuation_rate * 100)}% ({Math.round(row.continuation_rate * row.sample_size)}/{row.sample_size})
              </TableCell>
              <TableCell sx={{ borderTop: `1px solid ${tokens.borders.lighter}` }}>
                <PropStreakDots hits={row.recentHits} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
};

export default MLBPlayerPropsTable;
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/MLBPlayerPropsTable.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
cd getstam-react && git add src/utils/propStreaks.ts src/utils/propStreaks.test.ts src/components/PropStreakDots.tsx src/components/MLBPlayerPropsTable.tsx src/components/MLBPlayerPropsTable.test.tsx
git commit -m "$(cat <<'EOF'
Restyle MLBPlayerPropsTable to Player/Prop/Streak/Continues/Last 5

Derives streak length, continuation rate, and a last-5 hit strip
client-side from each player's existing historical rows — no new data —
via a new shared utils/propStreaks helper reused by the NFL/NBA tables
in the next two tasks.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: `NFLPlayerPropsTable` restyle

**Files:**
- Modify: `getstam-react/src/components/NFLPlayerPropsTable.tsx`
- Test: Create `getstam-react/src/components/NFLPlayerPropsTable.test.tsx`

**Interfaces:**
- Consumes: `computePropStreak` (`utils/propStreaks.ts`), `PropStreakDots` (Task 9). `NFLPlayerPropsTable`'s existing `players` prop is unchanged.

- [ ] **Step 1: Write the failing test**

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import NFLPlayerPropsTable from './NFLPlayerPropsTable';

const players = {
  'J. Jefferson': {
    player_reception_yds: { point: 75.5 },
    historical: [
      { short_game_date: '10/15', odds_player_reception_yds: 75.5, actual_player_reception_yds: 90 },
      { short_game_date: '10/8', odds_player_reception_yds: 72.5, actual_player_reception_yds: 85 },
    ],
  },
};

describe('NFLPlayerPropsTable Player/Prop/Streak/Continues/Last 5 layout', () => {
  it('renders one row per player-prop with the derived streak', () => {
    render(<NFLPlayerPropsTable players={players} />);
    expect(screen.getByText('J. Jefferson')).toBeInTheDocument();
    expect(screen.getByText('Over 75.5 Rec Yds')).toBeInTheDocument();
    expect(screen.getByText('2 straight Overs')).toBeInTheDocument();
    expect(screen.getByText('100% (2/2)')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/NFLPlayerPropsTable.test.tsx --watchAll=false`
Expected: FAIL — "Over 75.5 Rec Yds" not found

- [ ] **Step 3: Rewrite `components/NFLPlayerPropsTable.tsx`**

Same structure as the restyled `MLBPlayerPropsTable` (Task 9 Step 8), with this file's own column set and no `tableType` prop:

```tsx
import React from 'react';
import { Box, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import { computePropStreak } from '../utils/propStreaks';
import PropStreakDots from './PropStreakDots';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';

type NFLPlayerPropsTableProps = {
  players: any;
};

const COLUMNS = [
  { label: 'Pass Yds', marketKey: 'player_pass_yds', oddsKey: 'odds_player_pass_yds', actualKey: 'actual_player_pass_yds' },
  { label: 'Pass TDs', marketKey: 'player_pass_tds', oddsKey: 'odds_player_pass_tds', actualKey: 'actual_player_pass_tds' },
  { label: 'Rush Yds', marketKey: 'player_rush_yds', oddsKey: 'odds_player_rush_yds', actualKey: 'actual_player_rush_yds' },
  { label: 'Rec Yds', marketKey: 'player_reception_yds', oddsKey: 'odds_player_reception_yds', actualKey: 'actual_player_reception_yds' },
  { label: 'Receptions', marketKey: 'player_receptions', oddsKey: 'odds_player_receptions', actualKey: 'actual_player_receptions' },
  { label: 'Any TD', marketKey: 'player_anytime_td', oddsKey: 'odds_player_anytime_td', actualKey: 'actual_player_anytime_td' },
];

const NFLPlayerPropsTable: React.FC<NFLPlayerPropsTableProps> = ({ players }) => {
  let playersData: { [key: string]: any };
  if (Array.isArray(players)) {
    playersData = {};
    players.forEach((player, index) => {
      const playerName = player.player_name || `Player ${index + 1}`;
      playersData[playerName] = player;
    });
  } else if (players && typeof players === 'object') {
    playersData = players;
  } else {
    playersData = {};
  }

  type Row = {
    player: string;
    propLabel: string;
    direction: 'over' | 'under';
    count: number;
    continuation_rate: number;
    sample_size: number;
    recentHits: boolean[];
  };

  const rows: Row[] = [];
  Object.entries(playersData).forEach(([player, data]: [string, any]) => {
    COLUMNS.forEach((col) => {
      const point = data?.[col.marketKey]?.point;
      const historical = Array.isArray(data?.historical) ? data.historical : [];
      if (point == null) return;
      const streak = computePropStreak(historical, col.actualKey, col.oddsKey);
      if (!streak) return;
      rows.push({
        player,
        propLabel: `${streak.direction === 'over' ? 'Over' : 'Under'} ${point} ${col.label}`,
        ...streak,
      });
    });
  });

  if (rows.length === 0) {
    return (
      <Paper elevation={2} sx={{ p: 2, mb: 2, border: `1px solid ${tokens.cardBorder}` }}>
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body1" color="text.secondary">No player data available</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This could be due to server issues or no historical data for these players
          </Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper elevation={0} sx={{ border: `1px solid ${tokens.cardBorder}`, borderRadius: `${tokens.cardRadius}px`, overflow: 'hidden' }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Player</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Prop</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Streak</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Continues</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Last 5</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={`${row.player}-${row.propLabel}-${i}`} sx={{ '&:hover': { bgcolor: tokens.subtlePanelBg } }}>
              <TableCell sx={{ fontSize: '0.8125rem', fontWeight: 600, borderTop: `1px solid ${tokens.borders.lighter}` }}>{row.player}</TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>{row.propLabel}</TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                {row.count} straight {row.direction === 'over' ? 'Overs' : 'Unders'}
              </TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                {Math.round(row.continuation_rate * 100)}% ({Math.round(row.continuation_rate * row.sample_size)}/{row.sample_size})
              </TableCell>
              <TableCell sx={{ borderTop: `1px solid ${tokens.borders.lighter}` }}>
                <PropStreakDots hits={row.recentHits} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
};

export default NFLPlayerPropsTable;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/NFLPlayerPropsTable.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd getstam-react && git add src/components/NFLPlayerPropsTable.tsx src/components/NFLPlayerPropsTable.test.tsx
git commit -m "$(cat <<'EOF'
Restyle NFLPlayerPropsTable to Player/Prop/Streak/Continues/Last 5

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: `PlayerPropsTable` (NBA) restyle

**Files:**
- Modify: `getstam-react/src/components/PlayerPropsTable.tsx`
- Test: Create `getstam-react/src/components/PlayerPropsTable.test.tsx`

**Interfaces:**
- Consumes: `computePropStreak` (`utils/propStreaks.ts`), `PropStreakDots` (Task 9). `PlayerPropsTable`'s existing `players` prop is unchanged.

- [ ] **Step 1: Write the failing test**

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import PlayerPropsTable from './PlayerPropsTable';

const players = {
  'L. Doncic': {
    player_points: { point: 28.5 },
    historical: [
      { short_game_date: '10/15', odds_player_points: 28.5, actual_player_points: 33 },
      { short_game_date: '10/13', odds_player_points: 27.5, actual_player_points: 19 },
      { short_game_date: '10/11', odds_player_points: 27.5, actual_player_points: 31 },
    ],
  },
};

describe('PlayerPropsTable (NBA) Player/Prop/Streak/Continues/Last 5 layout', () => {
  it('renders one row per player-prop with the derived streak', () => {
    render(<PlayerPropsTable players={players} />);
    expect(screen.getByText('L. Doncic')).toBeInTheDocument();
    expect(screen.getByText('Over 28.5 Points')).toBeInTheDocument();
    expect(screen.getByText('1 straight Overs')).toBeInTheDocument();
    expect(screen.getByText('67% (2/3)')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/PlayerPropsTable.test.tsx --watchAll=false`
Expected: FAIL — "Over 28.5 Points" not found

- [ ] **Step 3: Rewrite `components/PlayerPropsTable.tsx`**

Same structure as Tasks 9–10, with this file's own column set:

```tsx
import React from 'react';
import { Box, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import { computePropStreak } from '../utils/propStreaks';
import PropStreakDots from './PropStreakDots';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';

const COLUMNS = [
  { label: 'Points', marketKey: 'player_points', oddsKey: 'odds_player_points', actualKey: 'actual_player_points' },
  { label: 'Assists', marketKey: 'player_assists', oddsKey: 'odds_player_assists', actualKey: 'actual_player_assists' },
  { label: 'Rebounds', marketKey: 'player_rebounds', oddsKey: 'odds_player_rebounds', actualKey: 'actual_player_rebounds' },
  { label: 'Threes', marketKey: 'player_threes', oddsKey: 'odds_player_threes', actualKey: 'actual_player_threes' },
];

const PlayerPropsTable: React.FC<{ players: any }> = ({ players }) => {
  let playersData: { [key: string]: any };
  if (Array.isArray(players)) {
    playersData = {};
    players.forEach((player, index) => {
      const playerName = player.player_name || `Player ${index + 1}`;
      playersData[playerName] = player;
    });
  } else if (players && typeof players === 'object') {
    playersData = players;
  } else {
    console.error('Invalid players format:', players);
    playersData = {};
  }

  type Row = {
    player: string;
    propLabel: string;
    direction: 'over' | 'under';
    count: number;
    continuation_rate: number;
    sample_size: number;
    recentHits: boolean[];
  };

  const rows: Row[] = [];
  Object.entries(playersData).forEach(([player, data]: [string, any]) => {
    COLUMNS.forEach((col) => {
      const point = data?.[col.marketKey]?.point;
      const historical = Array.isArray(data?.historical) ? data.historical : [];
      if (point == null) return;
      const streak = computePropStreak(historical, col.actualKey, col.oddsKey);
      if (!streak) return;
      rows.push({
        player,
        propLabel: `${streak.direction === 'over' ? 'Over' : 'Under'} ${point} ${col.label}`,
        ...streak,
      });
    });
  });

  if (rows.length === 0) {
    return (
      <Paper elevation={2} sx={{ p: 2, mb: 2, border: `1px solid ${tokens.cardBorder}` }}>
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body1" color="text.secondary">No player data available</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This could be due to server issues or no historical data for these players
          </Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper elevation={0} sx={{ border: `1px solid ${tokens.cardBorder}`, borderRadius: `${tokens.cardRadius}px`, overflow: 'hidden' }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Player</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Prop</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Streak</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Continues</TableCell>
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Last 5</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={`${row.player}-${row.propLabel}-${i}`} sx={{ '&:hover': { bgcolor: tokens.subtlePanelBg } }}>
              <TableCell sx={{ fontSize: '0.8125rem', fontWeight: 600, borderTop: `1px solid ${tokens.borders.lighter}` }}>{row.player}</TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>{row.propLabel}</TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                {row.count} straight {row.direction === 'over' ? 'Overs' : 'Unders'}
              </TableCell>
              <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                {Math.round(row.continuation_rate * 100)}% ({Math.round(row.continuation_rate * row.sample_size)}/{row.sample_size})
              </TableCell>
              <TableCell sx={{ borderTop: `1px solid ${tokens.borders.lighter}` }}>
                <PropStreakDots hits={row.recentHits} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
};

export default PlayerPropsTable;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/PlayerPropsTable.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd getstam-react && git add src/components/PlayerPropsTable.tsx src/components/PlayerPropsTable.test.tsx
git commit -m "$(cat <<'EOF'
Restyle PlayerPropsTable (NBA) to Player/Prop/Streak/Continues/Last 5

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Breadcrumb + wire `MatchupOddsCard` into `GameDetails.tsx`

**Files:**
- Modify: `getstam-react/src/components/GameDetails.tsx`
- Modify: `getstam-react/src/pages/GameDetailsPage.tsx`
- Modify: `getstam-react/src/components/GameDetails.test.tsx`

**Interfaces:**
- Consumes: `MatchupOddsCard` (Task 2), `gameDetailsTokens` (Task 1).
- Changes: `GameDetails.tsx`'s `<GameOdds game={game} pitcherData={pitcherData} sport={teamPageSport} />` (inside the `<Paper>` wrapper) becomes `<MatchupOddsCard game={game} pitcherData={pitcherData} sport={teamPageSport} />`, and the surrounding `<Paper>`'s translucent styling is removed (the card now supplies its own background/border). `GameDetailsPage.tsx` gains a breadcrumb row above `TrendAnalysisSection`, and passes the real `sportKey` prop through to it (closing the gap left by Task 3's default).

- [ ] **Step 1: Write the failing test**

Add to `GameDetails.test.tsx`:

```tsx
describe('GameDetails matchup card', () => {
  it('renders MatchupOddsCard (TeamLogo abbreviations) instead of the old GameOdds card', () => {
    render(
      <MemoryRouter initialEntries={['/game-details/mlb/boston-red-sox-vs-athletics-2026-07-28']}>
        <GameDetails game={fakeMlbGame} sportKey="baseball_mlb" />
      </MemoryRouter>
    );
    expect(screen.getByText('ATH')).toBeInTheDocument();
    expect(screen.getByText('BOS')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameDetails.test.tsx --watchAll=false`
Expected: FAIL — no "ATH"/"BOS" text (still rendering plain team names via `GameOdds`, no `TeamLogo`)

- [ ] **Step 3: Swap `GameOdds` for `MatchupOddsCard` in `GameDetails.tsx`**

```tsx
import MatchupOddsCard from "./MatchupOddsCard";
```

(remove `import GameOdds from "./GameOdds";`)

Replace:

```tsx
<Paper elevation={0} sx={{
  p: { xs: 2, sm: 3 },
  mt: 4,
  maxWidth: 900,
  mx: { xs: 1, sm: "auto" },
  backgroundColor: "transparent"
}}>
  {/* Odds section */}
  <GameOdds game={game} pitcherData={pitcherData} sport={teamPageSport} />
</Paper>
```

with:

```tsx
<Box sx={{ mt: 4, maxWidth: 900, mx: "auto", px: { xs: 1, sm: 0 } }}>
  <MatchupOddsCard game={game} pitcherData={pitcherData} sport={teamPageSport} />
</Box>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameDetails.test.tsx --watchAll=false`
Expected: PASS

- [ ] **Step 5: Add the breadcrumb and real `sportKey` to `GameDetailsPage.tsx`**

Add the import:

```tsx
import { gameDetailsTokens as tokens } from "../utils/gameDetailsTokens";
```

Just above the `<TrendAnalysisSection ...>` element in the final `return`, add:

```tsx
<Box sx={{ display: { xs: 'none', sm: 'block' }, maxWidth: 900, mx: 'auto', px: { xs: 1, sm: 0 }, pt: 2, fontSize: '0.75rem', color: tokens.text.secondary }}>
  {displaySport} › Games ›{' '}
  <Box component="span" sx={{ color: tokens.text.primary, fontWeight: 600 }}>
    {awayTeam} vs {homeTeam}
  </Box>
</Box>
```

(`Box` is already imported in this file; `displaySport`, `awayTeam`, `homeTeam` already exist as local `const`s a few lines above.)

Pass the real `sportKey` to `TrendAnalysisSection` (closing the gap left by Task 3's default value):

```tsx
<TrendAnalysisSection
  gameTrends={gameTrends}
  loading={trendsLoading}
  game={gameData}
  minTrendLength={minTrendLength}
  dataSinceYear={dataSinceYear}
  sportKey={sportKey || "baseball_mlb"}
/>
```

- [ ] **Step 6: Run the full test suite for all touched files to confirm no regressions**

Run: `cd getstam-react && CI=true npx react-scripts test src/components/GameDetails.test.tsx src/components/TrendAnalysisSection.test.tsx src/components/MatchupOddsCard.test.tsx src/components/GameLogTable.test.tsx src/components/TeamLogo.test.tsx src/components/PlayerStreakHighlight.test.tsx src/components/MLBPlayerPropsTable.test.tsx src/components/NFLPlayerPropsTable.test.tsx src/components/PlayerPropsTable.test.tsx src/utils/teamColors.test.ts src/utils/propStreaks.test.ts --watchAll=false`
Expected: PASS — every test file from Tasks 1–12

- [ ] **Step 7: Manually verify in the browser**

Run: `cd getstam-react && npm start` (and, in another terminal, `FLASK_ENV=development python app.py` from the repo root so the API is live), then open an MLB game's `/game-details/mlb/...` URL and confirm: team-colored circle logos appear in the matchup card, the 3 trend cards + collision card render above "More trends", the player-streak highlight line appears above the full streaks strip, the Last 5/Home/Away segmented control switches `GameLogTable`s, and the Player Props sub-tab shows the new Player/Prop/Streak/Continues/Last 5 columns. Also check an NFL and an NBA game's details page to confirm the shell renders correctly for sports outside the MLB mock.

- [ ] **Step 8: Commit**

```bash
cd getstam-react && git add src/components/GameDetails.tsx src/pages/GameDetailsPage.tsx src/components/GameDetails.test.tsx
git commit -m "$(cat <<'EOF'
Wire MatchupOddsCard and the page breadcrumb into Game Details

Final integration step: GameDetails now renders MatchupOddsCard instead
of GameOdds (which stays unchanged for GamesPage/TeamPage), and
GameDetailsPage gains a breadcrumb and passes its real sportKey through
to TrendAnalysisSection for team-colored trend cards.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1 → TeamLogo/team colors; Task 2 → matchup+odds card; Tasks 3–5 → Game Trends (3 cards) + Collision card + restyled remaining list; Task 6 → Player Prop Trends highlight; Tasks 7–8 → tabbed panel/game-log tables + segmented control; Tasks 9–11 → the three player-props tables; Task 12 → breadcrumb + final wiring. All sections of the spec (`docs/superpowers/specs/2026-10-23-game-details-redesign-design.md`) map to a task.
- **Out-of-scope items respected:** `GameOdds.tsx`/`HistoricalGames.tsx` are never edited (grep for `HistoricalGames` and `GameOdds` imports after Task 12 to confirm only `GamesPage.tsx`/`TeamPage.tsx`/`BlogPostPage.tsx` still import them). No new routes are added; the "View all" button and trend-card chevrons render without navigation. NCAAF/NCAAB get the neutral fallback automatically via `getTeamColors`.
- **Type consistency check:** `TeamLogo`'s props (`sportKey`, `teamName`, `size`, `border`) are used identically across Tasks 2, 4, 7. `getTeamColors(dbSport, teamName)` signature is consistent everywhere it's called (Tasks 1, 3, 4). `computePropStreak`/`PropStreak`/`PropStreakDots` (Task 9) are reused unchanged in Tasks 10–11. `GameLogTableProps` (Task 7) matches the call sites added in Task 8 exactly.
