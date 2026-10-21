from sqlalchemy import Column, Integer, String, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from .base import Base


class GameOpeningLine(Base):
    __tablename__ = 'game_opening_lines'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sport = Column(String(50), nullable=False)
    odds_event_id = Column(String(100), nullable=False)
    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)
    commence_time = Column(TIMESTAMP(timezone=True), nullable=False)
    opening_snapshot_time = Column(TIMESTAMP(timezone=True), nullable=False)
    home_spread_point = Column(Float)
    home_spread_price = Column(Integer)
    away_spread_point = Column(Float)
    away_spread_price = Column(Integer)
    home_moneyline = Column(Integer)
    away_moneyline = Column(Integer)
    total_point = Column(Float)
    over_price = Column(Integer)
    under_price = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('sport', 'odds_event_id', name='uq_game_opening_lines_sport_event'),
    )
