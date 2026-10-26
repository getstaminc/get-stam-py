// Team brand colors for the TeamLogo component. Keys are the SHORT team names
// already produced by utils/teamNameConverter.ts / utils/teamSlugUtils.ts
// (e.g. "Brewers", not "Milwaukee Brewers"). Only the 4 pro leagues are
// hand-curated here — NCAAF/NCAAB (hundreds of schools) fall back to the
// neutral entry until colors are supplied separately.

export interface TeamColorEntry {
  primary: string;
  secondary: string;
  abbr: string;
}

export const NEUTRAL_FALLBACK = { primary: '#4a5361', secondary: '#ffffff' };

const MLB_COLORS: Record<string, TeamColorEntry> = {
  Diamondbacks: { primary: '#A71930', secondary: '#E3D4AD', abbr: 'ARI' },
  Braves: { primary: '#13274F', secondary: '#FFFFFF', abbr: 'ATL' },
  Orioles: { primary: '#DF4601', secondary: '#000000', abbr: 'BAL' },
  'Red Sox': { primary: '#BD3039', secondary: '#FFFFFF', abbr: 'BOS' },
  Cubs: { primary: '#0E3386', secondary: '#FFFFFF', abbr: 'CHC' },
  'White Sox': { primary: '#27251F', secondary: '#C4CED4', abbr: 'CWS' },
  Reds: { primary: '#C6011F', secondary: '#FFFFFF', abbr: 'CIN' },
  Guardians: { primary: '#0C2340', secondary: '#FFFFFF', abbr: 'CLE' },
  Rockies: { primary: '#333366', secondary: '#C4CED4', abbr: 'COL' },
  Tigers: { primary: '#0C2340', secondary: '#FA4616', abbr: 'DET' },
  Astros: { primary: '#002D62', secondary: '#EB6E1F', abbr: 'HOU' },
  Royals: { primary: '#004687', secondary: '#BD9B60', abbr: 'KC' },
  Angels: { primary: '#BA0021', secondary: '#FFFFFF', abbr: 'LAA' },
  Dodgers: { primary: '#005A9C', secondary: '#FFFFFF', abbr: 'LAD' },
  Marlins: { primary: '#00A3E0', secondary: '#FFFFFF', abbr: 'MIA' },
  Brewers: { primary: '#13294B', secondary: '#FFC52F', abbr: 'MIL' },
  Twins: { primary: '#002B5C', secondary: '#FFFFFF', abbr: 'MIN' },
  Mets: { primary: '#002D72', secondary: '#FF5910', abbr: 'NYM' },
  Yankees: { primary: '#0C2340', secondary: '#FFFFFF', abbr: 'NYY' },
  Athletics: { primary: '#003831', secondary: '#EFB21E', abbr: 'ATH' },
  Phillies: { primary: '#E81828', secondary: '#FFFFFF', abbr: 'PHI' },
  Pirates: { primary: '#27251F', secondary: '#FDB827', abbr: 'PIT' },
  Padres: { primary: '#2F241D', secondary: '#FFC425', abbr: 'SD' },
  Giants: { primary: '#27251F', secondary: '#FD5A1E', abbr: 'SF' },
  Mariners: { primary: '#0C2C56', secondary: '#C4CED4', abbr: 'SEA' },
  Cardinals: { primary: '#C41E3A', secondary: '#FFFFFF', abbr: 'STL' },
  Rays: { primary: '#092C5C', secondary: '#8FBCE6', abbr: 'TB' },
  Rangers: { primary: '#003278', secondary: '#FFFFFF', abbr: 'TEX' },
  'Blue Jays': { primary: '#134A8E', secondary: '#FFFFFF', abbr: 'TOR' },
  Nationals: { primary: '#14225A', secondary: '#FFFFFF', abbr: 'WSH' },
};

