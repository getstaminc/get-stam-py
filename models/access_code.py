from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from .base import Base


class AccessCode(Base):
    __tablename__ = 'access_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    label = Column(String(255), nullable=True)
    max_redemptions = Column(Integer, nullable=True)
    redemption_count = Column(Integer, nullable=False, server_default='0')
    expires_at = Column(TIMESTAMP, nullable=True)
    active = Column(Boolean, nullable=False, server_default='true')
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
