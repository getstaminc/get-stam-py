import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import TrendInsightCard from './TrendInsightCard';
import { TrendResult } from '../utils/trendAnalysis';

let mockIsPro = false;
jest.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ isPro: mockIsPro, user: null }),
}));

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

  describe('value reads on the Overview card', () => {
    // Brewers -187 needs 65.2%; 0.80 over n=40 shrinks to ~0.77 → VALUE.
    const marketOverview = {
      moneyline: { lean: 'Milwaukee Brewers', probability: 0.8, trend_count: 2, sample_size: 40, contributing_trends: [] },
    };
    const renderWithOverview = (g: any = game) => render(
      <MemoryRouter>
        <TrendInsightCard game={g} trends={trends} marketOverview={marketOverview} detailsLink="/x" sport="mlb" />
      </MemoryRouter>
    );

    it('shows the verdict and break-even line to Pro users', () => {
      mockIsPro = true;
      renderWithOverview();
      expect(screen.getByText('VALUE')).toBeInTheDocument();
      expect(screen.getByText('-187 needs 65.2% to break even')).toBeInTheDocument();
    });

    it('shows a locked teaser without the real numbers to free users', () => {
      mockIsPro = false;
      renderWithOverview();
      expect(screen.getByRole('button', { name: /unlock value read/i })).toBeInTheDocument();
      expect(screen.queryByText('VALUE')).not.toBeInTheDocument();
      expect(screen.queryByText(/-187 needs/)).not.toBeInTheDocument();
    });

    it('opens the example preview when a free user clicks the teaser', async () => {
      mockIsPro = false;
      renderWithOverview();
      await userEvent.click(screen.getByText(/see what value reads show/i));
      expect(await screen.findByText(/Example · Knicks vs Hornets/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /unlock with pro/i })).toBeInTheDocument();
    });

    it('hides value reads once the game has a score', () => {
      mockIsPro = true;
      renderWithOverview({ ...game, home: { ...game.home, score: 3 }, away: { ...game.away, score: 1 } });
      expect(screen.queryByText('VALUE')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /unlock value read/i })).not.toBeInTheDocument();
    });
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
