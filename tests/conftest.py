import os

# Must be set before any api.routes.* module is imported, since several read
# these at import time (e.g. `API_KEY = os.getenv("API_KEY")` in each
# blueprint's before_request check).
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("ODDS_API_KEY", "test-odds-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("FLASK_ENV", "development")  # disables Flask-Caching (CACHE_TYPE=null)
os.environ.setdefault("INTERNAL_PASSWORD", "test-internal-password")
os.environ.setdefault("AUTH_SECRET_KEY", "test-auth-secret")  # auth_service reads this at import time for HMAC code hashing

import pytest
from flask import Flask

from cache import init_cache

TEST_API_KEY = os.environ["API_KEY"]


def make_test_app(*blueprints) -> Flask:
    """Build a minimal Flask app with only the given blueprint(s) registered,
    so a route test doesn't need the full app.py (and its ~30 other
    blueprints/DB-touching services) to import successfully."""
    app = Flask(__name__)
    init_cache(app)
    for bp in blueprints:
        app.register_blueprint(bp)
    return app


@pytest.fixture
def auth_headers():
    return {"X-API-KEY": TEST_API_KEY}
