// Slug utilities for team pages — built from the same data as teamNameConverter.ts

// Maps from oddsApiName → dbName for each sport
const NBA_TEAMS: Record<string, string> = {
  'Atlanta Hawks': 'Hawks',
  'Boston Celtics': 'Celtics',
  'Brooklyn Nets': 'Nets',
  'Charlotte Hornets': 'Hornets',
  'Chicago Bulls': 'Bulls',
  'Cleveland Cavaliers': 'Cavaliers',
  'Dallas Mavericks': 'Mavericks',
  'Denver Nuggets': 'Nuggets',
  'Detroit Pistons': 'Pistons',
  'Golden State Warriors': 'Warriors',
  'Houston Rockets': 'Rockets',
  'Indiana Pacers': 'Pacers',
  'Los Angeles Clippers': 'Clippers',
  'Los Angeles Lakers': 'Lakers',
  'Memphis Grizzlies': 'Grizzlies',
  'Miami Heat': 'Heat',
  'Milwaukee Bucks': 'Bucks',
  'Minnesota Timberwolves': 'Timberwolves',
  'New Orleans Pelicans': 'Pelicans',
  'New York Knicks': 'Knicks',
  'Oklahoma City Thunder': 'Thunder',
  'Orlando Magic': 'Magic',
  'Philadelphia 76ers': 'Seventysixers',
  'Phoenix Suns': 'Suns',
  'Portland Trail Blazers': 'Trailblazers',
  'Sacramento Kings': 'Kings',
  'San Antonio Spurs': 'Spurs',
  'Toronto Raptors': 'Raptors',
  'Utah Jazz': 'Jazz',
  'Washington Wizards': 'Wizards',
};

const NFL_TEAMS: Record<string, string> = {
  'Arizona Cardinals': 'Cardinals',
  'Atlanta Falcons': 'Falcons',
  'Baltimore Ravens': 'Ravens',
  'Buffalo Bills': 'Bills',
  'Carolina Panthers': 'Panthers',
  'Chicago Bears': 'Bears',
  'Cincinnati Bengals': 'Bengals',
  'Cleveland Browns': 'Browns',
  'Dallas Cowboys': 'Cowboys',
  'Denver Broncos': 'Broncos',
  'Detroit Lions': 'Lions',
  'Green Bay Packers': 'Packers',
  'Houston Texans': 'Texans',
  'Indianapolis Colts': 'Colts',
  'Jacksonville Jaguars': 'Jaguars',
  'Kansas City Chiefs': 'Chiefs',
  'Las Vegas Raiders': 'Raiders',
  'Los Angeles Chargers': 'Chargers',
  'Los Angeles Rams': 'Rams',
  'Miami Dolphins': 'Dolphins',
  'Minnesota Vikings': 'Vikings',
  'New England Patriots': 'Patriots',
  'New Orleans Saints': 'Saints',
  'New York Giants': 'Giants',
  'New York Jets': 'Jets',
  'Philadelphia Eagles': 'Eagles',
  'Pittsburgh Steelers': 'Steelers',
  'San Francisco 49ers': 'Fortyniners',
  'Seattle Seahawks': 'Seahawks',
  'Tampa Bay Buccaneers': 'Buccaneers',
  'Tennessee Titans': 'Titans',
  'Washington Commanders': 'Commanders',
};

const MLB_TEAMS: Record<string, string> = {
  'Arizona Diamondbacks': 'Diamondbacks',
  'Atlanta Braves': 'Braves',
  'Baltimore Orioles': 'Orioles',
  'Boston Red Sox': 'Red Sox',
  'Chicago Cubs': 'Cubs',
  'Chicago White Sox': 'White Sox',
  'Cincinnati Reds': 'Reds',
  'Cleveland Guardians': 'Guardians',
  'Colorado Rockies': 'Rockies',
  'Detroit Tigers': 'Tigers',
  'Houston Astros': 'Astros',
  'Kansas City Royals': 'Royals',
  'Los Angeles Angels': 'Angels',
  'Los Angeles Dodgers': 'Dodgers',
  'Miami Marlins': 'Marlins',
  'Milwaukee Brewers': 'Brewers',
  'Minnesota Twins': 'Twins',
  'New York Mets': 'Mets',
  'New York Yankees': 'Yankees',
  'Athletics': 'Athletics',
  'Philadelphia Phillies': 'Phillies',
  'Pittsburgh Pirates': 'Pirates',
  'San Diego Padres': 'Padres',
  'San Francisco Giants': 'Giants',
  'Seattle Mariners': 'Mariners',
  'St. Louis Cardinals': 'Cardinals',
  'Tampa Bay Rays': 'Rays',
  'Texas Rangers': 'Rangers',
  'Toronto Blue Jays': 'Blue Jays',
  'Washington Nationals': 'Nationals',
};

