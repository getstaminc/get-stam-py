from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class NFLPlayerAlias(Base):
    __tablename__ = 'nfl_player_aliases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('nfl_players.id', ondelete='CASCADE'), nullable=False)
    source = Column(String(50), nullable=False)
    source_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('source', 'normalized_name', name='uq_nfl_player_aliases_source_normalized'),
        Index('ix_nfl_player_aliases_normalized_name', 'normalized_name'),
    )
