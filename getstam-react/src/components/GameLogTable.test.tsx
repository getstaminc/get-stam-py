import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GameLogTable from './GameLogTable';
import { MLBGame, NFLGame } from '../types/gameTypes';

const games: MLBGame[] = [
  {
    game_id: 1,
    game_date: '2026-10-15',
    start_time: '',
    team_side: 'away',
    home_team: 'Los Angeles Dodgers',
    away_team: 'Milwaukee Brewers',
    home_runs: 4,
    away_runs: 6,
    home_line: -130,
    away_line: 130,
    total: 7.5,
    playoffs: false,
  },
];

const gamesWithMissingTotal: MLBGame[] = [
  {
    game_id: 2,
    game_date: '2026-10-14',
    start_time: '',
    team_side: 'home',
    home_team: 'Milwaukee Brewers',
    away_team: 'Los Angeles Dodgers',
    home_runs: 3,
    away_runs: 2,
    home_line: 120,
    away_line: -140,
    total: null as any, // Missing total line
    playoffs: false,
  },
];

const nflGames: NFLGame[] = [
  {
    game_id: 3,
    game_date: '2026-10-18',
    start_time: '',
    team_side: 'away',
    home_team_name: 'Philadelphia Eagles',
    away_team_name: 'Dallas Cowboys',
    home_points: 14,
    away_points: 25,
    home_line: 3,
    away_line: -3,
    home_money_line: 150,
    away_money_line: -180,
    total_points: 39,
    total: 39.5,
  },
];

function renderTable(defaultExpanded = true, testGames?: MLBGame[]) {
  return render(
    <MemoryRouter>
      <GameLogTable
        title="Milwaukee Brewers - Last 5 Games"
        games={testGames || games}
        teamName="Brewers"
        sportType="mlb"
        sport="mlb"
        defaultExpanded={defaultExpanded}
      />
    </MemoryRouter>
  );
}

describe('GameLogTable', () => {
  it('shows the header summary (win-loss only) and a TeamLogo abbreviation when expanded', () => {
    renderTable(true);
    expect(screen.getByText('Milwaukee Brewers - Last 5 Games')).toBeInTheDocument();
    expect(screen.getByText('1-0')).toBeInTheDocument();
    expect(screen.queryByText(/Over/)).not.toBeInTheDocument();
    expect(screen.getByText('MIL')).toBeInTheDocument();
    expect(screen.getByText('10/15/2026')).toBeInTheDocument();
    expect(screen.getByText('+130')).toBeInTheDocument();
  });

  it('starts collapsed and reveals rows on header click when defaultExpanded is false', async () => {
    renderTable(false);
    expect(screen.queryByText('10/15/2026')).not.toBeInTheDocument();
    const header = screen.getByRole('button', { name: /Milwaukee Brewers - Last 5 Games/i });
    header.click();
    expect(await screen.findByText('10/15/2026')).toBeInTheDocument();
  });

  it('shows just the betting total line, with no O/U/push suffix', () => {
    renderTable(true);
    // total: 7.5, no suffix text alongside it
    expect(screen.getByText('7.5')).toBeInTheDocument();
    expect(screen.queryByText(/7\.5 ·/)).not.toBeInTheDocument();
  });

  it('shows N/A (not a misleading push/over/under label) when total data is missing', () => {
    renderTable(true, gamesWithMissingTotal);
    const bettingTotalCell = screen.getAllByText('N/A');
    expect(bettingTotalCell.length).toBeGreaterThan(0);
    expect(screen.queryByText(/N\/A ·/)).not.toBeInTheDocument();
  });

  it('labels the line column "Line" for MLB and "Spread" for football', () => {
    const { rerender } = render(
      <MemoryRouter>
        <GameLogTable title="MLB Game" games={games} teamName="Brewers" sportType="mlb" sport="mlb" />
      </MemoryRouter>
    );
    expect(screen.getByText('Line')).toBeInTheDocument();
    expect(screen.queryByText('Spread')).not.toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <GameLogTable title="NFL Game" games={games as any} teamName="Brewers" sportType="nfl" sport="nfl" />
      </MemoryRouter>
    );
    expect(screen.getByText('Spread')).toBeInTheDocument();
    expect(screen.queryByText('Line')).not.toBeInTheDocument();
  });

  it('shows a color-meaning info icon next to the Team and Betting Total headers', () => {
    renderTable(true);
    expect(screen.getByTestId('team-legend-info')).toBeInTheDocument();
    expect(screen.getByTestId('total-legend-info')).toBeInTheDocument();
  });

  it('shows the Line/Spread legend icon for football and for MLB/NHL', () => {
    const { rerender } = render(
      <MemoryRouter>
        <GameLogTable title="NFL Game" games={nflGames} teamName="Cowboys" sportType="nfl" sport="nfl" />
      </MemoryRouter>
    );
    expect(screen.getByTestId('spread-legend-info')).toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <GameLogTable title="MLB Game" games={games} teamName="Brewers" sportType="mlb" sport="mlb" />
      </MemoryRouter>
    );
    expect(screen.getByTestId('spread-legend-info')).toBeInTheDocument();
  });

  it('colors the Line/Spread cell for the ATS result (football) or the moneyline result (MLB/NHL)', () => {
    const { rerender } = render(
      <MemoryRouter>
        <GameLogTable title="NFL Game" games={nflGames} teamName="Cowboys" sportType="nfl" sport="nfl" />
      </MemoryRouter>
    );
    // Cowboys (away): 25 pts + (-3) line = 22 > Eagles' 14 -> covered
    expect(screen.getByText('-3')).toHaveStyle({ backgroundColor: '#e3f4ea' });

    rerender(
      <MemoryRouter>
        <GameLogTable title="MLB Game" games={games} teamName="Brewers" sportType="mlb" sport="mlb" />
      </MemoryRouter>
    );
    // Brewers (away): 6 runs > Dodgers' 4 -> won straight up -> moneyline hit
    expect(screen.getByText('+130')).toHaveStyle({ backgroundColor: '#e3f4ea' });
  });
});
