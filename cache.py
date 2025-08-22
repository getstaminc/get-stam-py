# cache.py - Shared cache instance
from flask_caching import Cache
import os

# Define cache instance
cache = Cache()

def init_cache(app):
    """Initialize cache with app"""
    # if os.getenv('FLASK_ENV') == 'development':
    #     cache_config = {'CACHE_TYPE': 'null'}  # Disable caching in development
    # else:
    cache_config = {'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300}  # Enable caching with 5-minute timeout
    
    cache.init_app(app, config=cache_config)
    return cache
