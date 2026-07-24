import os
from dotenv import load_dotenv
load_dotenv(override=True)  # Must run before any other imports that read env vars

from flask import Flask, jsonify, Blueprint, send_from_directory, make_response
from datetime import datetime, timedelta
import pytz
import re
import html
import json

from cache import cache, init_cache
from api.services.blog_service import BlogService
from api.utils.team_slugs import team_slug as _team_slug, SPORT_TEAMS as _SPORT_TEAMS, resolve_team_slug
from api.services.game_service import GameService
from api.external_requests.odds_api import convert_sport_url_to_api_key
import logging
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
from api.routes.historical.mlb_player_trends import bp as mlb_player_trends_bp
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
app.register_blueprint(mlb_player_trends_bp)
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

BASE_URL = 'https://www.getstam.com'
DEFAULT_OG_IMAGE = f'{BASE_URL}/logo192.png'

_ORG_WEBSITE_JSON_LD = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "Organization", "name": "GetSTAM", "url": BASE_URL, "logo": f'{BASE_URL}/logo192.png'},
        {"@type": "WebSite", "name": "GetSTAM", "url": BASE_URL},
    ],
}

_STATIC_PAGE_META = {
    'about-us': ('About GetSTAM', 'Learn about GetSTAM and our sports analytics platform.'),
    'contact-us': ('Contact Us | GetSTAM', 'Get in touch with the GetSTAM team.'),
    'betting-guide': ('Betting Guide | GetSTAM', 'Learn how to read betting odds and use trends to your advantage.'),
    'privacy-policy': ('Privacy Policy | GetSTAM', 'GetSTAM privacy policy.'),
    'feature-requests': ('Feature Requests | GetSTAM', 'Request new features for GetSTAM.'),
    'blog': ('Blog | GetSTAM', 'Sports betting analysis and tips.'),
}

_BLOG_META_NOT_FOUND = '__not_found__'


def _get_blog_post_for_meta(slug):
    """Cached lookup of a published blog post for SSR meta/JSON-LD, mirroring the
    cache pattern used by api/routes/blog.py:get_post."""
    cache_key = f'ssr_blog_meta:{slug}'
    cached = cache.get(cache_key)
    if cached is not None:
        return None if cached == _BLOG_META_NOT_FOUND else cached
    post, _err = BlogService.get_post_by_slug(slug)
    cache.set(cache_key, post if post else _BLOG_META_NOT_FOUND, timeout=43200)
    return post


def _article_json_ld(post, canonical_path, og_image):
    published_at = post.get('published_at')
    updated_at = post.get('updated_at') or published_at
    node = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post.get('title') or '',
        "image": [og_image],
        "datePublished": published_at.isoformat() if published_at else None,
        "dateModified": updated_at.isoformat() if updated_at else None,
        "author": {"@type": "Organization", "name": "GetSTAM"},
        "publisher": {
            "@type": "Organization",
            "name": "GetSTAM",
            "logo": {"@type": "ImageObject", "url": f'{BASE_URL}/logo192.png'},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": f'{BASE_URL}{canonical_path}'},
    }
    return {k: v for k, v in node.items() if v is not None}


_MATCHUP_SLUG_RE = re.compile(
    r'^(?P<away>[a-z0-9-]+?)-vs-(?P<home>[a-z0-9-]+)-(?P<date>\d{4}-\d{2}-\d{2})(?:-(?P<n>\d+))?$'
)
_MATCHUP_META_NOT_FOUND = '__not_found__'


def _breadcrumb_json_ld(names, paths):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": name,
                "item": f'{BASE_URL}{path}',
            }
            for i, (name, path) in enumerate(zip(names, paths))
        ],
    }


def _sports_event_json_ld(matchup, canonical_path):
    node = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": f"{matchup['away_team']} vs {matchup['home_team']}",
        "homeTeam": {"@type": "SportsTeam", "name": matchup['home_team']},
        "awayTeam": {"@type": "SportsTeam", "name": matchup['away_team']},
        "startDate": matchup.get('commence_time'),
        "url": f'{BASE_URL}{canonical_path}',
    }
    return {k: v for k, v in node.items() if v is not None}


