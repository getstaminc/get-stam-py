import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MatchupOddsCard from './MatchupOddsCard';
import { GameWithDraw } from '../types/gameTypes';

const game: GameWithDraw = {
  game_id: 'evt1',
  commence_time: '2026-10-24T23:10:00Z',
  completed: false,
  home: { team: 'Milwaukee Brewers', score: null, odds: { h2h: -187, spread_point: -1.5, spread_price: 129 }, record: { wins: 16, losses: 5, ties: 0 } },
  away: { team: 'Tampa Bay Rays', score: null, odds: { h2h: 154, spread_point: 1.5, spread_price: -156 }, record: { wins: 15, losses: 6, ties: 0 } },
  totals: { over_point: 7.5, over_price: -110, under_point: 7.5, under_price: -110 },
};

function renderCard() {
  return render(
    <MemoryRouter>
      <MatchupOddsCard game={game} sport="mlb" pitcherData={{ home_pitcher: 'J. Misiorowski', away_pitcher: 'N. Martinez' }} />
    </MemoryRouter>
  );
}

describe('MatchupOddsCard', () => {
  it('shows each team name, a TeamLogo abbreviation, and the pitcher line', () => {
    renderCard();
    expect(screen.getByText('Milwaukee Brewers')).toBeInTheDocument();
    expect(screen.getByText('Tampa Bay Rays')).toBeInTheDocument();
    expect(screen.getByText('MIL')).toBeInTheDocument();
    expect(screen.getByText('TB')).toBeInTheDocument();
    expect(screen.getByText('J. Misiorowski')).toBeInTheDocument();
    expect(screen.getByText('N. Martinez')).toBeInTheDocument();
  });

  it('shows the moneyline, spread, and total odds rows', () => {
    renderCard();
    expect(screen.getByText('-187')).toBeInTheDocument();
    expect(screen.getByText('+154')).toBeInTheDocument();
    expect(screen.getByText('-1.5 (+129)')).toBeInTheDocument();
    expect(screen.getByText('Over +7.5 (-110)')).toBeInTheDocument();
  });
});
