import os
from dotenv import load_dotenv
load_dotenv(override=True)  # Must run before any other imports that read env vars

from flask import Flask, jsonify, Blueprint, send_from_directory, make_response
from datetime import datetime
import pytz
import re

from cache import cache, init_cache
import logging
from api.routes.games import games_bp
from api.routes.odds import odds_bp
from api.routes.rankings import rankings_bp
# Historical data routes
from api.routes.historical.nhl_games import nhl_historical_bp
from api.routes.historical.mlb_games import mlb_historical_bp
from api.routes.historical.soccer_games import soccer_historical_bp
from api.routes.historical.worldcup_games import worldcup_historical_bp
from api.routes.historical.nfl_games import nfl_historical_bp
from api.routes.historical.ncaab_games import ncaab_historical_bp
from api.routes.historical.ncaaf_games import ncaaf_historical_bp
from api.routes.historical.nfl_trends import nfl_trends_bp
from api.routes.historical.mlb_trends import mlb_trends_bp
from api.routes.historical.ncaaf_trends import ncaaf_trends_bp
from api.routes.historical.soccer_trends import soccer_trends_bp
from api.routes.historical.nhl_trends import nhl_trends_bp
from api.routes.historical.nba_games import nba_historical_bp
from api.routes.historical.nba_trends import nba_trends_bp
from api.routes.historical.ncaab_trends import ncaab_trends_bp
from api.routes.historical.meta import historical_meta_bp
from api.routes.mlb_pitchers import mlb_pitchers_bp
from api.routes.internal.mlb_mismatch import mlb_mismatch_bp
from api.routes.mlb_player_props import mlb_props_bp
from api.routes.webhooks.youtube_webhook import youtube_webhook_bp
from api.routes.blog import blog_bp
from api.routes.admin_blog import admin_blog_bp
from api.routes.subscribers import subscribers_bp
from flask_cors import CORS


# Configure Flask app to serve React build
app = Flask(__name__, static_folder='getstam-react/build/static', static_url_path='/static')

port = 5000

# Specify allowed origins
CORS(app, origins=[
    "http://localhost:3000",
    "http://127.0.0.1:5000",
    "https://www.getstam.com"
])

# Configure logging to write to a file
if not os.path.exists('logs'):
    os.makedirs('logs')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('logs/app.log')
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Define the Eastern timezone
eastern_tz = pytz.timezone('US/Eastern')

# Determine if caching should be enabled based on the environment
cache = init_cache(app)

app.register_blueprint(games_bp)
app.register_blueprint(odds_bp)
app.register_blueprint(rankings_bp)
# Register historical data blueprints
app.register_blueprint(mlb_historical_bp)
app.register_blueprint(soccer_historical_bp)
app.register_blueprint(worldcup_historical_bp)
app.register_blueprint(nfl_historical_bp)
app.register_blueprint(nba_historical_bp)
app.register_blueprint(ncaab_historical_bp)
app.register_blueprint(ncaaf_historical_bp)
app.register_blueprint(nhl_historical_bp)
app.register_blueprint(nfl_trends_bp)
app.register_blueprint(mlb_trends_bp)
app.register_blueprint(ncaaf_trends_bp)
app.register_blueprint(soccer_trends_bp)
app.register_blueprint(nba_trends_bp)
app.register_blueprint(ncaab_trends_bp)
app.register_blueprint(nhl_trends_bp)
app.register_blueprint(historical_meta_bp)
app.register_blueprint(mlb_pitchers_bp)
app.register_blueprint(mlb_mismatch_bp)
app.register_blueprint(mlb_props_bp)
app.register_blueprint(youtube_webhook_bp)
app.register_blueprint(blog_bp)
app.register_blueprint(admin_blog_bp)
app.register_blueprint(subscribers_bp)

_SPORT_DISPLAY = {
    'nfl': 'NFL', 'mlb': 'MLB', 'nba': 'NBA', 'nhl': 'NHL',
    'ncaaf': 'NCAAF', 'ncaab': 'NCAAB',
    'epl': 'EPL', 'laliga': 'La Liga', 'bundesliga': 'Bundesliga',
    'ligue1': 'Ligue 1', 'seriea': 'Serie A',
}

