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
