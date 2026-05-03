from flask import Flask, jsonify, Blueprint, send_from_directory, make_response
from datetime import datetime
import pytz
import re

from cache import cache, init_cache
import logging
import os
from dotenv import load_dotenv
from api.routes.games import games_bp
from api.routes.odds import odds_bp
from api.routes.rankings import rankings_bp
# Historical data routes
from api.routes.historical.nhl_games import nhl_historical_bp
from api.routes.historical.mlb_games import mlb_historical_bp
from api.routes.historical.soccer_games import soccer_historical_bp
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
from api.routes.mlb_pitchers import mlb_pitchers_bp
from api.routes.internal.mlb_mismatch import mlb_mismatch_bp
from api.routes.mlb_player_props import mlb_props_bp
from flask_cors import CORS

load_dotenv()  # Load environment variables from .env file

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
app.register_blueprint(mlb_pitchers_bp)
app.register_blueprint(mlb_mismatch_bp)
app.register_blueprint(mlb_props_bp)

_SPORT_DISPLAY = {
    'nfl': 'NFL', 'mlb': 'MLB', 'nba': 'NBA', 'nhl': 'NHL',
    'ncaaf': 'NCAAF', 'ncaab': 'NCAAB',
    'epl': 'EPL', 'laliga': 'La Liga', 'bundesliga': 'Bundesliga',
    'ligue1': 'Ligue 1', 'seriea': 'Serie A',
}

_STATIC_PAGE_META = {
    'about': ('About GetSTAM', 'Learn about GetSTAM and our sports analytics platform.'),
    'contact': ('Contact Us | GetSTAM', 'Get in touch with the GetSTAM team.'),
    'betting-guide': ('Betting Guide | GetSTAM', 'Learn how to read betting odds and use trends to your advantage.'),
    'privacy-policy': ('Privacy Policy | GetSTAM', 'GetSTAM privacy policy.'),
    'feature-requests': ('Feature Requests | GetSTAM', 'Request new features for GetSTAM.'),
}

def _get_page_meta(path):
    """Return (title, description) for a given URL path."""
    parts = [p for p in path.strip('/').split('/') if p]

    if not parts:
        return 'GetSTAM', 'Get stats that actually matter for all sports'

    slug = parts[0]

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
                f'{sport_name} Betting Trends | GetSTAM',
                f'{sport_name} ATS trends, over/under records, and historical betting patterns to find today\'s best matchups.',
            )
        return (
            f'{sport_name} Games & Odds | GetSTAM',
            f"Today's {sport_name} odds, point spreads, over/under lines, and ATS records for every matchup.",
        )

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
    ]

    urls = []
    for sport, priority in daily_sports:
        urls.append(f'  <url><loc>https://www.getstam.com/{sport}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>{priority}</priority></url>')
    for sport, priority in daily_trends:
        urls.append(f'  <url><loc>https://www.getstam.com/{sport}/trends</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>{priority}</priority></url>')
    for loc, changefreq, priority, lastmod in static_pages:
        urls.append(f'  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>')

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

