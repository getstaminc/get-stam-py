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
