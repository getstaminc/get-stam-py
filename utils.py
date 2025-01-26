# utils.py

# import sys
# import os

# # Add the directory containing sdql_queries.py to the Python path
# sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import pytz
from datetime import datetime
from shared_utils import convert_to_eastern, convert_team_name, convert_sport_key
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent

# def convert_team_name(full_team_name):
#     team_map = {
#         # MLB Teams
#         'Arizona Diamondbacks': 'Diamondbacks',
#         'Atlanta Braves': 'Braves',
#         'Baltimore Orioles': 'Orioles',
#         'Boston Red Sox': 'Red Sox',
#         'Chicago Cubs': 'Cubs',
#         'Chicago White Sox': 'White Sox',
#         'Cincinnati Reds': 'Reds',
#         'Cleveland Guardians': 'Guardians',
#         'Colorado Rockies': 'Rockies',
#         'Detroit Tigers': 'Tigers',
#         'Houston Astros': 'Astros',
#         'Kansas City Royals': 'Royals',
#         'Los Angeles Angels': 'Angels',
#         'Los Angeles Dodgers': 'Dodgers',
#         'Miami Marlins': 'Marlins',
#         'Milwaukee Brewers': 'Brewers',
#         'Minnesota Twins': 'Twins',
#         'New York Mets': 'Mets',
#         'New York Yankees': 'Yankees',
#         'Oakland Athletics': 'Athletics',
#         'Philadelphia Phillies': 'Phillies',
#         'Pittsburgh Pirates': 'Pirates',
#         'San Diego Padres': 'Padres',
#         'San Francisco Giants': 'Giants',
#         'Seattle Mariners': 'Mariners',
#         'St Louis Cardinals': 'Cardinals',
#         'Tampa Bay Rays': 'Rays',
#         'Texas Rangers': 'Rangers',
#         'Toronto Blue Jays': 'Blue Jays',
#         'Washington Nationals': 'Nationals',
        
#         # NFL Teams
#         'Arizona Cardinals': 'Cardinals',
#         'Atlanta Falcons': 'Falcons',
#         'Baltimore Ravens': 'Ravens',
#         'Buffalo Bills': 'Bills',
#         'Carolina Panthers': 'Panthers',
#         'Chicago Bears': 'Bears',
#         'Cincinnati Bengals': 'Bengals',
#         'Cleveland Browns': 'Browns',
#         'Dallas Cowboys': 'Cowboys',
#         'Denver Broncos': 'Broncos',
#         'Detroit Lions': 'Lions',
#         'Green Bay Packers': 'Packers',
#         'Houston Texans': 'Texans',
#         'Indianapolis Colts': 'Colts',
#         'Jacksonville Jaguars': 'Jaguars',
#         'Kansas City Chiefs': 'Chiefs',
#         'Las Vegas Raiders': 'Raiders',
#         'Los Angeles Chargers': 'Chargers',
#         'Los Angeles Rams': 'Rams',
#         'Miami Dolphins': 'Dolphins',
#         'Minnesota Vikings': 'Vikings',
#         'New England Patriots': 'Patriots',
#         'New Orleans Saints': 'Saints',
#         'New York Giants': 'Giants',
#         'New York Jets': 'Jets',
#         'Philadelphia Eagles': 'Eagles',
#         'Pittsburgh Steelers': 'Steelers',
#         'San Francisco 49ers': 'Fortyniners',
#         'Seattle Seahawks': 'Seahawks',
#         'Tampa Bay Buccaneers': 'Buccaneers',
#         'Tennessee Titans': 'Titans',
#         'Washington Commanders': 'Commanders',

