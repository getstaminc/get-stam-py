import pytz

eastern_tz = pytz.timezone('US/Eastern')

def convert_to_eastern(utc_time):
    if utc_time is None:
        return None
    utc_time = utc_time.replace(tzinfo=pytz.utc)
    eastern_time = utc_time.astimezone(eastern_tz)
    return eastern_time

def convert_team_name(full_team_name):
    team_map = {
        # MLB Teams
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
        'Oakland Athletics': 'Athletics',
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
        
        # NFL Teams
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

        #NHL
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
        'Utah Hockey Club': 'Hockey Club',
        'Vancouver Canucks': 'Canucks',
        'Vegas Golden Knights': 'Knights',
        'Washington Capitals': 'Capitals',
        'Winnipeg Jets': 'Jets',

        # NCAA
        'Alabama A&M Bulldogs': 'ABAM',
        'Alabama Crimson Tide': 'ALAB',
        'Alabama St Hornets': 'ALAST',
        'Alcorn St Braves': 'ALCST',
        'American University Eagles': 'AMERU',
        'Appalachian State Mountaineers': 'APPST',
        'Arkansas Razorbacks': 'ARK',
        'Arkansas-Pine Bluff Golden Lions': 'ARKPB',
        'Arkansas State Red Wolves': 'ARKST',
        'Army Black Knights': 'ARMY',
        'Arizona State Sun Devils': 'ARZST',
        'Arizona Wildcats': 'ARZ',
        'Auburn Tigers': 'AUB',
        'Austin Peay Governors': 'AUPEA',
        'Ball State Cardinals': 'BALLST',
        'Baylor Bears': 'BAY',
        'Belmont Bruins': 'BELM',
        'Bellarmine Knights': 'BELL',
        'Bethune-Cookman Wildcats': 'BCOOK',
        'Binghamton Bearcats': 'BING',
        'Boise State Broncos': 'BOIST',
        'Boston College Eagles': 'BC',
        'Boston University Terriers': 'BU',
        'Bowling Green Falcons': 'BGRN',
        'Brown Bears': 'BROWN',
        'Bryant Bulldogs': 'BRYNT',
        'Bucknell Bison': 'BUCK',
        'Buffalo Bulls': 'BUF',
        'Butler Bulldogs': 'BUT',
        'BYU Cougars': 'BYU',
        'Cal Baptist Lancers': 'CALBA',
        'Cal Poly Mustangs': 'CALPO',
        'Cal State Bakersfield Roadrunners': 'CALSB',
        'Cal State Fullerton Titans': 'CSFUL',
        'Cal State Northridge Matadors': 'CSNOR',
        'California Golden Bears': 'CAL',
        'Campbell Fighting Camels': 'CAMP',
        'Central Arkansas Bears': 'CENAR',
        'Central Connecticut Blue Devils': 'CCONS',
        'Central Michigan Chippewas': 'CMICH',
        'Charleston Cougars': 'CHARL',
        'Charleston Southern Buccaneers': 'CHASO',
        'Charlotte 49ers': 'CHAR',
        'Chattanooga Mocs': 'CHAT',
        'Chicago State Cougars': 'CHIST',
        'Cincinnati Bearcats': 'CIN',
        'Clemson Tigers': 'CLEM',
        'Colgate Raiders': 'COLG',
        'Columbia Lions': 'COLU',
        'Columbia Lions': 'COL',
        'Colorado State Rams': 'COLST',
        'Cornell Big Red': 'CORN',
        'Cornell Big Red': 'CFLR',
        'Coastal Carolina Chanticleers': 'CCAR',
        'Coppin St Eagles': 'COPST',
        'Dartmouth Big Green': 'DART',
        'Davidson Wildcats': 'DAV',
        'Dayton Flyers': 'DAYT',
        'Delaware Blue Hens': 'DELA',
        'Delaware St Hornets': 'DELST',
        'Denver Pioneers': 'DENV',
        'DePaul Blue Demons': 'DEP',
        'Drexel Dragons': 'DREX',
        'Duke Blue Devils': 'DUKE',
        'Duquesne Dukes': 'DUQ',
        'East Carolina Pirates': 'ECAR',
        'East Tennessee State Buccaneers': 'ETENS',
        'Eastern Illinois Panthers': 'EILL',
        'Eastern Kentucky Colonels': 'EKY',
        'Eastern Michigan Eagles': 'EMICH',
        'Eastern Washington Eagles': 'EWAS',
        'Elon Phoenix': 'ELCOL',
        'Fairleigh Dickinson Knights': 'FDICK',
        'Florida A&M Rattlers': 'FAMU',
        'Florida Gators': 'FLA',
        'Florida Gulf Coast Eagles': 'FLOGC',
        'Florida State Seminoles': 'FSU',
        'Fordham Rams': 'FORD',
        'Fresno State Bulldogs': 'FRSNO',
        'Furman Paladins': 'FURM',
        'Gardner-Webb Runnin\' Bulldogs': 'GARDW',
        'George Mason Patriots': 'GMASN',
        'George Washington Colonials': 'GW',
        'Georgetown Hoyas': 'GEOR',
        'Georgia Southern Eagles': 'GASO',
        'Georgia State Panthers': 'GAST',
        'Georgia Tech Yellow Jackets': 'GATEC',
        'Georgia Tech Yellow Jackets': 'GT',
        'Gonzaga Bulldogs': 'GONZ',
        'Grambling St Tigers': 'GRAMB',
        'Grand Canyon Antelopes': 'GC',
        'Hampton Pirates': 'HAMP',
        'Harvard Crimson': 'HARV',
        'Hawaii Rainbow Warriors': 'HAW',
        'Hofstra Pride': 'HOF',
        'Holy Cross Crusaders': 'HCROS',
        'Houston Christian Huskies': 'HOUBA',
        'Houston Cougars': 'HOU',
        'Howard Bison': 'HOW',
        'Idaho State Bengals': 'IDST',
        'Idaho Vandals': 'IDAHO',
        'Illinois Fighting Illini': 'ILL',
        'Illinois State Redbirds': 'ILLST',
        'Incarnate Word Cardinals': 'IW',
        'Indiana State Sycamores': 'INDST',
        'Iowa State Cyclones': 'IAST',
        'Jackson St Tigers': 'JCKST',
        'Jacksonville Dolphins': 'JCKSN',
        'Jacksonville State Gamecocks': 'JACST',
        'James Madison Dukes': 'JMAD',
        'Kansas Jayhawks': 'KAN',
        'Kansas St Wildcats': 'KANST',
        'Kentucky Wildcats': 'KENTY',
        'Lafayette Leopards': 'LAFA',
        'Lamar Cardinals': 'LAMAR',
        'La Salle Explorers': 'LASAL',
        'Le Moyne Dolphins': 'LMOYNE',
        'Lehigh Mountain Hawks': 'LEHI',
        'Liberty Flames': 'LIB',
        'Lindenwood Lions': 'LNDNWD',
        'Lipscomb Bisons': 'LIPSC',
        'LIU Sharks': 'LIU',
        'Longwood Lancers': 'LONGW',
        'Louisiana Tech Bulldogs': 'LOUTE',
        'Loyola Chicago Ramblers': 'LOULA',
        'Loyola Marymount Lions': 'LOMAR',
        'Loyola Maryland Greyhounds': 'LOYMD',
        'LSU Tigers': 'LSU',
        'Maine Black Bears': 'MAINE',
        'Marist Red Foxes': 'MARS',
        'Maryland Terrapins': 'MARY',
        'Maryland-Eastern Shore Hawks': 'MDESH',
        'Massachusetts Minutemen': 'MASS',
        'McNeese Cowboys': 'MCNST',
        'Mercer Bears': 'MER',
        'Merrimack Warriors': 'MERH',
        'Miami (OH) RedHawks': 'MIAOH',
        'Miami Hurricanes': 'MIAFL',
        'Michigan Wolverines': 'MICH',
        'Michigan St Spartans': 'MCHST',
        'Middle Tennessee Blue Raiders': 'MIDTN',
        'Miss Valley St Delta Devils': 'MSVAS',
        'Mississippi State Bulldogs': 'MISST',
        'Missouri Tigers': 'MISSO',
        'Monmouth Hawks': 'MONNJ',
        'Montana Grizzlies': 'MONT',
        'Montana State Bobcats': 'MONST',
        'Morgan St Bears': 'MORGS',
        'Morgan State Bears': 'MORST',
        'Murray St Racers': 'MURST',
        'Navy Midshipmen': 'NAVY',
        'Nebraska Omaha Mavericks': 'NEBO',
        'New Hampshire Wildcats': 'NH',
        'New Mexico State Aggies': 'NMEXS',
        'Nicholls St Colonels': 'NICST',
        'NJIT Highlanders': 'NJIT',
        'North Alabama Lions': 'NORAL',
        'North Carolina A&T Aggies': 'NCATT',
        'North Carolina Asheville Bulldogs': 'NCASH',
        'North Carolina Central Eagles': 'NCCEN',
        'North Carolina State Wolfpack': 'NCSTA',
        'North Dakota Fighting Hawks': 'NDAKOT',
        'North Dakota State Bison': 'NODAK',
        'North Florida Ospreys': 'NFLA',
        'Northern Colorado Bears': 'NOCOL',
        'Northern Illinois Huskies': 'NOILL',
        'Northern Iowa Panthers': 'NIOWA',
        'Northwestern St Demons': 'NWST',
        'Old Dominion Monarchs': 'OLDOM',
        'Oklahoma Sooners': 'OKL',
        'Oklahoma State Cowboys': 'OKLST',
        'Ole Miss Rebels': 'OLMIS',
        'Oral Roberts Golden Eagles': 'ORROB',
        'Oregon State Beavers': 'ORST',
        'Pacific Tigers': 'PAC',
        'Penn Quakers': 'PENN',
        'Penn State Nittany Lions': 'PENST',
        'Pepperdine Waves': 'PEP',
        'Pittsburgh Panthers': 'PITT',
        'Portland Pilots': 'POR',
        'Portland State Vikings': 'PORST',
        'Prairie View Panthers': 'PVAM',
        'Presbyterian Blue Hose': 'PRES',
        'Princeton Tigers': 'PRINC',
        'Providence Friars': 'PROV',
        'Purdue Boilermakers': 'PURD',
        'Purdue Fort Wayne Mastodons': 'PFW',
        'Queens Royals': 'Royals',
        'Rhode Island Rams': 'RI',
        'Rice Owls': 'RICE',
        'Richmond Spiders': 'RICH',
        'Robert Morris Colonials': 'RMORR',
        'Sacramento State Hornets': 'SACST',
        'Saint Bonaventure Bonnies': 'STBON',
        'Saint Joseph\'s Hawks': 'STJOE',
        'Saint Mary\'s Gaels': 'STM',
        'Samford Bulldogs': 'SAM',
        'San Diego State Aztecs': 'SDST',
        'San Diego Toreros': 'SD',
        'San Francisco Dons': 'SF',
        'Seattle Redhawks': 'SEA',
        'SE Louisiana Lions': 'SELOU',
        'Seton Hall Pirates': 'SETHA',
        'SFA Lumberjacks': 'SFAUS',
        'SIU Edwardsville Cougars': 'SIUED',
        'SMU Mustangs': 'SMU',
        'Southern Illinois Salukis': 'SOILL',
        'Southern Indiana Screaming Eagles': 'SIND',
        'Southern Jaguars': 'SOU',
        'Southern Miss Golden Eagles': 'SOMIS',
        'Southern Utah Thunderbirds': 'SUTAH',
        'South Alabama Jaguars': 'SALAB',
        'South Carolina Gamecocks': 'SOCAR',
        'South Carolina St Bulldogs': 'SCST',
        'Stanford Cardinal': 'STAN',
        'Stephen F. Austin Lumberjacks': 'SFAUS',
        'Stetson Hatters': 'STET',
        'St. Francis Brooklyn Terriers': 'STFRP',
        'St. Thomas Tommies': 'STT',
        'Stonehill Skyhawks': 'STONE',
        'Stony Brook Seawolves': 'STO',
        'Syracuse Orange': 'SYR',
        'Tarleton State Texans': 'FLINT',
        'Tarleton State Texans': 'TST',
        'TCU Horned Frogs': 'TCU',
        'Tennessee-Martin Skyhawks': 'TNMA',
        'Tennessee State Tigers': 'TENST',
        'Tennessee Tech Golden Eagles': 'TNTCH',
        'Tennessee Volunteers': 'TENN',
        'Texas A&M Aggies': 'TXAM',
        'Texas A&M-CC Islanders': 'TXCC',
        'Texas A&M-Commerce Lions': 'TXCOM',
        'Texas College Steers': 'TXCOM',
        'Texas Longhorns': 'TEX',
        'Texas Southern Tigers': 'TXSOU',
        'Texas State Bobcats': 'TXST',
        'Texas Tech Red Raiders': 'TXTCH',
        'Towson Tigers': 'TWSN',
        'Troy Trojans': 'TROY',
        'Tulane Green Wave': 'TLANE',
        'Tulsa Golden Hurricane': 'TLSA',
        'UC Davis Aggies': 'UCDAV',
        'UC Irvine Anteaters': 'UCIRV',
        'UC Riverside Highlanders': 'UCRIV',
        'UC San Diego Tritons': 'UCSD',
        'UC Santa Barbara Gauchos': 'UCSB',
        'UConn Huskies': 'UCONN',
        'UL Monroe Warhawks': 'ULMON',
        'UMass Lowell River Hawks': 'UMASS',
        'UMass Minutemen': 'UMASS',
        'UMBC Retrievers': 'UMBC',
        'UNLV Rebels': 'UNLV',
        'USC Trojans': 'USC',
        'USC Upstate Spartans': 'SCSPAR',
        'UT Arlington Mavericks': 'TXARL',
        'UTEP Miners': 'UTEP',
        'UT Rio Grande Valley Vaqueros': 'UTRGV',
        'Utah Utes': 'UTAH',
        'Utah Valley Wolverines': 'UTVAL',
        'Vanderbilt Commodores': 'VANDY',
        'Vermont Catamounts': 'VERM',
        'Villanova Wildcats': 'VILLA',
        'Virginia Cavaliers': 'VIRG',
        'Virginia Tech Hokies': 'VTECH',
        'VMI Keydets': 'VMI',
        'Wake Forest Demon Deacons': 'WFRST',
        'Washington Huskies': 'WGTON',
        'Washington State Cougars': 'WAST',
        'Weber State Wildcats': 'WEBST',
        'West Georgia Wolves': 'UWG',
        'West Virginia Mountaineers': 'WVA',
        'Western Carolina Catamounts': 'WCAR',
        'Western Kentucky Hilltoppers': 'WKY',
        'Western Michigan Broncos': 'WMICH',
        'William & Mary Tribe': 'WILLI',
        'William & Mary Tribe': 'WMMRY',
        'Winthrop Eagles': 'WINTH',
        'Wisconsin Badgers': 'WISC',
        'Wofford Terriers': 'WOFF',
        'Wyoming Cowboys': 'WYOM',
        'Xavier Musketeers': 'XAVER',
        'Yale Bulldogs': 'YALE',

        #NBA teams 
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
        'Washington Wizards': 'Wizards'
    }
    return team_map.get(full_team_name, full_team_name)

