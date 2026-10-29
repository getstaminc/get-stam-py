import { getTeamColors } from './teamColors';

describe('getTeamColors', () => {
  it('returns the known entry for an MLB team', () => {
    expect(getTeamColors('mlb', 'Brewers')).toEqual({ primary: '#13294B', secondary: '#FFC52F', abbr: 'MIL' });
    expect(getTeamColors('mlb', 'Rays')).toEqual({ primary: '#092C5C', secondary: '#8FBCE6', abbr: 'TB' });
  });

  it('falls back to a neutral gray entry for an unknown sport/team', () => {
    expect(getTeamColors('ncaaf', 'Michigan Wolverines')).toEqual({
      primary: '#4a5361',
      secondary: '#ffffff',
      abbr: 'MIC',
    });
  });

  it('falls back for a known sport with an unrecognized team name', () => {
    const result = getTeamColors('mlb', 'Totally Made Up Team');
    expect(result.primary).toBe('#4a5361');
    expect(result.secondary).toBe('#ffffff');
  });
});
