import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Typography } from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { BaseGame, NFLGame, MLBGame, SoccerGame, HistoricalGame, SportType } from '../types/gameTypes';
import { dbNameToSlug } from '../utils/teamSlugUtils';
import TeamLogo from './TeamLogo';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';
import Legend from './common/Legend';

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

const getLineLabel = (sportType: SportType): string => {
  if (sportType === 'mlb' || sportType === 'nhl') return 'Line';
  return 'Spread';
};

// Brighter than the actual hit/miss cell-fill tokens on purpose — these are
// small swatches in a tooltip popover, not a full table cell, so they need
// more saturation to read clearly at that size.
const LEGEND_SWATCH_HIT = '#c8e6c9';
const LEGEND_SWATCH_MISS = '#ffcdd2';
const LEGEND_SWATCH_PUSH = '#e0e0e0';

const TEAM_LEGEND_ITEMS = [
  { color: LEGEND_SWATCH_HIT, label: 'Win' },
  { color: LEGEND_SWATCH_MISS, label: 'Loss' },
  { color: LEGEND_SWATCH_PUSH, label: 'Push' },
];

const TOTAL_LEGEND_ITEMS = [
  { color: LEGEND_SWATCH_HIT, label: 'Went Over' },
  { color: LEGEND_SWATCH_MISS, label: 'Went Under' },
  { color: LEGEND_SWATCH_PUSH, label: 'Push' },
];

const SPREAD_LEGEND_ITEMS = [
  { color: LEGEND_SWATCH_HIT, label: 'Covered' },
  { color: LEGEND_SWATCH_MISS, label: "Didn't Cover" },
  { color: LEGEND_SWATCH_PUSH, label: 'Pushed' },
];

const HeaderWithInfo: React.FC<{ label: string; legendItems: { color: string; label: string }[]; testId: string }> = ({
  label,
  legendItems,
  testId,
}) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
    {label}
    <Tooltip title={<Legend title="Color Meanings:" items={legendItems} />} arrow placement="top">
      <InfoOutlinedIcon data-testid={testId} sx={{ fontSize: 14, color: tokens.text.tertiary, cursor: 'help' }} />
    </Tooltip>
  </Box>
);

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
      <Box sx={{ border: `1px solid ${tokens.borders.lighter}`, borderRadius: `${tokens.tableRadius}px`, p: 2, mb: 2 }}>
        <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{title}</Typography>
        <Typography sx={{ fontSize: '0.8125rem', color: tokens.text.secondary }}>Loading…</Typography>
      </Box>
    );
  }

  if (!games || games.length === 0) {
    return (
      <Box sx={{ border: `1px solid ${tokens.borders.lighter}`, borderRadius: `${tokens.tableRadius}px`, p: 2, mb: 2 }}>
        <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{title}</Typography>
        <Typography sx={{ fontSize: '0.8125rem', color: tokens.text.secondary }}>No games found</Typography>
      </Box>
    );
  }

  let wins = 0;
  let losses = 0;
  games.forEach((game) => {
    const td = getTeamData(game, sportType, teamName);
    if (td.teamPoints != null && td.opponentPoints != null) {
      if (td.teamPoints > td.opponentPoints) wins++;
      else if (td.teamPoints < td.opponentPoints) losses++;
    }
  });
  const summary = `${wins}-${losses}`;

  const h2hOpponentName = isHeadToHead && games.length > 0 ? getTeamData(games[0], sportType, teamName).opponentName : null;
  // MLB/NHL's "Line" isn't a true ATS spread, so neither the cell fill nor the
  // legend icon apply there — matches HistoricalGames.tsx's HeaderWithSpreadInfo.
  const showLineColor = sportType !== 'mlb' && sportType !== 'nhl';

  return (
    <Box sx={{ border: `1px solid ${tokens.borders.lighter}`, borderRadius: `${tokens.tableRadius}px`, overflow: 'hidden', mb: 2 }}>
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
                <TableCell sx={{ width: '1fr', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>
                  <HeaderWithInfo label="Team" legendItems={TEAM_LEGEND_ITEMS} testId="team-legend-info" />
                </TableCell>
                <TableCell sx={{ width: 90, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>{getScoreLabel(sportType)}</TableCell>
                <TableCell sx={{ width: 80, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>
                  {showLineColor ? (
                    <HeaderWithInfo label={getLineLabel(sportType)} legendItems={SPREAD_LEGEND_ITEMS} testId="spread-legend-info" />
                  ) : (
                    getLineLabel(sportType)
                  )}
                </TableCell>
                <TableCell sx={{ width: '1fr', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Opponent</TableCell>
                <TableCell sx={{ width: 110, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Opp {getScoreLabel(sportType)}</TableCell>
                <TableCell sx={{ width: 120, fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>
                  <HeaderWithInfo label="Betting Total" legendItems={TOTAL_LEGEND_ITEMS} testId="total-legend-info" />
                </TableCell>
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
                // Against-the-spread result for the Line/Spread cell. MLB/NHL's
                // "Line" isn't a true ATS spread (it's closer to a moneyline/run
                // line context), so it stays uncolored for those two sports.
                const lineResult: 'win' | 'loss' | 'push' | null =
                  td.teamPoints == null || td.teamLine == null || td.opponentPoints == null
                    ? null
                    : td.teamPoints + td.teamLine > td.opponentPoints
                    ? 'win'
                    : td.teamPoints + td.teamLine < td.opponentPoints
                    ? 'loss'
                    : 'push';
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
                    <TableCell
                      sx={{
                        fontSize: '0.8125rem',
                        fontWeight: 700,
                        borderTop: `1px solid ${tokens.borders.lighter}`,
                        fontVariantNumeric: 'tabular-nums',
                        ...(showLineColor ? resultColors(lineResult) : {}),
                      }}
                    >
                      {formatSigned(td.teamLine)}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                      <TeamCellLink name={td.opponentName} sport={sport} />
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', borderTop: `1px solid ${tokens.borders.lighter}` }}>
                      {td.opponentPoints ?? 'N/A'}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8125rem', fontWeight: 700, borderTop: `1px solid ${tokens.borders.lighter}`, ...resultColors(totalResult) }}>
                      {gd.totalLine ?? 'N/A'}
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
