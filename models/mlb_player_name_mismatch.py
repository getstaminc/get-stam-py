from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class MLBPlayerNameMismatch(Base):
    __tablename__ = 'mlb_player_name_mismatch'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batter_props_id = Column(Integer, ForeignKey('mlb_batter_props.id'), nullable=True)
    pitcher_props_id = Column(Integer, ForeignKey('mlb_pitcher_props.id'), nullable=True)
    game_date = Column(Date, nullable=False)
    odds_home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_away_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_home_team = Column(String(100))
    odds_away_team = Column(String(100))
    normalized_name = Column(String(255), nullable=False)
    player_id = Column(Integer, ForeignKey('mlb_players.id'))
    resolved = Column(Boolean, nullable=False, default=False)
    resolution_notes = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            '(batter_props_id IS NOT NULL)::int + (pitcher_props_id IS NOT NULL)::int = 1',
            name='chk_mlb_name_mismatch_exactly_one_props_id'
        ),
        Index('idx_mlb_name_mismatch_game_date', 'game_date'),
        Index('idx_mlb_name_mismatch_resolved', 'resolved'),
        Index('idx_mlb_name_mismatch_batter_props', 'batter_props_id'),
        Index('idx_mlb_name_mismatch_pitcher_props', 'pitcher_props_id'),
    )
