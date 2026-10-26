import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GameLogTable from './GameLogTable';
import { MLBGame } from '../types/gameTypes';

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
  it('shows the header summary and a TeamLogo abbreviation when expanded', () => {
    renderTable(true);
    expect(screen.getByText('Milwaukee Brewers - Last 5 Games')).toBeInTheDocument();
    expect(screen.getByText('1-0 · Over 1-0')).toBeInTheDocument();
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

  it('shows em-dash (—) for missing total data, not "P"', () => {
    renderTable(true, gamesWithMissingTotal);
    // Game has home_runs (3) and away_runs (2), so team result is win (3 > 2)
    // But total is null, so totalResult is null, so ouLabel should be '—' not 'P'
    const bettingTotalCells = screen.getAllByText(/N\/A · —/);
    expect(bettingTotalCells.length).toBeGreaterThan(0);
    // Ensure the misleading 'P' for missing data does not appear
    const allCells = screen.queryAllByText(/N\/A · P/);
    expect(allCells.length).toBe(0);
  });
});