const NHL_TEAMS: Record<string, string> = {
  'Anaheim Ducks': 'Ducks',
  'Arizona Coyotes': 'Coyotes',
  'Boston Bruins': 'Bruins',
  'Buffalo Sabres': 'Sabres',
  'Calgary Flames': 'Flames',
  'Carolina Hurricanes': 'Hurricanes',
  'Chicago Blackhawks': 'Blackhawks',
  'Colorado Avalanche': 'Avalanche',
  'Columbus Blue Jackets': 'Blue Jackets',
  'Dallas Stars': 'Stars',
  'Detroit Red Wings': 'Red Wings',
  'Edmonton Oilers': 'Oilers',
  'Florida Panthers': 'Panthers',
  'Los Angeles Kings': 'Kings',
  'Minnesota Wild': 'Wild',
  'Montréal Canadiens': 'Canadiens',
  'Nashville Predators': 'Predators',
  'New Jersey Devils': 'Devils',
  'New York Islanders': 'Islanders',
  'New York Rangers': 'Rangers',
  'Ottawa Senators': 'Senators',
  'Philadelphia Flyers': 'Flyers',
  'Pittsburgh Penguins': 'Penguins',
  'San Jose Sharks': 'Sharks',
  'Seattle Kraken': 'Kraken',
  'St Louis Blues': 'Blues',
  'Tampa Bay Lightning': 'Lightning',
  'Toronto Maple Leafs': 'Maple Leafs',
  'Utah Mammoth': 'Mammoth',
  'Vancouver Canucks': 'Canucks',
  'Vegas Golden Knights': 'Knights',
  'Washington Capitals': 'Capitals',
  'Winnipeg Jets': 'Jets',
};

