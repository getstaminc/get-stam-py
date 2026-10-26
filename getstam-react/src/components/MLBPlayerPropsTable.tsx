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
            <TableCell sx={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', color: tokens.text.tertiary }}>Hit Rate</TableCell>
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
