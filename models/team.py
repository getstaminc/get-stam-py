from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from . import Base

class Team(Base):
    __tablename__ = 'teams'

    team_id = Column(Integer, primary_key=True, autoincrement=True)
    team_name = Column(String(255), nullable=False, unique=True)
    sport = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)