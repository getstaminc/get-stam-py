import React from 'react';
import { Box, Typography } from '@mui/material';

// Reusable legend item component
interface LegendItemProps {
  color: string;
  label: string;
}

const LegendItem: React.FC<LegendItemProps> = ({ color, label }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
    <Box sx={{ width: 16, height: 16, backgroundColor: color, border: '1px solid #ccc' }} />
    <Typography variant="body2">{label}</Typography>
  </Box>
);

// Common legend structure
interface LegendProps {
  title: string;
  items: Array<{ color: string; label: string }>;
}

const Legend: React.FC<LegendProps> = ({ title, items }) => (
  <Box sx={{ p: 1 }}>
    <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
      {title}
    </Typography>
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
      {items.map((item, index) => (
        <LegendItem key={index} color={item.color} label={item.label} />
      ))}
    </Box>
  </Box>
);

// Predefined legend configurations
export const MoneylineLegend = () => (
  <Legend 
    title="Color Meanings:"
    items={[
      { color: '#c8e6c9', label: 'Win' },
      { color: '#ffcdd2', label: 'Loss' },
      { color: '#e0e0e0', label: 'Tie' }
    ]}
  />
);

export const SpreadLegend = () => (
  <Legend
    title="Color Meanings:"
    items={[
      { color: '#c8e6c9', label: 'Covered' },
      { color: '#ffcdd2', label: 'Didn\'t Cover' },
      { color: '#e0e0e0', label: 'Pushed' }
    ]}
  />
);

export const TotalLegend = () => (
  <Legend
    title="Color Meanings:"
    items={[
      { color: '#c8e6c9', label: 'Over' },
      { color: '#ffcdd2', label: 'Under' },
      { color: '#e0e0e0', label: 'Push' }
    ]}
  />
);

export default Legend;