def _team_slug(name):
    return re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))

# oddsApiNames for each sport — mirrors teamSlugUtils.ts
_SPORT_TEAMS = {
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
        'Minnesota Twins', 'New York Mets', 'New York Yankees', 'Oakland Athletics',
        'Philadelphia Phillies', 'Pittsburgh Pirates', 'San Diego Padres', 'San Francisco Giants',
        'Seattle Mariners', 'St. Louis Cardinals', 'Tampa Bay Rays', 'Texas Rangers',
        'Toronto Blue Jays', 'Washington Nationals',
    ],
    'nhl': [
        'Anaheim Ducks', 'Arizona Coyotes', 'Boston Bruins', 'Buffalo Sabres',
        'Calgary Flames', 'Carolina Hurricanes', 'Chicago Blackhawks', 'Colorado Avalanche',
        'Columbus Blue Jackets', 'Dallas Stars', 'Detroit Red Wings', 'Edmonton Oilers',
        'Florida Panthers', 'Los Angeles Kings', 'Minnesota Wild', 'Montr\u00e9al Canadiens',
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

_STATIC_PAGE_META = {
    'about': ('About GetSTAM', 'Learn about GetSTAM and our sports analytics platform.'),
    'contact': ('Contact Us | GetSTAM', 'Get in touch with the GetSTAM team.'),
    'betting-guide': ('Betting Guide | GetSTAM', 'Learn how to read betting odds and use trends to your advantage.'),
    'privacy-policy': ('Privacy Policy | GetSTAM', 'GetSTAM privacy policy.'),
    'feature-requests': ('Feature Requests | GetSTAM', 'Request new features for GetSTAM.'),
    'blog': ('Blog | GetSTAM', 'Sports betting analysis and tips.'),
}

def _get_page_meta(path):
    """Return (title, description) for a given URL path."""
    parts = [p for p in path.strip('/').split('/') if p]

    if not parts:
        return 'GetSTAM', 'Get stats that actually matter for all sports'

    slug = parts[0]

    if slug == 'team' and len(parts) >= 3:
        sport_display = _SPORT_DISPLAY.get(parts[1], parts[1].upper())
        team_name = parts[2].replace('-', ' ').title()
        return (
            f'{team_name} {sport_display} Odds & Stats | GetSTAM',
            f'{team_name} betting odds, ATS records, and recent game results.',
        )

    if slug == 'game-details' and len(parts) >= 2:
        sport_name = _SPORT_DISPLAY.get(parts[1], parts[1].upper())
        return (
            f'{sport_name} Game Details | GetSTAM',
            f'Betting odds, trends, and head-to-head stats for this {sport_name} matchup.',
        )

    sport_name = _SPORT_DISPLAY.get(slug)
    if sport_name:
        if len(parts) >= 2 and parts[1] == 'trends':
            return (
                f'{sport_name} Trends | GetSTAM',
                f'{sport_name} ATS trends, over/under records, and historical betting patterns to find today\'s best matchups.',
            )
        return (
            f'{sport_name} Games & Odds | GetSTAM',
            f"Today's {sport_name} odds, point spreads, over/under lines, and ATS records for every matchup.",
        )

    if slug == 'blog':
        if len(parts) >= 2:
            return (
                f'{parts[1].replace("-", " ").title()} | GetSTAM Blog',
                'Sports betting insights from GetSTAM.',
            )
        return _STATIC_PAGE_META['blog']

    if slug in _STATIC_PAGE_META:
        return _STATIC_PAGE_META[slug]

    return 'GetSTAM', 'Get stats that actually matter for all sports'


_index_html_content = None

def _get_index_html():
    global _index_html_content
    if _index_html_content is None:
        with open('getstam-react/build/index.html', 'r') as f:
            _index_html_content = f.read()
    return _index_html_content


def _inject_meta(html, title, description):
    html = re.sub(r'<title>[^<]*</title>', f'<title>{title}</title>', html)
    html = re.sub(
        r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
        f'<meta name="description" content="{description}" />',
        html,
    )
    return html


#Route to clear the cache
@app.route('/clear-cache')
def clear_cache():
    cache.clear()
    logging.info("Cache cleared")
    return "Cache cleared", 200

# Serve sitemap dynamically so daily pages always get today's lastmod
@app.route('/sitemap.xml')
def sitemap():
    today = datetime.now().strftime('%Y-%m-%d')

    daily_sports = [
        ('nba', '0.9'), ('mlb', '0.9'), ('nfl', '0.9'), ('nhl', '0.9'),
        ('ncaaf', '0.8'), ('ncaab', '0.8'), ('epl', '0.8'), ('laliga', '0.8'),
        ('bundesliga', '0.8'), ('ligue1', '0.8'), ('seriea', '0.8'),
    ]
    daily_trends = [
        ('nba', '0.8'), ('mlb', '0.8'), ('nfl', '0.8'), ('nhl', '0.8'),
        ('ncaaf', '0.7'), ('ncaab', '0.7'), ('epl', '0.7'), ('laliga', '0.7'),
        ('bundesliga', '0.7'), ('ligue1', '0.7'), ('seriea', '0.7'),
    ]
    static_pages = [
        ('https://www.getstam.com/about-us',      'monthly', '0.5', '2025-01-01'),
        ('https://www.getstam.com/betting-guide',  'monthly', '0.6', '2025-01-01'),
        ('https://www.getstam.com/contact-us',     'monthly', '0.4', '2025-01-01'),
        ('https://www.getstam.com/privacy-policy', 'yearly',  '0.3', '2025-01-01'),
        ('https://www.getstam.com/blog',           'weekly',  '0.7', today),
    ]

    team_page_priority = {'nba': '0.7', 'nfl': '0.7', 'mlb': '0.7', 'nhl': '0.7', 'ncaaf': '0.6', 'ncaab': '0.6'}

    urls = []
    for sport, priority in daily_sports:
        urls.append(f'  <url><loc>https://www.getstam.com/{sport}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>{priority}</priority></url>')
    for sport, priority in daily_trends:
        urls.append(f'  <url><loc>https://www.getstam.com/{sport}/trends</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>{priority}</priority></url>')
    for sport, teams in _SPORT_TEAMS.items():
        priority = team_page_priority.get(sport, '0.6')
        for team in teams:
            slug = _team_slug(team)
            urls.append(f'  <url><loc>https://www.getstam.com/team/{sport}/{slug}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>{priority}</priority></url>')
    for loc, changefreq, priority, lastmod in static_pages:
        urls.append(f'  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>')

    # Blog post pages
    try:
        from api.services.blog_service import BlogService as _BlogService
        post_slugs, _ = _BlogService.get_published_slugs()
        for post_slug in post_slugs:
            urls.append(f'  <url><loc>https://www.getstam.com/blog/{post_slug}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>')
    except Exception:
        pass

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '\n'.join(urls)
    xml += '\n</urlset>'

    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    return response


# Serve Firebase messaging service worker from root
@app.route('/firebase-messaging-sw.js')
def firebase_sw():
    return send_from_directory('.', 'firebase-messaging-sw.js')

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Serve favicon and other root files from build directory
    if path in ['favicon.ico', 'logo192.png', 'logo512.png', 'manifest.json', 'robots.txt']:
        build_file_path = os.path.join('getstam-react/build', path)
        if os.path.exists(build_file_path) and os.path.isfile(build_file_path):
            return send_from_directory('getstam-react/build', path)
    
    # Try to serve static files from the static folder
    static_file_path = os.path.join(app.static_folder, path)
    if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
        return send_from_directory(app.static_folder, path)
    # Serve index.html with injected meta tags for crawler-friendly SSR
    title, description = _get_page_meta(path)
    html = _inject_meta(_get_index_html(), title, description)
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html'
    return response

if __name__ == '__main__':
    # Start the Flask application
    app.run(port=port)

