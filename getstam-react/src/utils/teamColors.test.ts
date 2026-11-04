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

  it('returns curated colors for NCAAF/NCAAB, keyed by the abbreviation code (not the full school name)', () => {
    // NCAAF/NCAAB are keyed by the code convertTeamNameNcaaf/convertTeamNameNcaab
    // actually produce (e.g. "MICH" for Michigan), not a mascot short name like
    // the pro leagues use -- this is how TeamLogo.tsx really calls getTeamColors.
    expect(getTeamColors('ncaaf', 'MICH')).toEqual({ primary: '#00274C', secondary: '#FFCB05', abbr: 'MICH' });
    expect(getTeamColors('ncaaf', 'ALA')).toEqual({ primary: '#9E1B32', secondary: '#FFFFFF', abbr: 'ALA' });
    expect(getTeamColors('ncaab', 'DUKE')).toEqual({ primary: '#001A57', secondary: '#FFFFFF', abbr: 'DUKE' });
  });

  it('truncates an abbreviation-code abbr to a shorter display form when it would otherwise be unusually long', () => {
    // UTAHTCH (Utah Tech) is the one outlier code longer than 5 characters among
    // all NCAAF/NCAAB entries -- its display abbr is shortened, the lookup key is not.
    expect(getTeamColors('ncaaf', 'UTAHTCH').abbr).toBe('UTAHT');
  });

  it('has a color entry for every NCAAF and NCAAB team code the app knows about', () => {
    // Guards against a future addition to teamSlugUtils.ts's NCAAF_TEAMS/NCAAB_TEAMS
    // silently falling back to the neutral gray circle because nobody added a
    // matching entry here.
    const ncaafCodes = ['ABCH', 'AIR', 'ALA', 'BYU', 'CLEM', 'DUKE', 'MICH', 'OKLA', 'TEX', 'UTAHTCH', 'YST'];
    for (const code of ncaafCodes) {
      expect(getTeamColors('ncaaf', code).primary).not.toBe('#4a5361');
    }
    const ncaabCodes = ['ALAB', 'DUKE', 'KAN', 'MICH', 'UCLA', 'UCONN', 'XAVER'];
    for (const code of ncaabCodes) {
      expect(getTeamColors('ncaab', code).primary).not.toBe('#4a5361');
    }
  });

  it('returns curated colors for soccer clubs, keyed by the full club name (soccer names pass through unshortened)', () => {
    expect(getTeamColors('soccer', 'Arsenal')).toEqual({ primary: '#EF0107', secondary: '#063672', abbr: 'ARS' });
    expect(getTeamColors('soccer', 'Real Madrid')).toEqual({ primary: '#FFFFFF', secondary: '#FEBE10', abbr: 'RMA' });
    expect(getTeamColors('soccer', 'Paris Saint Germain')).toEqual({ primary: '#001E62', secondary: '#DA020E', abbr: 'PSG' });
  });

  it('has a color entry for every club that appeared in the last 2 seasons of EPL/La Liga/Bundesliga/Ligue 1/Serie A data', () => {
    const clubs = ['Brighton and Hove Albion', 'Leicester City', 'Atlético Madrid', '1. FC Köln', 'Borussia Monchengladbach', 'Saint Etienne', 'Inter Milan', 'Hellas Verona'];
    for (const club of clubs) {
      expect(getTeamColors('soccer', club).primary).not.toBe('#4a5361');
    }
  });

  it('corrects the NBA/NHL entries flagged by a color audit (primary/secondary were swapped or stale)', () => {
    expect(getTeamColors('nhl', 'Capitals')).toEqual({ primary: '#C8102E', secondary: '#041E42', abbr: 'WSH' });
    expect(getTeamColors('nhl', 'Bruins')).toEqual({ primary: '#FFB81C', secondary: '#000000', abbr: 'BOS' });
    expect(getTeamColors('nhl', 'Predators')).toEqual({ primary: '#FFB81C', secondary: '#041E42', abbr: 'NSH' });
    expect(getTeamColors('nhl', 'Blackhawks')).toEqual({ primary: '#CF0A2C', secondary: '#000000', abbr: 'CHI' });
    expect(getTeamColors('nhl', 'Flames')).toEqual({ primary: '#D2001C', secondary: '#FAAF19', abbr: 'CGY' });
    expect(getTeamColors('nhl', 'Hurricanes')).toEqual({ primary: '#CE1126', secondary: '#FFFFFF', abbr: 'CAR' });
    expect(getTeamColors('nhl', 'Senators')).toEqual({ primary: '#DA1A32', secondary: '#B79257', abbr: 'OTT' });
    expect(getTeamColors('nhl', 'Sabres')).toEqual({ primary: '#003087', secondary: '#FCB514', abbr: 'BUF' });
    expect(getTeamColors('nba', 'Cavaliers')).toEqual({ primary: '#860038', secondary: '#FDBB30', abbr: 'CLE' });
    expect(getTeamColors('nba', 'Clippers')).toEqual({ primary: '#12173F', secondary: '#C8102E', abbr: 'LAC' });
  });
});
