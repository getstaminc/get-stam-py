# utils.py

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
        'St Louis Cardinals': 'Cardinals',
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
        'San Francisco 49ers': '49ers',
        'Seattle Seahawks': 'Seahawks',
        'Tampa Bay Buccaneers': 'Buccaneers',
        'Tennessee Titans': 'Titans',
        'Washington Commanders': 'Commanders'
    }
    return team_map.get(full_team_name, full_team_name)

def convert_sport_key(sport_key):
    sport_mapping = {
        'baseball_mlb': 'MLB',
        'basketball_nba': 'NBA',
        'americanfootball_nfl': 'NFL',
        'americanfootball_nfl_preseason': 'NFL',
        'icehockey_nhl': 'NHL',
        'americanfootball_ncaaf': 'NCAAFB'
        # Add other mappings as needed
    }
    return sport_mapping.get(sport_key, sport_key)

