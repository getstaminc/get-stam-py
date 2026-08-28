# limiter.py - Shared rate limiter instance
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Define limiter instance
limiter = Limiter(key_func=get_remote_address)

def init_limiter(app):
    """Initialize rate limiter with app. In-memory storage — resets on restart, not
    shared across worker processes, which is fine for this app's single-worker gunicorn setup."""
    limiter.init_app(app)
    return limiter