#         #NHL
#         'Anaheim Ducks': 'Ducks',
#         'Arizona Coyotes': 'Coyotes',
#         'Boston Bruins': 'Bruins',
#         'Buffalo Sabres': 'Sabres',
#         'Calgary Flames': 'Flames',
#         'Carolina Hurricanes': 'Hurricanes',
#         'Chicago Blackhawks': 'Blackhawks',
#         'Colorado Avalanche': 'Avalanche',
#         'Columbus Blue Jackets': 'Blue Jackets',
#         'Dallas Stars': 'Stars',
#         'Detroit Red Wings': 'Red Wings',
#         'Edmonton Oilers': 'Oilers',
#         'Florida Panthers': 'Panthers',
#         'Los Angeles Kings': 'Kings',
#         'Minnesota Wild': 'Wild',
#         'Montréal Canadiens': 'Canadiens',
#         'Nashville Predators': 'Predators',
#         'New Jersey Devils': 'Devils',
#         'New York Islanders': 'Islanders',
#         'New York Rangers': 'Rangers',
#         'Ottawa Senators': 'Senators',
#         'Philadelphia Flyers': 'Flyers',
#         'Pittsburgh Penguins': 'Penguins',
#         'San Jose Sharks': 'Sharks',
#         'Seattle Kraken': 'Kraken',
#         'St. Louis Blues': 'Blues',
#         'Tampa Bay Lightning': 'Lightning',
#         'Toronto Maple Leafs': 'Maple Leafs',
#         'Utah Hockey Club': 'Hockey Club',
#         'Vancouver Canucks': 'Canucks',
#         'Vegas Golden Knights': 'Golden Knights',
#         'Washington Capitals': 'Capitals',
#         'Winnipeg Jets': 'Jets',

