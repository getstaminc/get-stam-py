import React from 'react';
import { render, screen } from '@testing-library/react';
import PlayerPropsTable from './PlayerPropsTable';

const players = {
  'L. Doncic': {
    player_points: { point: 28.5 },
    historical: [
      { short_game_date: '10/15', odds_player_points: 28.5, actual_player_points: 33 },
      { short_game_date: '10/13', odds_player_points: 27.5, actual_player_points: 19 },
      { short_game_date: '10/11', odds_player_points: 27.5, actual_player_points: 31 },
    ],
  },
};

describe('PlayerPropsTable (NBA) Player/Prop/Streak/Continues/Last 5 layout', () => {
  it('renders one row per player-prop with the derived streak', () => {
    render(<PlayerPropsTable players={players} />);
    expect(screen.getByText('L. Doncic')).toBeInTheDocument();
    expect(screen.getByText('Over 28.5 Points')).toBeInTheDocument();
    expect(screen.getByText('1 straight Overs')).toBeInTheDocument();
    expect(screen.getByText('67% (2/3)')).toBeInTheDocument();
  });
});
