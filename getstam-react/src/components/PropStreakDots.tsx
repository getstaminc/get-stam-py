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
