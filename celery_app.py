from celery import Celery
import os
from dotenv import load_dotenv
import logging

load_dotenv()  # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def make_celery():
    redis_url = os.getenv('REDIS_URL')
    logger.info(f"Using Redis URL: {redis_url}")
    
    celery = Celery(
        'app',
        backend=redis_url,
        broker=redis_url,
    )
    
    # If using rediss://, configure SSL parameters
    if celery.conf.broker_url.startswith('rediss://'):
        ssl_cert_reqs = None
        logger.info(f"Disabling SSL certificate verification")
        celery.conf.update(
            broker_use_ssl={
                'ssl_cert_reqs': ssl_cert_reqs
            },
            redis_backend_use_ssl={
                'ssl_cert_reqs': ssl_cert_reqs
            }
        )
    
    return celery

celery = make_celery()