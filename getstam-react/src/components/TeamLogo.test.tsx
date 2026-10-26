import React from 'react';
import { render, screen } from '@testing-library/react';
import TeamLogo from './TeamLogo';

describe('TeamLogo', () => {
  it('renders the team abbreviation in its brand colors', () => {
    render(<TeamLogo sportKey="baseball_mlb" teamName="Milwaukee Brewers" size={60} />);
    const logo = screen.getByText('MIL');
    expect(logo).toBeInTheDocument();
    expect(logo).toHaveStyle({ backgroundColor: '#13294B', color: '#FFC52F' });
  });

  it('falls back to a neutral abbreviation circle for an unrecognized team', () => {
    render(<TeamLogo sportKey="basketball_ncaab" teamName="Some College Team" size={40} />);
    const logo = screen.getByText('SOM');
    expect(logo).toHaveStyle({ backgroundColor: '#4a5361' });
  });
});
