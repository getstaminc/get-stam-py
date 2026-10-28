import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PlayerStreakHighlight from './PlayerStreakHighlight';
import { TeamStreaks } from './PlayerStreaksStrip';

const groups: TeamStreaks[] = [
  {
    team: 'Brewers',
    streaks: [
      { player_name: 'C. Yelich', stat: 'hits', streak_count: 5, continuation_rate: 0.57, sample_size: 7 },
    ],
  },
  {
    team: 'Rays',
    streaks: [
      { player_name: 'R. Arozarena', stat: 'hr', streak_count: 2, continuation_rate: 0.8, sample_size: 10 },
    ],
  },
];

describe('PlayerStreakHighlight', () => {
  it('shows the single best streak (highest continuation rate) with a HOT pill', () => {
    render(
      <MemoryRouter>
        <PlayerStreakHighlight groups={groups} />
      </MemoryRouter>
    );
    expect(screen.getByText('HOT')).toBeInTheDocument();
    expect(screen.getByText('R. Arozarena')).toBeInTheDocument();
    expect(screen.getByText(/2 straight 1\+ HR/)).toBeInTheDocument();
    expect(screen.getByText(/continues 80% \(8\/10\)/)).toBeInTheDocument();
  });

  it('renders nothing when there are no streaks', () => {
    const { container } = render(
      <MemoryRouter>
        <PlayerStreakHighlight groups={[{ team: 'Brewers', streaks: [] }]} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });
});
