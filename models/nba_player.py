from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from .base import Base


class NBAPlayer(Base):
    __tablename__ = 'nba_players'

    id = Column(Integer, primary_key=True, autoincrement=True)
    espn_player_id = Column(String(50), unique=True)
    player_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    position = Column(String(10))
    team_id = Column(Integer, ForeignKey('teams.team_id'))
    first_seen_date = Column(Date, nullable=False)
    last_seen_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_players_normalized_name', 'normalized_name'),
    )
