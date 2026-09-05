from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.sql import func
from .base import Base


class ProcessedStripeEvent(Base):
    __tablename__ = 'processed_stripe_events'

    id = Column(String(255), primary_key=True)
    processed_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
