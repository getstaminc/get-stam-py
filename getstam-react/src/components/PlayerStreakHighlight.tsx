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
