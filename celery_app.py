from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def make_celery():
    celery = Celery(
        'app',
        backend=os.getenv('REDIS_URL'),
        broker=os.getenv('REDIS_URL')
    )
    
    # If using rediss://, configure SSL parameters
    if celery.conf.broker_url.startswith('rediss://'):
        celery.conf.update(
            broker_use_ssl={
                'ssl_cert_reqs': 'CERT_NONE'  # Change to 'CERT_REQUIRED' for production
            },
            redis_backend_use_ssl={
                'ssl_cert_reqs': 'CERT_NONE'  # Change to 'CERT_REQUIRED' for production
            }
        )
    
    return celery

celery = make_celery()