def _get_matchup_for_meta(sport, slug):
    """Cached resolver for matchup-page SSR meta: parses the slug, reverse-resolves team
    slugs, and calls GameService.resolve_matchup in-process (mirrors _get_blog_post_for_meta).
    Cached for 20 min (much shorter than blog's 43200s — unlike blog content, odds/scores
    for a game genuinely change), keyed by sport+slug."""
    m = _MATCHUP_SLUG_RE.match(slug)
    if not m:
        return None

    cache_key = f'ssr_matchup_meta:{sport}:{slug}'
    cached = cache.get(cache_key)
    if cached is not None:
        return None if cached == _MATCHUP_META_NOT_FOUND else cached

    away_name = resolve_team_slug(sport, m.group('away'))
    home_name = resolve_team_slug(sport, m.group('home'))
    matchup = None
    if away_name and home_name:
        occurrence = int(m.group('n')) if m.group('n') else 1
        sport_key = convert_sport_url_to_api_key(sport)
        result, _err = GameService.resolve_matchup(sport_key, away_name, home_name, m.group('date'), occurrence)
        if result:
            game = result.get('game') or {}
            matchup = {
                'away_team': game.get('away', {}).get('team') or away_name,
                'home_team': game.get('home', {}).get('team') or home_name,
                'commence_time': game.get('commence_time'),
            }

    cache.set(cache_key, matchup if matchup else _MATCHUP_META_NOT_FOUND, timeout=1200)
    return matchup


def _get_page_meta(path):
    """Return a metadata dict for a given URL path:
    {title, description, canonical_path, og_image, json_ld}."""
    parts = [p for p in path.strip('/').split('/') if p]
    canonical_path = '/' + '/'.join(parts) if parts else '/'
    meta = {
        'title': 'GetSTAM',
        'description': 'Get stats that actually matter for all sports',
        'canonical_path': canonical_path,
        'og_image': DEFAULT_OG_IMAGE,
        'json_ld': [_ORG_WEBSITE_JSON_LD],
    }

    if not parts:
        meta['title'] = 'GetSTAM — Today\'s Betting Trends'
        meta['description'] = ('Today\'s strongest betting trends. Win streaks, H2H patterns, '
                                'and historical probabilities updated every morning.')
        return meta

    slug = parts[0]

    if slug == 'team' and len(parts) >= 3:
        sport_display = _SPORT_DISPLAY.get(parts[1], parts[1].upper())
        team_name = parts[2].replace('-', ' ').title()
        meta['title'] = f'{team_name} {sport_display} Odds & Stats | GetSTAM'
        meta['description'] = f'{team_name} betting odds, ATS records, and recent game results.'
        return meta

    if slug == 'game-details' and len(parts) >= 2:
        sport_name = _SPORT_DISPLAY.get(parts[1], parts[1].upper())
        if len(parts) >= 3:
            matchup = _get_matchup_for_meta(parts[1], parts[2])
            if matchup:
                away, home = matchup['away_team'], matchup['home_team']
                meta['title'] = f'{away} vs {home} {sport_name} Odds & Trends | GetSTAM'
                meta['description'] = (f'{away} vs {home} betting odds, ATS records, over/under trends, '
                                        'and head-to-head history.')
                meta['json_ld'] = [
                    _ORG_WEBSITE_JSON_LD,
                    _sports_event_json_ld(matchup, canonical_path),
                    _breadcrumb_json_ld(
                        ['Home', sport_name, f'{away} vs {home}'],
                        ['/', f'/{parts[1]}', canonical_path],
                    ),
                ]
                return meta
            # not found / aged out beyond the DB window / bad slug — fall through below
        meta['title'] = f'{sport_name} Game Details | GetSTAM'
        meta['description'] = f'Betting odds, trends, and head-to-head stats for this {sport_name} matchup.'
        return meta

    sport_name = _SPORT_DISPLAY.get(slug)
    if sport_name:
        if len(parts) >= 2 and parts[1] == 'trends':
            meta['title'] = f'{sport_name} Trends | GetSTAM'
            meta['description'] = (f'{sport_name} ATS trends, over/under records, and historical '
                                    'betting patterns to find today\'s best matchups.')
        else:
            meta['title'] = f'{sport_name} Games & Odds | GetSTAM'
            meta['description'] = (f"Today's {sport_name} odds, point spreads, over/under lines, "
                                    "and ATS records for every matchup.")
        return meta

    if slug == 'blog':
        if len(parts) >= 2:
            post_slug = parts[1]
            post = _get_blog_post_for_meta(post_slug)
            if post:
                meta['title'] = f"{post['title']} | GetSTAM Blog"
                meta['description'] = post.get('meta_description') or post.get('excerpt') or 'Sports betting insights from GetSTAM.'
                meta['og_image'] = post.get('og_image_url') or post.get('youtube_thumbnail_url') or DEFAULT_OG_IMAGE
                meta['json_ld'] = [_ORG_WEBSITE_JSON_LD, _article_json_ld(post, canonical_path, meta['og_image'])]
                return meta
            # not found / draft / unpublished / bad slug — fall back to generic behavior
            meta['title'] = f'{post_slug.replace("-", " ").title()} | GetSTAM Blog'
            meta['description'] = 'Sports betting insights from GetSTAM.'
            return meta
        meta['title'], meta['description'] = _STATIC_PAGE_META['blog']
        return meta

    if slug in _STATIC_PAGE_META:
        meta['title'], meta['description'] = _STATIC_PAGE_META[slug]
        return meta

    return meta