def convert_sport_key(sport_key):
    sport_mapping = {
        'baseball_mlb': 'MLB',
        'basketball_nba': 'NBA',
        'americanfootball_nfl': 'NFL',
        'americanfootball_nfl_preseason': 'NFL',
        'icehockey_nhl': 'NHL',
        'americanfootball_ncaaf': 'NCAAFB',
        'basketball_ncaab': 'NCAABB',
        'soccer_epl': 'EPL'
        # Add other mappings as needed
    }
    return sport_mapping.get(sport_key, sport_key)

def convert_roto_team_names(team_name):
    team_map = {
       # MLB Teams
        'Arizona Diamondbacks': 'ARI',
        'Atlanta Braves': 'ATL',
        'Baltimore Orioles': 'BAL',
        'Boston Red Sox': 'BOS',
        'Chicago Cubs': 'CHC',
        'Chicago White Sox': 'CWS',
        'Cincinnati Reds': 'CIN',
        'Cleveland Guardians': 'CLE',
        'Colorado Rockies': 'COL',
        'Detroit Tigers': 'DET',
        'Houston Astros': 'HOU',
        'Kansas City Royals': 'KC',
        'Los Angeles Angels': 'LAA',
        'Los Angeles Dodgers': 'LAD',
        'Miami Marlins': 'MIA',
        'Milwaukee Brewers': 'MIL',
        'Minnesota Twins': 'MIN',
        'New York Mets': 'NYM',
        'New York Yankees': 'NYY',
        'Oakland Athletics': 'ATH',
        'Philadelphia Phillies': 'PHI',
        'Pittsburgh Pirates': 'PIT',
        'San Diego Padres': 'SD',
        'San Francisco Giants': 'SF',
        'Seattle Mariners': 'SEA',
        'St. Louis Cardinals': 'STL',
        'Tampa Bay Rays': 'TB',
        'Texas Rangers': 'TEX',
        'Toronto Blue Jays': 'TOR',
        'Washington Nationals': 'WSH',
    }
    return team_map.get(team_name, team_name)