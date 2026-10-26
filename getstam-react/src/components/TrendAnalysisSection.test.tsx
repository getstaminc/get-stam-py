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

describe('TrendAnalysisSection collision card', () => {
  const collisionTrend = {
    type: 'win_streak' as const,
    count: 5,
    description: "Brewers' 5-game win streak at home meets Rays' 3-game loss streak on the road — ...",
    continuation_rate: 0.72,
    sample_size: 18,
    home_trend: { team: 'Milwaukee Brewers', type: 'win_streak' as const, count: 5, venue: 'venue_specific' as const },
    away_trend: { team: 'Tampa Bay Rays', type: 'loss_streak' as const, count: 3, venue: 'venue_specific' as const },
  };

  it('renders both teams, their streak text, and the split percentage', () => {
    const trends: GameWithTrends = {
      ...gameTrends,
      collisionTrends: [collisionTrend],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    expect(screen.getByText('Trend vs. Trend Collision')).toBeInTheDocument();
    expect(screen.getByText('Won 5 straight at home')).toBeInTheDocument();
    expect(screen.getByText('Lost 3 straight on the road')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
    expect(screen.getByText('28%')).toBeInTheDocument();
    expect(screen.getByText('18 historical meetings')).toBeInTheDocument();
  });

  it('renders nothing for the collision card when there are no collision trends', () => {
    render(<TrendAnalysisSection gameTrends={gameTrends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);
    expect(screen.queryByText('Trend vs. Trend Collision')).not.toBeInTheDocument();
  });
});

describe('TrendAnalysisSection remaining trends list', () => {
  it('shows a "More trends" heading and does not repeat the collision trend', () => {
    const collisionTrend = {
      type: 'win_streak' as const,
      count: 5,
      description: 'collision description',
      continuation_rate: 0.72,
      sample_size: 18,
      home_trend: { team: 'Milwaukee Brewers', type: 'win_streak' as const, count: 5, venue: 'venue_specific' as const },
      away_trend: { team: 'Tampa Bay Rays', type: 'loss_streak' as const, count: 3, venue: 'venue_specific' as const },
    };
    const otherTrend = {
      type: 'cover_streak' as const,
      count: 4,
      description: 'Brewers covered 4 straight spreads',
      continuation_rate: 0.6,
      sample_size: 10,
    };
    const trends: GameWithTrends = {
      ...gameTrends,
      collisionTrends: [collisionTrend],
      homeTeamTrends: [otherTrend],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    expect(screen.getByText('More trends')).toBeInTheDocument();
    expect(screen.getAllByText(/Brewers covered 4 straight spreads|collision description/).length).toBe(1);
  });
});
