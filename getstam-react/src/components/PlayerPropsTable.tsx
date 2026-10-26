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

export default PlayerPropsTable;