#         #NCAA 
#         'Abilene Christian Wildcats': 'ABCH',
#         'Air Force Falcons': 'AIR',
#         'Arkansas-Pine Bluff Golden Lions': 'AKPB',
#         'Akron Zips': 'AKRON',
#         'Arkansas State Red Wolves': 'AKST',
#         'Alabama Crimson Tide': 'ALA',
#         'Alabama A&M Bulldogs': 'ALAM',
#         'Albany Great Danes': 'ALBS',  # There are two entries for Albany Great Danes
#         'Alcorn State Braves': 'ALCN',
#         'Appalachian State Mountaineers': 'APP',
#         'Arkansas Razorbacks': 'ARK',
#         'Army Black Knights': 'ARMY',
#         'Arizona Wildcats': 'ARZ',
#         'Auburn Tigers': 'AUB',
#         'Arizona State Sun Devils': 'AZST',
#         'Ball State Cardinals': 'BALL',
#         'Baylor Bears': 'BAY',
#         'Boston College Eagles': 'BCOL',
#         'Boise State Broncos': 'BOIS',
#         'Bowling Green Falcons': 'BOWL',
#         'Bryant Bulldogs': 'BRY',
#         'Bucknell Bison': 'BUCK',
#         'Buffalo Bulls': 'BUF',
#         'BYU Cougars': 'BYU',
#         'California Golden Bears': 'CAL',
#         'Campbell Camels': 'CAMP',
#         'Central Arkansas Bears': 'CARK',
#         'Central Connecticut Blue Devils': 'CCON',
#         'UC Davis Aggies': 'CDAV',
#         'UCF Knights': 'CFL',
#         'Charlotte 49ers': 'CHAR',
#         'Charleston Southern Buccaneers': 'CHSO',
#         'Cincinnati Bearcats': 'CIN',
#         'Clemson Tigers': 'CLEM',
#         'Colgate Raiders': 'CLG',
#         'Central Michigan Chippewas': 'CMCH',
#         'Colorado Buffaloes': 'COLO',
#         'Columbia Lions': 'COLU',
#         'Connecticut Huskies': 'CON',
#         'Bethune-Cookman Wildcats': 'COOK',
#         'Cornell Big Red': 'COR',
#         'Colorado State Rams': 'COST',
#         'Cal Poly Mustangs': 'CPOL',
#         'Sacramento State Hornets': 'CSAC',
#         'Coastal Carolina Chanticleers': 'CSTC',
#         'The Citadel Bulldogs': 'CTDL',
#         'Dartmouth Big Green': 'DART',
#         'Davidson Wildcats': 'DAV',
#         'Dayton Flyers': 'DAYT',
#         'Delaware Blue Hens': 'DEL',
#         'Drake Bulldogs': 'DRAKE',
#         'Delaware State Hornets': 'DSU',
#         'Duke Blue Devils': 'DUKE',
#         'Duquesne Dukes': 'DUQ',
#         'East Carolina Pirates': 'ECAR',
#         'Eastern Illinois Panthers': 'EIL',
#         'Eastern Kentucky Colonels': 'EKY',
#         'Elon Phoenix': 'ELON',
#         'Eastern Michigan Eagles': 'EMCH',
#         'East Tennessee State Buccaneers': 'ETSU',
#         'Eastern Washington Eagles': 'EWAS',
#         'Florida A&M Rattlers': 'FAM',
#         'Florida Atlantic Owls': 'FATL',
#         'Florida International Golden Panthers': 'FINT',
#         'Florida Gators': 'FLA',
#         'Florida State Seminoles': 'FLST',
#         'Fordham Rams': 'FORD',
#         'Fresno State Bulldogs': 'FRES',
#         'Furman Paladins': 'FUR',
#         'Gardner-Webb Bulldogs': 'GARD',
#         'Georgia State Panthers': 'GAST',
#         'Georgia Bulldogs': 'GEO',
#         'Grambling Tigers': 'GRAM',
#         'Georgia Southern Eagles': 'GSOU',
#         'Georgia Tech Yellow Jackets': 'GTCH',
#         'Georgetown Hoyas': 'GTWN',
#         'Hawaii Rainbow Warriors': 'HAW',
#         'Houston Baptist Huskies': 'HBU',
#         'Holy Cross Crusaders': 'HCR',
#         'Houston Cougars': 'HOU',
#         'Howard Bison': 'HOW',
#         'Harvard Crimson': 'HVD',
#         'Idaho Vandals': 'IDA',
#         'Idaho State Bengals': 'IDST',
#         'Illinois Fighting Illini': 'ILL',
#         'Illinois State Redbirds': 'ILST',
#         'Indiana Hoosiers': 'IND',
#         'Indiana State Sycamores': 'INST',
#         'Iowa Hawkeyes': 'IOWA',
#         'Incarnate Word Cardinals': 'IW',
#         'Iowa State Cyclones': 'IWST',
#         'Jackson State Tigers': 'JAST',
#         'James Madison Dukes': 'JMAD',
#         'Jacksonville State Gamecocks': 'JVST',
#         'Kansas Jayhawks': 'KAN',
#         'Kansas State Wildcats': 'KAST',
#         'Kennesaw State Owls': 'KENN',
#         'Kent State Golden Flashes': 'KEST',
#         'Kentucky Wildcats': 'KTKY',
#         'Lafayette Leopards': 'LAF',
#         'Lamar Cardinals': 'LAMA',
#         'Liberty Flames': 'LIB',
#         'Long Island University Sharks': 'LIU',
#         'Louisiana Ragin\' Cajuns': 'LLAF',
#         'UL Monroe Warhawks': 'LMON',
#         'Louisville Cardinals': 'LOU',
#         'LSU Tigers': 'LSU',
#         'Louisiana Tech Bulldogs': 'LTCH',
#         'Maine Black Bears': 'MAIN',
#         'Marist Red Foxes': 'MAR',
#         'Maryland Terrapins': 'MARY',
#         'UMass Minutemen': 'MAS',
#         'Michigan State Spartans': 'MCST',
#         'Memphis Tigers': 'MEM',
#         'Mercer Bears': 'MER',
#         'Miami Hurricanes': 'MIAF',
#         'Miami (OH) RedHawks': 'MIAO',
#         'Michigan Wolverines': 'MICH',
#         'Minnesota Golden Gophers': 'MIN',
#         'Ole Miss Rebels': 'MIS',
#         'Missouri Tigers': 'MIZ',
#         'McNeese Cowboys': 'MNEE',
#         'Monmouth Hawks': 'MONM',
#         'Montana State Bobcats': 'MONS',
#         'Montana Grizzlies': 'MONT',
#         'Morgan State Bears': 'MORG',
#         'Merrimack Warriors': 'MRR',
#         'Marshall Thundering Herd': 'MRSH',
#         'Mississippi State Bulldogs': 'MSST',
#         'Middle Tennessee Blue Raiders': 'MTEN',
#         'Murray State Racers': 'MUR',
#         'Mississippi Valley State Delta Devils': 'MVST',
#         'Missouri State Bears': 'MZST',
#         'North Alabama Lions': 'NALA',
#         'Navy Midshipmen': 'NAVY',
#         'Northern Arizona Lumberjacks': 'NAZ',
#         'North Carolina Tar Heels': 'NCAR',
#         'North Carolina A&T Aggies': 'NCAT',
#         'North Carolina Central Eagles': 'NCC',
#         'Northern Colorado Bears': 'NCOL',
#         'NC State Wolfpack': 'NCST',
#         'North Dakota State Bison': 'NDST',
#         'Nebraska Cornhuskers': 'NEB',
#         'Nevada Wolf Pack': 'NEV',
#         'Norfolk State Spartans': 'NFST',
#         'New Hampshire Wildcats': 'NHAM',
#         'Nicholls Colonels': 'NICH',
#         'Northern Illinois Huskies': 'NIL',
#         'Northern Iowa Panthers': 'NIWA',
#         'New Mexico State Aggies': 'NMST',
#         'New Mexico Lobos': 'NMX',
#         'Northwestern Wildcats': 'NORW',
#         'Northwestern State Demons': 'NOST',
#         'Notre Dame Fighting Irish': 'NOTD',
#         'North Texas Mean Green': 'NTX',
#         'Ohio State Buckeyes': 'OHST',
#         'Ohio Bobcats': 'OHU',
#         'Oklahoma Sooners': 'OKLA',
#         'Oklahoma State Cowboys': 'OKST',
#         'Old Dominion Monarchs': 'OLDD',
#         'Oregon Ducks': 'ORE',
#         'Oregon State Beavers': 'ORST',
#         'Austin Peay Governors': 'PEAY',
#         'Pennsylvania Quakers': 'PEN',
#         'Pittsburgh Panthers': 'PIT',
#         'Penn State Nittany Lions': 'PNST',
#         'Portland State Vikings': 'POST',
#         'Presbyterian College Blue Hose': 'PRES',
#         'Princeton Tigers': 'PRIN',
#         'Prairie View Panthers': 'PRVW',
#         'Purdue Boilermakers': 'PUR',
#         'Rice Owls': 'RICE',
#         'Richmond Spiders': 'RICH',
#         'Robert Morris Colonials': 'RMOR',
#         'Rutgers Scarlet Knights': 'RUT',
#         'Sacred Heart Pioneers': 'SACHT',
#         'South Alabama Jaguars': 'SALA',
#         'Samford Bulldogs': 'SAMF',
#         'South Carolina Gamecocks': 'SCAR',
#         'South Carolina State Bulldogs': 'SCST',
#         'South Dakota State Jackrabbits': 'SDKS',
#         'San Diego State Aztecs': 'SDST',
#         'Southeastern Louisiana Lions': 'SELA',
#         'Southeast Missouri State Red Hawks': 'SEMST',
#         'Stephen F. Austin Lumberjacks': 'SFAN',
#         'South Florida Bulls': 'SFL',
#         'St Francis (PA) Red Flash': 'SFPA',
#         'Sam Houston State Bearkats': 'SHST',
#         'Southern Illinois Salukis': 'SIL',
#         'San Jose State Spartans': 'SJST',
#         'Southern Mississippi Golden Eagles': 'SMIS',
#         'SMU Mustangs': 'SMU',
#         'Southern Jaguars': 'SOU',
#         'Stanford Cardinal': 'STAN',
#         'Stony Brook Seawolves': 'STBR',
#         'Stetson Hatters': 'STET',
#         'Southern Utah Thunderbirds': 'SUT',
#         'Syracuse Orange': 'SYR',
#         'Tarleton State': 'TARL',
#         'Chattanooga Mocs': 'TCHA',
#         'TCU Horned Frogs': 'TCU',
#         'Temple Owls': 'TEM',
#         'Tennessee Volunteers': 'TEN',
#         'Tennessee Tech Golden Eagles': 'TENT',
#         'Texas Longhorns': 'TEX',
#         'Tulane Green Wave': 'TLN',
#         'Tulsa Golden Hurricane': 'TLS',
#         'UT Martin Skyhawks': 'TMAR',
#         'Tennessee State Tigers': 'TNST',
#         'Toledo Rockets': 'TOL',
#         'Troy Trojans': 'TROY',
#         'Towson Tigers': 'TWSN',
#         'Texas A&M Aggies': 'TXAM',
#         'Texas A&M-Commerce Lions': 'TXAMC',
#         'Texas Southern Tigers': 'TXSO',
#         'Texas State Bobcats': 'TXST',
#         'Texas Tech Red Raiders': 'TXT',
#         'UAB Blazers': 'UAB',
#         'UCLA Bruins': 'UCLA',
#         'North Dakota Fighting Hawks': 'UND',
#         'UNLV Rebels': 'UNLV',
#         'Rhode Island Rams': 'URI',
#         'USC Trojans': 'USC',
#         'South Dakota Coyotes': 'USD',
#         'Utah Utes': 'UTAH',
#         'Utah Tech Trailblazers': 'UTAHTCH',
#         'UTEP Miners': 'UTEP',
#         'UT San Antonio Roadrunners': 'UTSA',
#         'Utah State Aggies': 'UTST',
#         'Valparaiso Beacons': 'VAL',
#         'Vanderbilt Commodores': 'VAN',
#         'Villanova Wildcats': 'VIL',
#         'Virginia Cavaliers': 'VIR',
#         'VMI Keydets': 'VMI',
#         'Virginia Tech Hokies': 'VTCH',
#         'Wagner Seahawks': 'WAG',
#         'Wake Forest Demon Deacons': 'WAKE',
#         'William & Mary Tribe': 'WAM',
#         'Washington Huskies': 'WAS',
#         'Washington State Cougars': 'WAST',
#         'Western Carolina Catamounts': 'WCAR',
#         'Weber State Wildcats': 'WEB',
#         'Western Illinois Leathernecks': 'WIL',
#         'Wisconsin Badgers': 'WIS',
#         'Western Kentucky Hilltoppers': 'WKY',
#         'Western Michigan Broncos': 'WMCH',
#         'Wofford Terriers': 'WOF',
#         'West Virginia Mountaineers': 'WVA',
#         'Wyoming Cowboys': 'WYO',
#         'Yale Bulldogs': 'YALE',
#         'Youngstown State Penguins': 'YST', 