_index_html_content = None

def _get_index_html():
    global _index_html_content
    if _index_html_content is None:
        with open('getstam-react/build/index.html', 'r') as f:
            _index_html_content = f.read()
    return _index_html_content


def _inject_meta(page_html, meta):
    title = html.escape(meta['title'])
    description = html.escape(meta['description'])
    og_image = html.escape(meta['og_image'])
    canonical_url = html.escape(f"{BASE_URL}{meta['canonical_path']}")

    page_html = re.sub(r'<title>[^<]*</title>', f'<title>{title}</title>', page_html)
    page_html = re.sub(
        r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
        f'<meta name="description" content="{description}" />',
        page_html,
    )
    page_html = re.sub(
        r'<meta\s+property="og:title"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:title" content="{title}" />',
        page_html,
    )
    page_html = re.sub(
        r'<meta\s+property="og:description"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:description" content="{description}" />',
        page_html,
    )
    page_html = re.sub(
        r'<meta\s+property="og:image"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:image" content="{og_image}" />',
        page_html,
    )

    extra_tags = (
        f'<meta property="og:url" content="{canonical_url}" />'
        f'<link rel="canonical" href="{canonical_url}" />'
        f'<meta name="twitter:card" content="summary" />'
        f'<meta name="twitter:title" content="{title}" />'
        f'<meta name="twitter:description" content="{description}" />'
        f'<meta name="twitter:image" content="{og_image}" />'
    )
    json_ld_tags = ''.join(
        '<script type="application/ld+json">'
        + json.dumps(block).replace('<', '\\u003c')
        + '</script>'
        for block in meta['json_ld']
    )

    return page_html.replace('</head>', extra_tags + json_ld_tags + '</head>', 1)


#Route to clear the cache
@app.route('/clear-cache')
def clear_cache():
    global _index_html_content
    cache.clear()
    _index_html_content = None
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
        ('https://www.getstam.com/',              'daily',   '1.0', today),
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

    # Matchup pages — today + tomorrow only, for the 6 sports with team-slug infrastructure.
    # Doubleheader "-2" URLs are intentionally omitted (low value; still reachable via
    # internal links, just not proactively submitted).
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    matchup_sport_keys = {
        'nba': 'basketball_nba', 'nfl': 'americanfootball_nfl', 'mlb': 'baseball_mlb',
        'nhl': 'icehockey_nhl', 'ncaaf': 'americanfootball_ncaaf', 'ncaab': 'basketball_ncaab',
    }
    for date_str in (today, tomorrow):
        for sport, sport_key in matchup_sport_keys.items():
            try:
                result, err = GameService.get_games_for_date(sport_key, date_str)
                if err or not result:
                    continue
                for g in result['games']:
                    away_slug = _team_slug(g['away']['team'])
                    home_slug = _team_slug(g['home']['team'])
                    urls.append(
                        f'  <url><loc>https://www.getstam.com/game-details/{sport}/{away_slug}-vs-{home_slug}-{date_str}</loc>'
                        f'<lastmod>{today}</lastmod><changefreq>hourly</changefreq><priority>0.75</priority></url>'
                    )
            except Exception:
                continue

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
    meta = _get_page_meta(path)
    html_out = _inject_meta(_get_index_html(), meta)
    response = make_response(html_out)
    response.headers['Content-Type'] = 'text/html'
    return response

if __name__ == '__main__':
    # Start the Flask application
    app.run(port=port)

