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

  it('shows the opening line alongside current odds when present', () => {
    const gameWithOpening: GameWithDraw = {
      ...game,
      opening: {
        home: { spread_point: -7, spread_price: -110, h2h: -280 },
        away: { spread_point: 7, spread_price: -110, h2h: 230 },
        totals: { over_point: 44.5, over_price: -110, under_point: 44.5, under_price: -110 },
        snapshot_time: '2026-10-14T12:00:00Z',
      },
    };
    render(
      <MemoryRouter>
        <MatchupOddsCard game={gameWithOpening} sport="mlb" />
      </MemoryRouter>
    );

    expect(screen.getByText('Opened -7')).toBeInTheDocument();
    expect(screen.getByText('Opened +7')).toBeInTheDocument();
    expect(screen.getByText('Opened -280')).toBeInTheDocument();
    expect(screen.getByText('Opened +230')).toBeInTheDocument();
    expect(screen.getByText('Opened Over +44.5')).toBeInTheDocument();
    expect(screen.getByText('Opened Under +44.5')).toBeInTheDocument();
  });

  it('renders no Opened row when opening data is absent', () => {
    renderCard();
    expect(screen.queryByText(/^Opened/)).not.toBeInTheDocument();
  });

  it("shows each team's win-loss record under its name", () => {
    renderCard();
    // MatchupOddsCard joins record/site with " · ", no parens (unlike the old GameOdds card)
    expect(screen.getByText('16-5 · Home')).toBeInTheDocument();
    expect(screen.getByText('15-6 · Away')).toBeInTheDocument();
  });

  it('shows a LIVE badge and the live score, but no odds rows, for an in-progress game', () => {
    const liveGame: GameWithDraw = {
      ...game,
      completed: false,
      home: { ...game.home, score: 3 },
      away: { ...game.away, score: 1 },
    };
    render(
      <MemoryRouter>
        <MatchupOddsCard game={liveGame} sport="mlb" />
      </MemoryRouter>
    );
    expect(screen.getByText('LIVE')).toBeInTheDocument();
    expect(screen.getByText('3 - 1')).toBeInTheDocument();
    expect(screen.queryByText('-187')).not.toBeInTheDocument();
  });

  it('shows a FINAL badge for a completed game', () => {
    const finalGame: GameWithDraw = {
      ...game,
      completed: true,
      home: { ...game.home, score: 5 },
      away: { ...game.away, score: 2 },
    };
    render(
      <MemoryRouter>
        <MatchupOddsCard game={finalGame} sport="mlb" />
      </MemoryRouter>
    );
    expect(screen.getByText('FINAL')).toBeInTheDocument();
    expect(screen.getByText('5 - 2')).toBeInTheDocument();
    expect(screen.queryByText('LIVE')).not.toBeInTheDocument();
  });

  it('shows a View Details button only when detailsLink is passed', () => {
    const { rerender } = render(
      <MemoryRouter>
        <MatchupOddsCard game={game} sport="mlb" />
      </MemoryRouter>
    );
    expect(screen.queryByText('View Details')).not.toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <MatchupOddsCard game={game} sport="mlb" detailsLink="/game-details/mlb?game_id=abc" />
      </MemoryRouter>
    );
    const link = screen.getByText('View Details').closest('a');
    expect(link).toHaveAttribute('href', '/game-details/mlb?game_id=abc');
  });

  it('constrains the header grid/flex tracks so a long team name cannot overflow the card', () => {
    const longNameGame: GameWithDraw = {
      ...game,
      home: { ...game.home, team: 'Arizona Cardinals' },
      away: { ...game.away, team: 'Tampa Bay Buccaneers' },
    };
    render(
      <MemoryRouter>
        <MatchupOddsCard game={longNameGame} sport="nfl" />
      </MemoryRouter>
    );
    // minmax(0, 1fr), not bare 1fr -- otherwise a long team name forces the
    // grid track (and the card) wider than the layout intends. Regression
    // test for a real overflow seen once this card started appearing in a
    // narrower 2-up list grid instead of only as a full-width page header.
    expect(screen.getByTestId('matchup-header-grid')).toHaveStyle({
      gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
    });
    expect(screen.getByTestId('team-header-home')).toHaveStyle({ minWidth: 0 });
    expect(screen.getByTestId('team-header-away')).toHaveStyle({ minWidth: 0 });
  });
});
