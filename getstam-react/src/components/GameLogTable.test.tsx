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

function renderTable(defaultExpanded = true) {
  return render(
    <MemoryRouter>
      <GameLogTable
        title="Milwaukee Brewers - Last 5 Games"
        games={games}
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
});
