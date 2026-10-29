import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
    moneyline: { lean: 'Milwaukee Brewers', probability: 0.64, trend_count: 1, sample_size: 25, contributing_trends: [] },
    spread: { lean: 'Milwaukee Brewers', probability: 0.58, trend_count: 1, sample_size: 24, contributing_trends: [] },
    total: { lean: 'Over', probability: 0.6, trend_count: 1, sample_size: 20, contributing_trends: [] },
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

  it('sizes the market cards grid to the actual number of cards, not a fixed 3 columns', () => {
    const { rerender } = render(
      <TrendAnalysisSection gameTrends={gameTrends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );
    // gameTrends fixture has all 3 markets
    expect(screen.getByTestId('market-cards-grid')).toHaveStyle({ gridTemplateColumns: 'repeat(3, 1fr)' });

    const twoMarkets: GameWithTrends = {
      ...gameTrends,
      marketOverview: {
        spread: gameTrends.marketOverview!.spread,
        total: gameTrends.marketOverview!.total,
      },
    };
    rerender(
      <TrendAnalysisSection gameTrends={twoMarkets} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );
    expect(screen.getByTestId('market-cards-grid')).toHaveStyle({ gridTemplateColumns: 'repeat(2, 1fr)' });

    const oneMarket: GameWithTrends = {
      ...gameTrends,
      marketOverview: { total: gameTrends.marketOverview!.total },
    };
    rerender(
      <TrendAnalysisSection gameTrends={oneMarket} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );
    expect(screen.getByTestId('market-cards-grid')).toHaveStyle({ gridTemplateColumns: 'repeat(1, 1fr)' });
  });

  it('no longer renders the old "What the numbers suggest" banner', () => {
    render(
      <TrendAnalysisSection gameTrends={gameTrends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );
    expect(screen.queryByText('What the numbers suggest')).not.toBeInTheDocument();
  });

  it('shows the contributing-trends breakdown under each market card when present', () => {
    const trendsWithContext: GameWithTrends = {
      ...gameTrends,
      marketOverview: {
        moneyline: {
          lean: 'Milwaukee Brewers',
          probability: 0.64,
          trend_count: 2,
          sample_size: 25,
          contributing_trends: [
            { title: 'Milwaukee Brewers won 5 straight', rate: 0.64, sample_size: 20, weight: 0.8 },
            { title: 'H2H trend vs Rays', rate: 0.5, sample_size: 5, weight: 0.2 },
          ],
        },
      },
    };
    render(
      <TrendAnalysisSection gameTrends={trendsWithContext} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />
    );

    expect(screen.getByText('Blended from 2 trends:')).toBeInTheDocument();
    expect(screen.getByText(/Milwaukee Brewers won 5 straight — 64% \(20 games\) · 80% weight/)).toBeInTheDocument();
    expect(screen.getByText(/H2H trend vs Rays — 50% \(5 games\) · 20% weight/)).toBeInTheDocument();
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

  it('labels a cover-rate collision as "cover", not "win", and colors both bar segments with team primaries', () => {
    const coverCollisionTrend = {
      type: 'cover_streak' as const,
      count: 5,
      description: "Brewers' 5-game cover streak meets Yankees' 3-game no-cover streak — ...",
      continuation_rate: 0.72,
      sample_size: 18,
      home_trend: { team: 'Milwaukee Brewers', type: 'cover_streak' as const, count: 5, venue: 'general' as const },
      away_trend: { team: 'New York Yankees', type: 'no_cover_streak' as const, count: 3, venue: 'general' as const },
    };
    const trends: GameWithTrends = {
      ...gameTrends,
      collisionTrends: [coverCollisionTrend],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    const panel = within(screen.getByTestId('collision-split-panel'));
    expect(panel.getByText('Milwaukee Brewers cover')).toBeInTheDocument();
    expect(panel.getByText('New York Yankees cover')).toBeInTheDocument();
    expect(panel.queryByText('Milwaukee Brewers win')).not.toBeInTheDocument();
    expect(panel.queryByText('New York Yankees win')).not.toBeInTheDocument();

    // Fix 3: the away segment should use the away team's primary color (never a
    // white/near-invisible secondary). Yankees' secondary is white (#FFFFFF),
    // so this case would have been invisible on the panel background pre-fix.
    const rightBar = screen.getByTestId('collision-bar-right');
    expect(rightBar).toHaveStyle({ backgroundColor: '#0C2340' });
    const leftBar = screen.getByTestId('collision-bar-left');
    expect(leftBar).toHaveStyle({ backgroundColor: '#13294B' });
  });

  it('shows OVER/UNDER framing with no team attribution and neutral bar colors for a total-based collision', () => {
    const totalCollisionTrend = {
      type: 'over_streak' as const,
      count: 5,
      description: "Brewers games have gone OVER 5 straight meets Rays games going OVER 3 straight — ...",
      continuation_rate: 0.65,
      sample_size: 12,
      home_trend: { team: 'Milwaukee Brewers', type: 'over_streak' as const, count: 5, venue: 'general' as const },
      away_trend: { team: 'Tampa Bay Rays', type: 'over_streak' as const, count: 3, venue: 'general' as const },
    };
    const trends: GameWithTrends = {
      ...gameTrends,
      collisionTrends: [totalCollisionTrend],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    const panel = within(screen.getByTestId('collision-split-panel'));
    expect(panel.getByText('OVER')).toBeInTheDocument();
    expect(panel.getByText('UNDER')).toBeInTheDocument();
    expect(panel.queryByText('Milwaukee Brewers win')).not.toBeInTheDocument();
    expect(panel.queryByText('Tampa Bay Rays win')).not.toBeInTheDocument();
    expect(panel.queryByText('Milwaukee Brewers cover')).not.toBeInTheDocument();

    const leftBar = screen.getByTestId('collision-bar-left');
    const rightBar = screen.getByTestId('collision-bar-right');
    expect(leftBar).toHaveStyle({ backgroundColor: '#4a5361' });
    expect(rightBar).toHaveStyle({ backgroundColor: '#eceee9' });
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

  it('collapses to 2 trends with a "View More ▾" toggle when there are more than 2', async () => {
    const makeTrend = (n: number) => ({
      type: 'cover_streak' as const,
      count: 4,
      description: `Trend number ${n}`,
      continuation_rate: 0.6,
      sample_size: 10,
    });
    const trends: GameWithTrends = {
      ...gameTrends,
      homeTeamTrends: [makeTrend(1), makeTrend(2), makeTrend(3)],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    expect(screen.getByText('Trend number 1')).toBeInTheDocument();
    expect(screen.getByText('Trend number 2')).toBeInTheDocument();
    expect(screen.queryByText('Trend number 3')).not.toBeInTheDocument();
    expect(screen.getByText('View More ▾')).toBeInTheDocument();

    await userEvent.click(screen.getByText('View More ▾'));

    expect(screen.getByText('Trend number 3')).toBeInTheDocument();
    expect(screen.getByText('View Less ▾')).toBeInTheDocument();
    expect(screen.queryByText('View More ▾')).not.toBeInTheDocument();
  });

  it('shows no toggle when there are 2 or fewer trends', () => {
    const makeTrend = (n: number) => ({
      type: 'cover_streak' as const,
      count: 4,
      description: `Trend number ${n}`,
      continuation_rate: 0.6,
      sample_size: 10,
    });
    const trends: GameWithTrends = {
      ...gameTrends,
      homeTeamTrends: [makeTrend(1), makeTrend(2)],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    expect(screen.getByText('Trend number 1')).toBeInTheDocument();
    expect(screen.getByText('Trend number 2')).toBeInTheDocument();
    expect(screen.queryByText('View More ▾')).not.toBeInTheDocument();
    expect(screen.queryByTestId('trend-fade-overlay')).not.toBeInTheDocument();
  });

  it('fades the last visible card while collapsed, and removes the fade once expanded', async () => {
    const makeTrend = (n: number) => ({
      type: 'cover_streak' as const,
      count: 4,
      description: `Trend number ${n}`,
      continuation_rate: 0.6,
      sample_size: 10,
    });
    const trends: GameWithTrends = {
      ...gameTrends,
      homeTeamTrends: [makeTrend(1), makeTrend(2), makeTrend(3)],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    expect(screen.getByTestId('trend-fade-overlay')).toBeInTheDocument();

    await userEvent.click(screen.getByText('View More ▾'));

    expect(screen.queryByTestId('trend-fade-overlay')).not.toBeInTheDocument();
  });

  it('only fades the bottom portion of the card, not the whole thing', () => {
    const makeTrend = (n: number) => ({
      type: 'cover_streak' as const,
      count: 4,
      description: `Trend number ${n}`,
      continuation_rate: 0.6,
      sample_size: 10,
    });
    const trends: GameWithTrends = {
      ...gameTrends,
      homeTeamTrends: [makeTrend(1), makeTrend(2), makeTrend(3)],
    };
    render(<TrendAnalysisSection gameTrends={trends} loading={false} game={game} minTrendLength={3} sportKey="baseball_mlb" />);

    // The title of the last visible (faded) card must still be readable text in
    // the DOM — this guards against the overlay covering 100% of the card height
    // (which visually washes out the title from the very top).
    expect(screen.getByText('Trend number 2')).toBeVisible();
    const overlay = screen.getByTestId('trend-fade-overlay');
    expect(overlay).not.toHaveStyle({ height: '100%' });
  });
});
