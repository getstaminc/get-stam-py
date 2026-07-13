"""Shared team-slug utilities for the 6 sports with team-page infrastructure
(nba, nfl, mlb, nhl, ncaaf, ncaab). Mirrors getstam-react/src/utils/teamSlugUtils.ts.

Lives outside app.py so it can be imported by both app.py and API route/service
modules without creating a circular import (app.py imports blueprints from
api/routes/*, so those modules can't import back from app.py).
"""
import re

# oddsApiNames for each sport — mirrors teamSlugUtils.ts
SPORT_TEAMS = {
    'nba': [
        'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets',
        'Chicago Bulls', 'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets',
        'Detroit Pistons', 'Golden State Warriors', 'Houston Rockets', 'Indiana Pacers',
        'Los Angeles Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies', 'Miami Heat',
        'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans', 'New York Knicks',
        'Oklahoma City Thunder', 'Orlando Magic', 'Philadelphia 76ers', 'Phoenix Suns',
        'Portland Trail Blazers', 'Sacramento Kings', 'San Antonio Spurs', 'Toronto Raptors',
        'Utah Jazz', 'Washington Wizards',
    ],
    'nfl': [
        'Arizona Cardinals', 'Atlanta Falcons', 'Baltimore Ravens', 'Buffalo Bills',
        'Carolina Panthers', 'Chicago Bears', 'Cincinnati Bengals', 'Cleveland Browns',
        'Dallas Cowboys', 'Denver Broncos', 'Detroit Lions', 'Green Bay Packers',
        'Houston Texans', 'Indianapolis Colts', 'Jacksonville Jaguars', 'Kansas City Chiefs',
        'Las Vegas Raiders', 'Los Angeles Chargers', 'Los Angeles Rams', 'Miami Dolphins',
        'Minnesota Vikings', 'New England Patriots', 'New Orleans Saints', 'New York Giants',
        'New York Jets', 'Philadelphia Eagles', 'Pittsburgh Steelers', 'San Francisco 49ers',
        'Seattle Seahawks', 'Tampa Bay Buccaneers', 'Tennessee Titans', 'Washington Commanders',
    ],
    'mlb': [
        'Arizona Diamondbacks', 'Atlanta Braves', 'Baltimore Orioles', 'Boston Red Sox',
        'Chicago Cubs', 'Chicago White Sox', 'Cincinnati Reds', 'Cleveland Guardians',
        'Colorado Rockies', 'Detroit Tigers', 'Houston Astros', 'Kansas City Royals',
        'Los Angeles Angels', 'Los Angeles Dodgers', 'Miami Marlins', 'Milwaukee Brewers',
        'Minnesota Twins', 'New York Mets', 'New York Yankees', 'Athletics',
        'Philadelphia Phillies', 'Pittsburgh Pirates', 'San Diego Padres', 'San Francisco Giants',
        'Seattle Mariners', 'St. Louis Cardinals', 'Tampa Bay Rays', 'Texas Rangers',
        'Toronto Blue Jays', 'Washington Nationals',
    ],
    'nhl': [
        'Anaheim Ducks', 'Arizona Coyotes', 'Boston Bruins', 'Buffalo Sabres',
        'Calgary Flames', 'Carolina Hurricanes', 'Chicago Blackhawks', 'Colorado Avalanche',
        'Columbus Blue Jackets', 'Dallas Stars', 'Detroit Red Wings', 'Edmonton Oilers',
        'Florida Panthers', 'Los Angeles Kings', 'Minnesota Wild', 'Montréal Canadiens',
        'Nashville Predators', 'New Jersey Devils', 'New York Islanders', 'New York Rangers',
        'Ottawa Senators', 'Philadelphia Flyers', 'Pittsburgh Penguins', 'San Jose Sharks',
        'Seattle Kraken', 'St Louis Blues', 'Tampa Bay Lightning', 'Toronto Maple Leafs',
        'Utah Mammoth', 'Vancouver Canucks', 'Vegas Golden Knights', 'Washington Capitals',
        'Winnipeg Jets',
    ],
    'ncaaf': [
        'Alabama Crimson Tide', 'Appalachian State Mountaineers', 'Arizona Wildcats',
        'Arizona State Sun Devils', 'Arkansas Razorbacks', 'Auburn Tigers', 'Baylor Bears',
        'Boise State Broncos', 'Boston College Eagles', 'BYU Cougars', 'California Golden Bears',
        'Cincinnati Bearcats', 'Clemson Tigers', 'Colorado Buffaloes', 'Florida Gators',
        'Florida State Seminoles', 'Fresno State Bulldogs', 'Georgia Bulldogs',
        'Georgia Tech Yellow Jackets', 'Houston Cougars', 'Illinois Fighting Illini',
        'Indiana Hoosiers', 'Iowa Hawkeyes', 'Iowa State Cyclones', 'Kansas Jayhawks',
        'Kansas State Wildcats', 'Kentucky Wildcats', 'Louisiana Ragin\' Cajuns', 'LSU Tigers',
        'Louisville Cardinals', 'Maryland Terrapins', 'Memphis Tigers', 'Miami Hurricanes',
        'Michigan Wolverines', 'Michigan State Spartans', 'Minnesota Golden Gophers',
        'Mississippi State Bulldogs', 'Missouri Tigers', 'NC State Wolfpack', 'Nebraska Cornhuskers',
        'Nevada Wolf Pack', 'North Carolina Tar Heels', 'Northwestern Wildcats',
        'Notre Dame Fighting Irish', 'Ohio State Buckeyes', 'Oklahoma Sooners',
        'Oklahoma State Cowboys', 'Ole Miss Rebels', 'Oregon Ducks', 'Oregon State Beavers',
        'Penn State Nittany Lions', 'Pittsburgh Panthers', 'Purdue Boilermakers',
        'Rutgers Scarlet Knights', 'San Diego State Aztecs', 'SMU Mustangs',
        'South Carolina Gamecocks', 'Stanford Cardinal', 'Syracuse Orange', 'TCU Horned Frogs',
        'Tennessee Volunteers', 'Texas Longhorns', 'Texas A&M Aggies', 'Texas Tech Red Raiders',
        'Toledo Rockets', 'Tulane Green Wave', 'UCF Knights', 'UCLA Bruins', 'UNLV Rebels',
        'USC Trojans', 'Utah Utes', 'Utah State Aggies', 'Vanderbilt Commodores',
        'Virginia Cavaliers', 'Virginia Tech Hokies', 'Wake Forest Demon Deacons',
        'Washington Huskies', 'Washington State Cougars', 'West Virginia Mountaineers',
        'Wisconsin Badgers', 'Wyoming Cowboys',
    ],
    'ncaab': [
        'Alabama Crimson Tide', 'Arizona Wildcats', 'Arizona State Sun Devils',
        'Arkansas Razorbacks', 'Auburn Tigers', 'Baylor Bears', 'BYU Cougars',
        'California Golden Bears', 'Cincinnati Bearcats', 'Clemson Tigers', 'Colorado Buffaloes',
        'Colorado State Rams', 'UConn Huskies', 'Creighton Bluejays', 'Dayton Flyers',
        'Duke Blue Devils', 'Florida Gators', 'Florida State Seminoles', 'Gonzaga Bulldogs',
        'Georgia Bulldogs', 'Houston Cougars', 'Illinois Fighting Illini', 'Indiana Hoosiers',
        'Iowa Hawkeyes', 'Iowa State Cyclones', 'Kansas Jayhawks', 'Kansas State Wildcats',
        'Kentucky Wildcats', 'LSU Tigers', 'Maryland Terrapins', 'Memphis Tigers',
        'Michigan Wolverines', 'Michigan State Spartans', 'Missouri Tigers', 'Nebraska Cornhuskers',
        'North Carolina Tar Heels', 'NC State Wolfpack', 'Notre Dame Fighting Irish',
        'Ohio State Buckeyes', 'Oklahoma Sooners', 'Oklahoma State Cowboys', 'Ole Miss Rebels',
        'Oregon Ducks', 'Oregon State Beavers', 'Penn State Nittany Lions', 'Pittsburgh Panthers',
        'Purdue Boilermakers', 'Rutgers Scarlet Knights', 'San Diego State Aztecs',
        'SMU Mustangs', 'South Carolina Gamecocks', "St. John's Red Storm", 'Stanford Cardinal',
        'Syracuse Orange', 'TCU Horned Frogs', 'Tennessee Volunteers', 'Texas Longhorns',
        'Texas A&M Aggies', 'Texas Tech Red Raiders', 'UCLA Bruins', 'UNLV Rebels',
        'USC Trojans', 'Utah Utes', 'Utah State Aggies', 'Vanderbilt Commodores', 'VCU Rams',
        'Villanova Wildcats', 'Virginia Cavaliers', 'Virginia Tech Hokies',
        'Wake Forest Demon Deacons', 'Washington Huskies', 'West Virginia Mountaineers',
        'Wisconsin Badgers', 'Xavier Musketeers',
    ],
}


def team_slug(name):
    return re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))


def resolve_team_slug(sport, slug):
    """Given a sport key (nba/nfl/mlb/nhl/ncaaf/ncaab) and a team slug, return the
    full odds-api-style team name, or None if not found."""
    for name in SPORT_TEAMS.get(sport, []):
        if team_slug(name) == slug:
            return name
    return None