const NFL_COLORS: Record<string, TeamColorEntry> = {
  Cardinals: { primary: '#97233F', secondary: '#FFFFFF', abbr: 'ARI' },
  Falcons: { primary: '#A71930', secondary: '#FFFFFF', abbr: 'ATL' },
  Ravens: { primary: '#241773', secondary: '#9E7C0C', abbr: 'BAL' },
  Bills: { primary: '#00338D', secondary: '#FFFFFF', abbr: 'BUF' },
  Panthers: { primary: '#0085CA', secondary: '#FFFFFF', abbr: 'CAR' },
  Bears: { primary: '#0B162A', secondary: '#C83803', abbr: 'CHI' },
  Bengals: { primary: '#FB4F14', secondary: '#000000', abbr: 'CIN' },
  Browns: { primary: '#311D00', secondary: '#FF3C00', abbr: 'CLE' },
  Cowboys: { primary: '#041E42', secondary: '#869397', abbr: 'DAL' },
  Broncos: { primary: '#002244', secondary: '#FB4F14', abbr: 'DEN' },
  Lions: { primary: '#0076B6', secondary: '#B0B7BC', abbr: 'DET' },
  Packers: { primary: '#203731', secondary: '#FFB612', abbr: 'GB' },
  Texans: { primary: '#03202F', secondary: '#FFFFFF', abbr: 'HOU' },
  Colts: { primary: '#002C5F', secondary: '#A2AAAD', abbr: 'IND' },
  Jaguars: { primary: '#101820', secondary: '#D7A22A', abbr: 'JAX' },
  Chiefs: { primary: '#E31837', secondary: '#FFB81C', abbr: 'KC' },
  Raiders: { primary: '#000000', secondary: '#A5ACAF', abbr: 'LV' },
  Chargers: { primary: '#0080C6', secondary: '#FFC20E', abbr: 'LAC' },
  Rams: { primary: '#003594', secondary: '#FFA300', abbr: 'LAR' },
  Dolphins: { primary: '#008E97', secondary: '#FC4C02', abbr: 'MIA' },
  Vikings: { primary: '#4F2683', secondary: '#FFC62F', abbr: 'MIN' },
  Patriots: { primary: '#002244', secondary: '#FFFFFF', abbr: 'NE' },
  Saints: { primary: '#101820', secondary: '#D3BC8D', abbr: 'NO' },
  Giants: { primary: '#0B2265', secondary: '#FFFFFF', abbr: 'NYG' },
  Jets: { primary: '#125740', secondary: '#FFFFFF', abbr: 'NYJ' },
  Eagles: { primary: '#004C54', secondary: '#A5ACAF', abbr: 'PHI' },
  Steelers: { primary: '#101820', secondary: '#FFB612', abbr: 'PIT' },
  Fortyniners: { primary: '#AA0000', secondary: '#B3995D', abbr: 'SF' },
  Seahawks: { primary: '#002244', secondary: '#69BE28', abbr: 'SEA' },
  Buccaneers: { primary: '#D50A0A', secondary: '#FFFFFF', abbr: 'TB' },
  Titans: { primary: '#0C2340', secondary: '#4B92DB', abbr: 'TEN' },
  Commanders: { primary: '#5A1414', secondary: '#FFB612', abbr: 'WAS' },
};

const NBA_COLORS: Record<string, TeamColorEntry> = {
  Hawks: { primary: '#E03A3E', secondary: '#C1D32F', abbr: 'ATL' },
  Celtics: { primary: '#007A33', secondary: '#BA9653', abbr: 'BOS' },
  Nets: { primary: '#000000', secondary: '#FFFFFF', abbr: 'BKN' },
  Hornets: { primary: '#1D1160', secondary: '#00788C', abbr: 'CHA' },
  Bulls: { primary: '#CE1141', secondary: '#FFFFFF', abbr: 'CHI' },
  Cavaliers: { primary: '#6F263D', secondary: '#FFB81C', abbr: 'CLE' },
  Mavericks: { primary: '#00538C', secondary: '#B8C4CA', abbr: 'DAL' },
  Nuggets: { primary: '#0E2240', secondary: '#FEC524', abbr: 'DEN' },
  Pistons: { primary: '#C8102E', secondary: '#FFFFFF', abbr: 'DET' },
  Warriors: { primary: '#1D428A', secondary: '#FFC72C', abbr: 'GSW' },
  Rockets: { primary: '#CE1141', secondary: '#FFFFFF', abbr: 'HOU' },
  Pacers: { primary: '#002D62', secondary: '#FDBB30', abbr: 'IND' },
  Clippers: { primary: '#1D428A', secondary: '#FFFFFF', abbr: 'LAC' },
  Lakers: { primary: '#552583', secondary: '#FDB927', abbr: 'LAL' },
  Grizzlies: { primary: '#12173F', secondary: '#F5B112', abbr: 'MEM' },
  Heat: { primary: '#98002E', secondary: '#F9A01B', abbr: 'MIA' },
  Bucks: { primary: '#00471B', secondary: '#EEE1C6', abbr: 'MIL' },
  Timberwolves: { primary: '#0C2340', secondary: '#78BE20', abbr: 'MIN' },
  Pelicans: { primary: '#0C2340', secondary: '#85714D', abbr: 'NOP' },
  Knicks: { primary: '#006BB6', secondary: '#F58426', abbr: 'NYK' },
  Thunder: { primary: '#007AC1', secondary: '#EF3B24', abbr: 'OKC' },
  Magic: { primary: '#0077C0', secondary: '#C4CED4', abbr: 'ORL' },
  Seventysixers: { primary: '#006BB6', secondary: '#FFFFFF', abbr: 'PHI' },
  Suns: { primary: '#1D1160', secondary: '#E56020', abbr: 'PHX' },
  Trailblazers: { primary: '#000000', secondary: '#E03A3E', abbr: 'POR' },
  Kings: { primary: '#5A2D81', secondary: '#63727A', abbr: 'SAC' },
  Spurs: { primary: '#000000', secondary: '#C4CED4', abbr: 'SAS' },
  Raptors: { primary: '#CE1141', secondary: '#FFFFFF', abbr: 'TOR' },
  Jazz: { primary: '#002B5C', secondary: '#F9A01B', abbr: 'UTA' },
  Wizards: { primary: '#002B5C', secondary: '#FFFFFF', abbr: 'WAS' },
};