// NCAAF: abbreviated DB names, only include teams active in the odds API
const NCAAF_TEAMS: Record<string, string> = {
  'Abilene Christian Wildcats': 'ABCH',
  'Air Force Falcons': 'AIR',
  'Akron Zips': 'AKRON',
  'Arkansas State Red Wolves': 'AKST',
  'Alabama Crimson Tide': 'ALA',
  'Alabama A&M Bulldogs': 'ALAM',
  'Alcorn State Braves': 'ALCN',
  'Appalachian State Mountaineers': 'APP',
  'Arkansas Razorbacks': 'ARK',
  'Army Black Knights': 'ARMY',
  'Arizona Wildcats': 'ARZ',
  'Auburn Tigers': 'AUB',
  'Arizona State Sun Devils': 'AZST',
  'Ball State Cardinals': 'BALL',
  'Baylor Bears': 'BAY',
  'Boston College Eagles': 'BCOL',
  'Boise State Broncos': 'BOIS',
  'Bowling Green Falcons': 'BOWL',
  'BYU Cougars': 'BYU',
  'California Golden Bears': 'CAL',
  'UCF Knights': 'CFL',
  'Charlotte 49ers': 'CHAR',
  'Cincinnati Bearcats': 'CIN',
  'Clemson Tigers': 'CLEM',
  'Central Michigan Chippewas': 'CMCH',
  'Colorado Buffaloes': 'COLO',
  'UConn Huskies': 'CON',
  'Colorado State Rams': 'COST',
  'Coastal Carolina Chanticleers': 'CSTC',
  'Duke Blue Devils': 'DUKE',
  'East Carolina Pirates': 'ECAR',
  'Florida A&M Rattlers': 'FAM',
  'Florida Atlantic Owls': 'FATL',
  'Florida International Panthers': 'FINT',
  'Florida Gators': 'FLA',
  'Florida State Seminoles': 'FLST',
  'Fresno State Bulldogs': 'FRES',
  'Georgia State Panthers': 'GAST',
  'Georgia Bulldogs': 'GEO',
  'Georgia Southern Eagles': 'GSOU',
  'Georgia Tech Yellow Jackets': 'GTCH',
  'Hawaii Rainbow Warriors': 'HAW',
  'Houston Cougars': 'HOU',
  'Illinois Fighting Illini': 'ILL',
  'Indiana Hoosiers': 'IND',
  'Iowa Hawkeyes': 'IOWA',
  'Iowa State Cyclones': 'IWST',
  'Kansas Jayhawks': 'KAN',
  'Kansas State Wildcats': 'KAST',
  'Kent State Golden Flashes': 'KEST',
  'Kentucky Wildcats': 'KTKY',
  'Liberty Flames': 'LIB',
  'Louisiana Ragin\' Cajuns': 'LLAF',
  'UL Monroe Warhawks': 'LMON',
  'Louisville Cardinals': 'LOU',
  'LSU Tigers': 'LSU',
  'Louisiana Tech Bulldogs': 'LTCH',
  'Maryland Terrapins': 'MARY',
  'UMass Minutemen': 'MAS',
  'Michigan State Spartans': 'MCST',
  'Memphis Tigers': 'MEM',
  'Miami Hurricanes': 'MIAF',
  'Miami (OH) RedHawks': 'MIAOH',
  'Michigan Wolverines': 'MICH',
  'Minnesota Golden Gophers': 'MIN',
  'Ole Miss Rebels': 'MIS',
  'Missouri Tigers': 'MIZ',
  'Marshall Thundering Herd': 'MRSH',
  'Mississippi State Bulldogs': 'MSST',
  'Middle Tennessee Blue Raiders': 'MTEN',
  'North Alabama Lions': 'NALA',
  'Navy Midshipmen': 'NAVY',
  'North Carolina Tar Heels': 'NCAR',
  'NC State Wolfpack': 'NCST',
  'North Dakota State Bison': 'NDST',
  'Nebraska Cornhuskers': 'NEB',
  'Nevada Wolf Pack': 'NEV',
  'Northern Illinois Huskies': 'NIL',
  'New Mexico State Aggies': 'NMST',
  'New Mexico Lobos': 'NMX',
  'Northwestern Wildcats': 'NORW',
  'Notre Dame Fighting Irish': 'NOTD',
  'North Texas Mean Green': 'NTX',
  'Ohio State Buckeyes': 'OHST',
  'Ohio Bobcats': 'OHIO',
  'Oklahoma Sooners': 'OKLA',
  'Oklahoma State Cowboys': 'OKST',
  'Old Dominion Monarchs': 'OLDD',
  'Oregon Ducks': 'ORE',
  'Oregon State Beavers': 'ORST',
  'Pittsburgh Panthers': 'PIT',
  'Penn State Nittany Lions': 'PNST',
  'Purdue Boilermakers': 'PUR',
  'Rice Owls': 'RICE',
  'Rutgers Scarlet Knights': 'RUT',
  'South Alabama Jaguars': 'SALA',
  'South Carolina Gamecocks': 'SCAR',
  'San Diego State Aztecs': 'SDST',
  'South Florida Bulls': 'SFL',
  'Sam Houston State Bearkats': 'SHST',
  'Southern Illinois Salukis': 'SIL',
  'San Jose State Spartans': 'SJST',
  'Southern Mississippi Golden Eagles': 'SMIS',
  'SMU Mustangs': 'SMU',
  'Stanford Cardinal': 'STAN',
  'Syracuse Orange': 'SYR',
  'TCU Horned Frogs': 'TCU',
  'Temple Owls': 'TEM',
  'Tennessee Volunteers': 'TEN',
  'Texas Longhorns': 'TEX',
  'Tulane Green Wave': 'TLN',
  'Tulsa Golden Hurricane': 'TLS',
  'Toledo Rockets': 'TOL',
  'Troy Trojans': 'TROY',
  'Texas A&M Aggies': 'TXAM',
  'Texas Southern Tigers': 'TXSO',
  'Texas State Bobcats': 'TXST',
  'Texas Tech Red Raiders': 'TXT',
  'UAB Blazers': 'UAB',
  'UCLA Bruins': 'UCLA',
  'UNLV Rebels': 'UNLV',
  'USC Trojans': 'USC',
  'Utah Utes': 'UTAH',
  'UTEP Miners': 'UTEP',
  'UT San Antonio Roadrunners': 'UTSA',
  'Utah State Aggies': 'UTST',
  'Vanderbilt Commodores': 'VAN',
  'Virginia Cavaliers': 'VIR',
  'Virginia Tech Hokies': 'VTCH',
  'Wake Forest Demon Deacons': 'WAKE',
  'Washington Huskies': 'WAS',
  'Washington State Cougars': 'WAST',
  'Weber State Wildcats': 'WEB',
  'Wisconsin Badgers': 'WIS',
  'Western Kentucky Hilltoppers': 'WKY',
  'Western Michigan Broncos': 'WMCH',
  'West Virginia Mountaineers': 'WVA',
  'Wyoming Cowboys': 'WYO',
};

