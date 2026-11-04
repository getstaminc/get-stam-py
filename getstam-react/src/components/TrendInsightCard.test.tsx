import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TrendInsightCard from './TrendInsightCard';
import { TrendResult } from '../utils/trendAnalysis';

const game = {
  home: { team: 'Milwaukee Brewers', score: null, odds: { h2h: -187, spread_point: -1.5, spread_price: 129 }, record: { wins: 16, losses: 5, ties: 0 } },
  away: { team: 'Tampa Bay Rays', score: null, odds: { h2h: 154, spread_point: 1.5, spread_price: -156 }, record: { wins: 15, losses: 6, ties: 0 } },
  totals: { over_point: 7.5, over_price: -110, under_point: 7.5, under_price: -110 },
  commence_time: '2026-10-24T23:10:00Z',
};

const trends: TrendResult[] = [
  { type: 'win_streak', count: 5, description: 'Milwaukee Brewers won 5 straight', continuation_rate: 0.64, sample_size: 25 },
];

function renderCard() {
  return render(
    <MemoryRouter>
      <TrendInsightCard game={game} trends={trends} detailsLink="/game-details/mlb?game_id=abc" sport="mlb" />
    </MemoryRouter>
  );
}

describe('TrendInsightCard', () => {
  it('shows each team name, a TeamLogo abbreviation, and its win-loss record (shared MatchupTeamHeader)', () => {
    renderCard();
    expect(screen.getByText('Milwaukee Brewers')).toBeInTheDocument();
    expect(screen.getByText('Tampa Bay Rays')).toBeInTheDocument();
    expect(screen.getByText('MIL')).toBeInTheDocument();
    expect(screen.getByText('TB')).toBeInTheDocument();
    expect(screen.getByText('16-5 · Home')).toBeInTheDocument();
    expect(screen.getByText('15-6 · Away')).toBeInTheDocument();
  });

  it('returns null when there are no trends to show', () => {
    const { container } = render(
      <MemoryRouter>
        <TrendInsightCard game={game} trends={[]} detailsLink="/game-details/mlb?game_id=abc" sport="mlb" />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });
});