#         #NBA teams 
#         'Atlanta Hawks': 'Hawks',
#         'Boston Celtics': 'Celtics',
#         'Brooklyn Nets': 'Nets',
#         'Charlotte Hornets': 'Hornets',
#         'Chicago Bulls': 'Bulls',
#         'Cleveland Cavaliers': 'Cavaliers',
#         'Dallas Mavericks': 'Mavericks',
#         'Denver Nuggets': 'Nuggets',
#         'Detroit Pistons': 'Pistons',
#         'Golden State Warriors': 'Warriors',
#         'Houston Rockets': 'Rockets',
#         'Indiana Pacers': 'Pacers',
#         'Los Angeles Clippers': 'Clippers',
#         'Los Angeles Lakers': 'Lakers',
#         'Memphis Grizzlies': 'Grizzlies',
#         'Miami Heat': 'Heat',
#         'Milwaukee Bucks': 'Bucks',
#         'Minnesota Timberwolves': 'Timberwolves',
#         'New Orleans Pelicans': 'Pelicans',
#         'New York Knicks': 'Knicks',
#         'Oklahoma City Thunder': 'Thunder',
#         'Orlando Magic': 'Magic',
#         'Philadelphia 76ers': 'Seventysixers',
#         'Phoenix Suns': 'Suns',
#         'Portland Trail Blazers': 'Trailblazers',
#         'Sacramento Kings': 'Kings',
#         'San Antonio Spurs': 'Spurs',
#         'Toronto Raptors': 'Raptors',
#         'Utah Jazz': 'Jazz',
#         'Washington Wizards': 'Wizards'
#     }
#     return team_map.get(full_team_name, full_team_name)

