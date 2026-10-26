import React from 'react';
import { render, screen } from '@testing-library/react';
import TrendAnalysisSection from './TrendAnalysisSection';
import { GameWithTrends } from '../utils/trendAnalysis';

const game = {
  home: { team: 'Milwaukee Brewers', score: null, odds: { spread_point: -1.5 } },
  away: { team: 'Tampa Bay Rays', score: null, odds: { spread_point: 1.5 } },
  totals: {},
};

const gameTrends: GameWithTrends = {
  game,
  homeTeamTrends: [],
  awayTeamTrends: [],
  headToHeadTrends: [],
  marketOverview: {
    moneyline: { lean: 'Milwaukee Brewers', probability: 0.64, trend_count: 1, sample_size: 25, supporting_description: '' },
    spread: { lean: 'Milwaukee Brewers', probability: 0.58, trend_count: 1, sample_size: 24, supporting_description: '' },
    total: { lean: 'Over', probability: 0.6, trend_count: 1, sample_size: 20, supporting_description: '' },
  },
  hasTrends: true,
};

describe('TrendAnalysisSection market cards', () => {
  it('renders a card per market with percent, label, and W-L record', () => {
    render(
      <TrendAnalysisSection gameTrends={gameTrends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );

    expect(screen.getByText('Moneyline Trends')).toBeInTheDocument();
    expect(screen.getByText('64%')).toBeInTheDocument();
    expect(screen.getByText('Milwaukee Brewers win')).toBeInTheDocument();
    expect(screen.getByText('16-9 (25 games)')).toBeInTheDocument();

    expect(screen.getByText('Spread Trends')).toBeInTheDocument();
    expect(screen.getByText('Milwaukee Brewers cover -1.5')).toBeInTheDocument();

    expect(screen.getByText('Total Trends')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText('Over')).toBeInTheDocument();
  });

  it('no longer renders the old "What the numbers suggest" banner', () => {
    render(
      <TrendAnalysisSection gameTrends={gameTrends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );
    expect(screen.queryByText('What the numbers suggest')).not.toBeInTheDocument();
  });
});
