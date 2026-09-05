from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.sql import func
from .base import Base


class NFLPlayerNameMismatch(Base):
    __tablename__ = 'nfl_player_name_mismatch'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nfl_player_props_id = Column(Integer, ForeignKey('nfl_player_props.id'), nullable=False)
    game_date = Column(Date, nullable=False)
    odds_home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_away_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_home_team = Column(String(100))
    odds_away_team = Column(String(100))
    normalized_name = Column(String(255), nullable=False)
    player_id = Column(Integer, ForeignKey('nfl_players.id'))
    resolved = Column(Boolean, nullable=False, default=False)
    resolution_notes = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_nfl_name_mismatch_game_date', 'game_date'),
        Index('idx_nfl_name_mismatch_resolved', 'resolved'),
        Index('idx_nfl_name_mismatch_player_props', 'nfl_player_props_id'),
    )