const NHL_COLORS: Record<string, TeamColorEntry> = {
  Ducks: { primary: '#F47A38', secondary: '#000000', abbr: 'ANA' },
  Coyotes: { primary: '#8C2633', secondary: '#E2D6B5', abbr: 'ARI' },
  Bruins: { primary: '#000000', secondary: '#FFB81C', abbr: 'BOS' },
  Sabres: { primary: '#002654', secondary: '#FCB514', abbr: 'BUF' },
  Flames: { primary: '#C8102E', secondary: '#F1BE48', abbr: 'CGY' },
  Hurricanes: { primary: '#CC0000', secondary: '#FFFFFF', abbr: 'CAR' },
  Blackhawks: { primary: '#000000', secondary: '#CF0A2C', abbr: 'CHI' },
  Avalanche: { primary: '#6F263D', secondary: '#A2AAAD', abbr: 'COL' },
  'Blue Jackets': { primary: '#002654', secondary: '#FFFFFF', abbr: 'CBJ' },
  Stars: { primary: '#006847', secondary: '#8F8F8C', abbr: 'DAL' },
  'Red Wings': { primary: '#CE1126', secondary: '#FFFFFF', abbr: 'DET' },
  Oilers: { primary: '#041E42', secondary: '#FF4C00', abbr: 'EDM' },
  Panthers: { primary: '#C8102E', secondary: '#B9975B', abbr: 'FLA' },
  Kings: { primary: '#111111', secondary: '#A2AAAD', abbr: 'LAK' },
  Wild: { primary: '#154734', secondary: '#DDCBA4', abbr: 'MIN' },
  Canadiens: { primary: '#AF1E2D', secondary: '#FFFFFF', abbr: 'MTL' },
  Predators: { primary: '#041E42', secondary: '#FFB81C', abbr: 'NSH' },
  Devils: { primary: '#CE1126', secondary: '#FFFFFF', abbr: 'NJD' },
  Islanders: { primary: '#00539B', secondary: '#F47D30', abbr: 'NYI' },
  Rangers: { primary: '#0038A8', secondary: '#FFFFFF', abbr: 'NYR' },
  Senators: { primary: '#C52032', secondary: '#C2912C', abbr: 'OTT' },
  Flyers: { primary: '#F74902', secondary: '#000000', abbr: 'PHI' },
  Penguins: { primary: '#000000', secondary: '#FCB514', abbr: 'PIT' },
  Sharks: { primary: '#006D75', secondary: '#EA7200', abbr: 'SJS' },
  Kraken: { primary: '#001628', secondary: '#99D9D9', abbr: 'SEA' },
  Blues: { primary: '#002F87', secondary: '#FCB514', abbr: 'STL' },
  Lightning: { primary: '#002868', secondary: '#FFFFFF', abbr: 'TBL' },
  'Maple Leafs': { primary: '#00205B', secondary: '#FFFFFF', abbr: 'TOR' },
  Mammoth: { primary: '#0F0F0F', secondary: '#71C5E8', abbr: 'UTA' },
  Canucks: { primary: '#00205B', secondary: '#00843D', abbr: 'VAN' },
  Knights: { primary: '#333F42', secondary: '#B4975A', abbr: 'VGK' },
  Capitals: { primary: '#041E42', secondary: '#FFFFFF', abbr: 'WSH' },
  Jets: { primary: '#041E42', secondary: '#FFFFFF', abbr: 'WPG' },
};

const COLOR_TABLES: Record<string, Record<string, TeamColorEntry>> = {
  mlb: MLB_COLORS,
  nfl: NFL_COLORS,
  nba: NBA_COLORS,
  nhl: NHL_COLORS,
};

export function getTeamColors(dbSport: string, teamName: string): TeamColorEntry {
  const table = COLOR_TABLES[dbSport];
  const entry = table?.[teamName];
  if (entry) return entry;

  const abbr = (teamName || '').replace(/[^A-Za-z]/g, '').slice(0, 3).toUpperCase() || '?';
  return { ...NEUTRAL_FALLBACK, abbr };
}