// NCAAB: abbreviated DB names
const NCAAB_TEAMS: Record<string, string> = {
  'Alabama Crimson Tide': 'ALAB',
  'Arizona Wildcats': 'ARZ',
  'Arizona State Sun Devils': 'ARZST',
  'Arkansas Razorbacks': 'ARK',
  'Auburn Tigers': 'AUB',
  'Baylor Bears': 'BAY',
  'Boston College Eagles': 'BC',
  'BYU Cougars': 'BYU',
  'California Golden Bears': 'CAL',
  'Cincinnati Bearcats': 'CIN',
  'Clemson Tigers': 'CLEM',
  'Colorado Buffaloes': 'COL',
  'Colorado State Rams': 'COLST',
  'Connecticut Huskies': 'UCONN',
  'UConn Huskies': 'UCONN',
  'Creighton Bluejays': 'CRE',
  'Dayton Flyers': 'DAYT',
  'Duke Blue Devils': 'DUKE',
  'Florida Gators': 'FLA',
  'Florida State Seminoles': 'FSU',
  'Gonzaga Bulldogs': 'GONZ',
  'Georgia Bulldogs': 'GEOR',
  'Houston Cougars': 'HOU',
  'Illinois Fighting Illini': 'ILL',
  'Indiana Hoosiers': 'IND',
  'Iowa Hawkeyes': 'IOWA',
  'Iowa State Cyclones': 'IAST',
  'Kansas Jayhawks': 'KAN',
  'Kansas State Wildcats': 'KANST',
  'Kentucky Wildcats': 'KENTY',
  'LSU Tigers': 'LSU',
  'Marquette Golden Eagles': 'MARQ',
  'Maryland Terrapins': 'MARY',
  'Memphis Tigers': 'MEM',
  'Michigan Wolverines': 'MICH',
  'Michigan State Spartans': 'MCHST',
  'Missouri Tigers': 'MISSO',
  'Nebraska Cornhuskers': 'NEB',
  'North Carolina Tar Heels': 'NOCAR',
  'NC State Wolfpack': 'NCSTA',
  'Northwestern Wildcats': 'NORW',
  'Notre Dame Fighting Irish': 'NOTRE',
  'Ohio State Buckeyes': 'OHIOS',
  'Oklahoma Sooners': 'OKL',
  'Oklahoma State Cowboys': 'OKLST',
  'Ole Miss Rebels': 'OLMIS',
  'Oregon Ducks': 'ORE',
  'Oregon State Beavers': 'ORST',
  'Penn State Nittany Lions': 'PENST',
  'Pittsburgh Panthers': 'PITT',
  'Purdue Boilermakers': 'PURD',
  'Rutgers Scarlet Knights': 'RUTG',
  'San Diego State Aztecs': 'SDST',
  'Seton Hall Pirates': 'SETHA',
  'SMU Mustangs': 'SMU',
  'South Carolina Gamecocks': 'SOCAR',
  'St. John\'s Red Storm': 'STJ',
  'Stanford Cardinal': 'STAN',
  'Syracuse Orange': 'SYR',
  'TCU Horned Frogs': 'TCU',
  'Tennessee Volunteers': 'TENN',
  'Texas Longhorns': 'TEX',
  'Texas A&M Aggies': 'TXAM',
  'Texas Tech Red Raiders': 'TXTCH',
  'UCLA Bruins': 'UCLA',
  'UNLV Rebels': 'UNLV',
  'USC Trojans': 'USC',
  'Utah Utes': 'UTAH',
  'Utah State Aggies': 'UTST',
  'Vanderbilt Commodores': 'VANDY',
  'VCU Rams': 'VCU',
  'Villanova Wildcats': 'VILLA',
  'Virginia Cavaliers': 'VIRG',
  'Virginia Tech Hokies': 'VTECH',
  'Wake Forest Demon Deacons': 'WFRST',
  'Washington Huskies': 'WGTON',
  'West Virginia Mountaineers': 'WVA',
  'Wisconsin Badgers': 'WISC',
  'Xavier Musketeers': 'XAVER',
};

