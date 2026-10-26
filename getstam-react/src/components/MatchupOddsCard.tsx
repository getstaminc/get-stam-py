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
          // flexDirection: row-reverse flips which edge "flex-start"/"flex-end"
          // point to, so flex-start is what pushes a reversed row to the right.
          justifyContent: 'flex-start',
          // The mirrored (logo-on-right, text right-aligned) away layout only
          // makes sense in the desktop side-by-side grid. On mobile everything
          // stacks into one full-width column, so a mirrored away row stretches
          // its logo and text to opposite edges of the whole card — stay
          // left-aligned like the home row there instead.
          textAlign: { xs: 'left', sm: side === 'away' ? 'right' : 'left' },
          flexDirection: { xs: 'row', sm: side === 'away' ? 'row-reverse' : 'row' },
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
        gridTemplateColumns: { xs: '1fr 64px 1fr', sm: '1fr 90px 1fr' },
        gap: 0.5,
        alignItems: 'center',
        px: { xs: 2, sm: 3 },
        py: 1.25,
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
