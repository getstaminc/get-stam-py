import React from 'react';
import { Link } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import { getTeamPageLink } from '../utils/teamSlugUtils';
import TeamLogo from './TeamLogo';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';

// Sports with a team-page slug map (see teamSlugUtils.ts's SPORT_MAPS) -- soccer/
// international sports (e.g. World Cup) don't have one yet, so avoid linking to a
// team page that doesn't exist for them.
const TEAM_PAGE_SPORTS = new Set(['nba', 'nfl', 'mlb', 'nhl', 'ncaaf', 'ncaab']);

// This header renders at very different widths depending on context -- a full
// ~900px single card on Game Details, but as little as ~420px per card in a
// list grid (GamesPage, the home page trends feed). MUI's xs/sm breakpoints key
// off the *viewport*, not this header's own rendered width, so they can't tell
// those two apart (both happen on the same desktop-width window) -- that's
// what let a long team name's wrapped second line collide with the logo
// circle in a narrow list context. A CSS container query reacts to the
// header's actual width instead, so the stacked/centered layout applies
// whenever the card itself is narrow, regardless of the browser window size.
const WIDE_HEADER_QUERY = '@container matchup-card (min-width: 560px)';

// Spread onto the sx of whichever Box wraps a MatchupTeamHeader (the card's
// own root) -- establishes the containment context the query above measures.
export const MATCHUP_CARD_CONTAINER_SX = {
  containerType: 'inline-size' as const,
  containerName: 'matchup-card',
};

const formatRecord = (record?: { wins: number; losses: number; ties: number }): string | null => {
  if (!record) return null;
  const { wins, losses, ties } = record;
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
};

export interface MatchupTeamHeaderProps {
  team: string;
  side: 'home' | 'away';
  sport?: string;
  record?: { wins: number; losses: number; ties: number };
  pitcher?: string;
  pitcherStats?: string;
}

const MatchupTeamHeader: React.FC<MatchupTeamHeaderProps> = ({ team, side, sport, record, pitcher, pitcherStats }) => {
  const sportKeyForLogo = sport || 'mlb';
  const formattedRecord = formatRecord(record);
  const metaParts = [formattedRecord, pitcherStats, side === 'home' ? 'Home' : 'Away'].filter(Boolean);
  const canLink = !!sport && TEAM_PAGE_SPORTS.has(sport);

  return (
    <Box
      data-testid={`team-header-${side}`}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 0.75,
        // flexDirection: row-reverse flips which edge "flex-start"/"flex-end"
        // point to, so flex-start is what pushes a reversed row to the right.
        justifyContent: 'flex-start',
        textAlign: 'center',
        flexDirection: 'column',
        [WIDE_HEADER_QUERY]: {
          gap: 2,
          textAlign: side === 'away' ? 'right' : 'left',
          flexDirection: side === 'away' ? 'row-reverse' : 'row',
        },
        // Without this, a flex item's default min-width is its content's
        // intrinsic width, not 0 -- so the text column below would refuse to
        // shrink/wrap and push this whole header past its container's bounds.
        minWidth: 0,
      }}
    >
      <TeamLogo sportKey={sportKeyForLogo} teamName={team} size={52} />
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
          alignItems: 'center',
          [WIDE_HEADER_QUERY]: { alignItems: 'stretch' },
          minWidth: 0,
        }}
      >
        <Typography sx={{ fontSize: '1.25rem', fontWeight: 700 }}>
          {canLink ? (
            <Link to={getTeamPageLink(sport!, team)} style={{ textDecoration: 'none', color: 'inherit' }}>
              {team}
            </Link>
          ) : (
            team
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

export default MatchupTeamHeader;
