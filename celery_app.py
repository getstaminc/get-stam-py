from celery import Celery
import os
from dotenv import load_dotenv
import logging
import ssl  # Import ssl module to disable certificate verification

load_dotenv()  # Load environment variables from .env file

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

def make_celery():
    redis_url = os.getenv('REDIS_URL')
    logger.info(f"Using Redis URL: {redis_url}")
    
    celery = Celery(
        'app',
        backend=redis_url,
        broker=redis_url,
        include=['tasks']  # Ensure tasks are included
    )
    
    # If using rediss://, configure SSL parameters to disable certificate verification
    if celery.conf.broker_url.startswith('rediss://'):
        if os.getenv('FLASK_ENV') == 'development':
            ssl_cert_reqs = ssl.CERT_NONE
            logger.info(f"Setting SSL cert requirements to: {ssl_cert_reqs} for development")
            celery.conf.update(
                broker_use_ssl={
                    'ssl_cert_reqs': ssl_cert_reqs
                },
                redis_backend_use_ssl={
                    'ssl_cert_reqs': ssl_cert_reqs
                }
            )
        else:
            ssl_cert_reqs = ssl.CERT_NONE  # Disable SSL certificate verification for production
            logger.info(f"Disabling SSL certificate verification for production")
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