# def convert_sport_key(sport_key):
#     sport_mapping = {
#         'baseball_mlb': 'MLB',
#         'basketball_nba': 'NBA',
#         'americanfootball_nfl': 'NFL',
#         'americanfootball_nfl_preseason': 'NFL',
#         'icehockey_nhl': 'NHL',
#         'americanfootball_ncaaf': 'NCAAFB',
#         'basketball_ncaab': 'NCAABB'
#         # Add other mappings as needed
#     }
#     return sport_mapping.get(sport_key, sport_key)


def mlb_totals(runs, opponent_runs, total):
    return (runs + opponent_runs) > total

def other_totals(points, opponent_points, total):
            combined_score = points + opponent_points
            return combined_score < total

eastern_tz = pytz.timezone('US/Eastern')

def convert_to_eastern(utc_time):
    if utc_time is None:
        return None
    utc_time = utc_time.replace(tzinfo=pytz.utc)
    eastern_time = utc_time.astimezone(eastern_tz)
    return eastern_time

def check_for_trends(game, selected_date_start, sport_key):


    home_team_last_5 = get_last_5_games(game['homeTeam'], selected_date_start, sport_key) or []
    away_team_last_5 = get_last_5_games(game['awayTeam'], selected_date_start, sport_key) or []
    last_5_vs_opponent = get_last_5_games_vs_opponent(
        team=game['homeTeam'],
        opponent=game['awayTeam'],
        today_date=selected_date_start,
        sport_key=sport_key
    ) or []

    home_trend = detect_trends(home_team_last_5, sport_key)
    away_trend = detect_trends(away_team_last_5, sport_key)
    vs_opponent_trend = detect_trends(last_5_vs_opponent, sport_key)

    trend_detected = home_trend or away_trend or vs_opponent_trend

    return {
        'home_trend': home_trend,
        'away_trend': away_trend,
        'vs_opponent_trend': vs_opponent_trend,
        'trend_detected': trend_detected
    }