const SPORT_MAPS: Record<string, Record<string, string>> = {
  nba: NBA_TEAMS,
  nfl: NFL_TEAMS,
  mlb: MLB_TEAMS,
  nhl: NHL_TEAMS,
  ncaaf: NCAAF_TEAMS,
  ncaab: NCAAB_TEAMS,
};

// Sports with team-slug infrastructure (and thus matchup-page support) — soccer isn't
// included here yet, so callers should fall back to the legacy ?game_id= link for it.
export const MATCHUP_SLUG_SPORTS = new Set(Object.keys(SPORT_MAPS));

// Core slugify: "Los Angeles Lakers" → "los-angeles-lakers"
export function oddsApiNameToSlug(name: string): string {
  return name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
}

// Build a link to a team page from sport + oddsApiName
export function getTeamPageLink(sport: string, oddsApiName: string): string {
  return `/team/${sport}/${oddsApiNameToSlug(oddsApiName)}`;
}

// Given sport + slug, return { oddsApiName, dbName } or null if not found
export function getTeamBySlug(
  sport: string,
  slug: string
): { oddsApiName: string; dbName: string } | null {
  const map = SPORT_MAPS[sport];
  if (!map) return null;

  for (const [oddsApiName, dbName] of Object.entries(map)) {
    if (oddsApiNameToSlug(oddsApiName) === slug) {
      return { oddsApiName, dbName };
    }
  }
  return null;
}

// Given sport + dbName (as stored in DB), return the slug or null if not found
export function dbNameToSlug(dbName: string, sport: string): string | null {
  const map = SPORT_MAPS[sport];
  if (!map) return null;

  for (const [oddsApiName, db] of Object.entries(map)) {
    if (db === dbName) {
      return oddsApiNameToSlug(oddsApiName);
    }
  }
  return null;
}

// Convert a game's commence_time to the Eastern-time calendar date (YYYY-MM-DD)
// used in matchup slugs/URLs — the date fans think of the game as being "on",
// not the UTC date the backend stores it in. Games starting after ~8pm ET land
// on the next UTC calendar day, so a naive commenceTime.split('T')[0] is wrong
// for a large share of night games.
//
// DB-fallback games (source: "db") carry a bare date with no time component
// (e.g. "2026-06-14", no "T") — that's already the correct calendar date as
// seeded, so it's returned unchanged rather than run through a timezone
// conversion that would shift it a day earlier.
export function getEasternDateStr(commenceTime: string): string {
  if (!commenceTime.includes('T')) return commenceTime;
  return new Date(commenceTime).toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
}

// Matchup slugs: "<away-slug>-vs-<home-slug>-<YYYY-MM-DD>", optional "-2" suffix
// for same-day rematches (MLB doubleheaders in practice).
export function buildMatchupSlug(
  awayName: string,
  homeName: string,
  commenceTime: string,
  occurrence: number = 1
): string {
  const dateStr = getEasternDateStr(commenceTime);
  const base = `${oddsApiNameToSlug(awayName)}-vs-${oddsApiNameToSlug(homeName)}-${dateStr}`;
  return occurrence > 1 ? `${base}-${occurrence}` : base;
}

export function getMatchupPageLink(
  sport: string,
  awayName: string,
  homeName: string,
  commenceTime: string,
  occurrence: number = 1
): string {
  return `/game-details/${sport}/${buildMatchupSlug(awayName, homeName, commenceTime, occurrence)}`;
}

export interface ParsedMatchupSlug {
  awaySlug: string;
  homeSlug: string;
  date: string;
  occurrence: number;
}

export function parseMatchupSlug(slug: string): ParsedMatchupSlug | null {
  const m = slug.match(/^([a-z0-9-]+?)-vs-([a-z0-9-]+)-(\d{4}-\d{2}-\d{2})(?:-(\d+))?$/);
  if (!m) return null;
  return {
    awaySlug: m[1],
    homeSlug: m[2],
    date: m[3],
    occurrence: m[4] ? parseInt(m[4], 10) : 1,
  };
}
