from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class MLBPitcherProp(Base):
    __tablename__ = 'mlb_pitcher_props'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('mlb_players.id'), nullable=False)
    normalized_name = Column(String(255))
    game_date = Column(Date, nullable=False)
    odds_event_id = Column(String(100))
    espn_event_id = Column(String(100))
    odds_source = Column(String(50), server_default='odds_api')
    bookmaker = Column(String(50))

    # Pitcher odds
    odds_pitcher_strikeouts = Column(Numeric(4, 1))
    odds_pitcher_strikeouts_over_price = Column(Integer)
    odds_pitcher_strikeouts_under_price = Column(Integer)
    odds_pitcher_earned_runs = Column(Numeric(4, 1))
    odds_pitcher_earned_runs_over_price = Column(Integer)
    odds_pitcher_earned_runs_under_price = Column(Integer)
    odds_pitcher_hits_allowed = Column(Numeric(4, 1))
    odds_pitcher_hits_allowed_over_price = Column(Integer)
    odds_pitcher_hits_allowed_under_price = Column(Integer)
    odds_pitcher_walks = Column(Numeric(4, 1))
    odds_pitcher_walks_over_price = Column(Integer)
    odds_pitcher_walks_under_price = Column(Integer)

    # Pitcher actuals
    actual_pitcher_strikeouts = Column(Integer)
    actual_pitcher_earned_runs = Column(Integer)
    actual_pitcher_hits_allowed = Column(Integer)
    actual_pitcher_walks = Column(Integer)
    actual_pitcher_innings_pitched = Column(String(10))  # e.g. "6.0", "6 2/3"

    # Team info
    player_team_name = Column(String(100))
    player_team_id = Column(Integer, ForeignKey('teams.team_id'))
    opponent_team_name = Column(String(100))
    opponent_team_id = Column(Integer, ForeignKey('teams.team_id'))

    # Odds API team info
    odds_home_team = Column(String(100))
    odds_away_team = Column(String(100))
    odds_home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_away_team_id = Column(Integer, ForeignKey('teams.team_id'))

    did_not_play = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('player_id', 'odds_event_id', name='uq_mlb_pitcher_props_player_odds_event'),
        Index('idx_mlb_pitcher_props_game_date_normalized_name', 'game_date', 'normalized_name'),
        Index('ix_mlb_pitcher_props_player_game_date', 'player_id', 'game_date'),
    )