def detect_trends(games, sport_key):
    def is_winner(points, o_points):
        if points is None or o_points is None:
            return None
        return points > o_points

    def calculate_line_result(points, line, o_points):
        if points is None or line is None or o_points is None:
            return None, ''
        if points + line > o_points:
            return True, 'green-bg'
        elif points + line < o_points:
            return False, 'red-bg'
        else:
            return None, ''

    def other_totals(points, o_points, total):
        if points is None or o_points is None or total is None:
            return None, ''
        if points + o_points > total:
            return True, 'green-bg'
        elif points + o_points < total:
            return False, 'red-bg'
        else:
            return None, ''

    if sport_key == 'icehockey_nhl':
        points_key = 'goals'
    else:
        points_key = 'points'

    # Check for trends in the 'team' column
    team_colors = []
    for game in games:
        result = is_winner(game[points_key], game[f'o:{points_key}'])
        if result is not None:
            color = 'green-bg' if result else 'red-bg'
            team_colors.append(color)
    if team_colors.count('green-bg') == 5 or team_colors.count('red-bg') == 5:
        return True

    # Check for trends in the 'points' column
    points_colors = []
    for game in games:
        result = is_winner(game[points_key], game[f'o:{points_key}'])
        if result is not None:
            color = 'green-bg' if result else 'red-bg'
            points_colors.append(color)
    if points_colors.count('green-bg') == 5 or points_colors.count('red-bg') == 5:
        return True

    # Skip line trend check for NHL
    if sport_key != 'icehockey_nhl':
        # Check for trends in the 'line' column
        line_colors = []
        for game in games:
            result, color = calculate_line_result(game[points_key], game['line'], game[f'o:{points_key}'])
            if result is not None:
                line_colors.append(color)
        if line_colors.count('green-bg') == 5 or line_colors.count('red-bg') == 5:
            return True

    # Check for trends in the 'total' column
    total_colors = []
    for game in games:
        result, color = other_totals(game[points_key], game[f'o:{points_key}'], game['total'])
        if result is not None:
            total_colors.append(color)
    if total_colors.count('green-bg') == 5 or total_colors.count('red-bg') == 5:
        return True

    return False