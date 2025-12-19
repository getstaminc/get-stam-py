from flask import Flask, jsonify, Blueprint, send_from_directory
from datetime import datetime
import pytz

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

#Route to clear the cache
@app.route('/clear-cache')
def clear_cache():
    cache.clear()
    logging.info("Cache cleared")
    return "Cache cleared", 200

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
    # Serve index.html from the build root (not static)
    return send_from_directory('getstam-react/build', 'index.html')

if __name__ == '__main__':
    # Start the Flask application
    app.run(port=port)

