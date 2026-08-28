from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from .base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    timezone = Column(String(50), nullable=False, server_default='America/New_York')
    theme_preference = Column(String(10), nullable=False, server_default='light')
    plan = Column(String(10), nullable=False, server_default='free')
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    subscription_status = Column(String(50), nullable=True)
    trial_ends_at = Column(TIMESTAMP, nullable=True)
    email_verified_at = Column(TIMESTAMP, nullable=True)
    signup_intent = Column(String(10), nullable=True)
    login_code_hash = Column(String(64), nullable=True)
    login_code_expires_at = Column(TIMESTAMP, nullable=True)
    login_code_attempts = Column(Integer, nullable=False, server_default='0')
    access_code_id = Column(Integer, nullable=True)
    access_code_redeemed_at = Column(TIMESTAMP, nullable=True)
    token_version = Column(Integer, nullable=False, server_default='0')
    stripe_event_created_at = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
