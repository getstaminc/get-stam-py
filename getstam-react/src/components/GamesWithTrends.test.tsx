import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TrendFilter } from './GamesWithTrends';

let mockIsPro = false;
jest.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ isPro: mockIsPro, user: null }),
}));
jest.mock('./UpgradeDialog', () => ({ open }: { open: boolean }) => (open ? <div>Upgrade dialog</div> : null));

async function openMenu(sport: string, onChange = jest.fn()) {
  render(<TrendFilter value={3} onChange={onChange} sport={sport} />);
  await userEvent.click(screen.getByRole('combobox'));
  return { onChange, listbox: screen.getByRole('listbox') };
}

describe('TrendFilter', () => {
  it('offers 7+ and 10+ on every sport, locked for free users', async () => {
    mockIsPro = false;
    const { listbox } = await openMenu('nba');
    const options = within(listbox).getAllByRole('option').map((o) => o.textContent?.trim());
    expect(options).toEqual(['3+ Games', '4+ Games', '5+ Games', '7+ Games', '10+ Games']);
    expect(within(listbox).getAllByTestId('LockIcon')).toHaveLength(2);
  });

  it('gives college 7+ free and locks only 10+', async () => {
    mockIsPro = false;
    const { onChange, listbox } = await openMenu('ncaab');
    expect(within(listbox).getAllByTestId('LockIcon')).toHaveLength(1);
    await userEvent.click(within(listbox).getByText('7+ Games'));
    expect(onChange).toHaveBeenCalledWith(7);
  });

  it('opens the upgrade dialog instead of applying a locked length', async () => {
    mockIsPro = false;
    const { onChange, listbox } = await openMenu('ncaab');
    await userEvent.click(within(listbox).getByText('10+ Games'));
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByText('Upgrade dialog')).toBeInTheDocument();
  });

  it('lets Pro users pick 7+ and 10+ with no locks', async () => {
    mockIsPro = true;
    const { onChange, listbox } = await openMenu('nfl');
    expect(within(listbox).queryByTestId('LockIcon')).not.toBeInTheDocument();
    await userEvent.click(within(listbox).getByText('10+ Games'));
    expect(onChange).toHaveBeenCalledWith(10);
  });

  it('keeps MLB at 5+, 7+, 10+', async () => {
    mockIsPro = true;
    const { listbox } = await openMenu('mlb');
    expect(within(listbox).getAllByRole('option').map((o) => o.textContent)).toEqual(['5+ Games', '7+ Games', '10+ Games']);
  });
});
