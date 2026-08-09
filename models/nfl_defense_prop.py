from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class NFLDefenseProp(Base):
    """Team defense/special-teams (D/ST) anytime-TD props. The Odds API's
    player_anytime_td market includes team D/ST as a valid entrant alongside
    skill-position players, so this is kept team-scoped and separate from
    NFLPlayerProp rather than faked into a fake nfl_players row."""
    __tablename__ = 'nfl_defense_props'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    team_name = Column(String(100))
    game_date = Column(Date, nullable=False)
    odds_event_id = Column(String(100))
    espn_event_id = Column(String(100))
    odds_source = Column(String(50), server_default='odds_api')
    bookmaker = Column(String(50))

    # Odds data
    odds_anytime_td = Column(Numeric(4, 1))
    odds_anytime_td_over_price = Column(Integer)

    # Actual results (ESPN boxscore team totals: defensive / interceptions /
    # kickReturns / puntReturns stat groups)
    actual_total_tackles = Column(Integer)
    actual_solo_tackles = Column(Integer)
    actual_sacks = Column(Numeric(4, 1))
    actual_tackles_for_loss = Column(Integer)
    actual_passes_defended = Column(Integer)
    actual_qb_hits = Column(Integer)
    actual_defensive_touchdowns = Column(Integer)
    actual_interceptions = Column(Integer)
    actual_interception_yards = Column(Integer)
    actual_interception_touchdowns = Column(Integer)
    actual_kick_returns = Column(Integer)
    actual_kick_return_yards = Column(Integer)
    actual_yards_per_kick_return = Column(Numeric(4, 1))
    actual_long_kick_return = Column(Integer)
    actual_kick_return_touchdowns = Column(Integer)
    actual_punt_returns = Column(Integer)
    actual_punt_return_yards = Column(Integer)
    actual_yards_per_punt_return = Column(Numeric(4, 1))
    actual_long_punt_return = Column(Integer)
    actual_punt_return_touchdowns = Column(Integer)
    actual_anytime_td = Column(Boolean)

    # Team info
    opponent_team_name = Column(String(100))
    opponent_team_id = Column(Integer, ForeignKey('teams.team_id'))

    # Odds API team info
    odds_home_team = Column(String(100))
    odds_away_team = Column(String(100))
    odds_home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_away_team_id = Column(Integer, ForeignKey('teams.team_id'))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('team_id', 'odds_event_id', name='uq_nfl_defense_props_team_odds_event'),
        Index('idx_nfl_defense_props_game_date', 'game_date'),
        Index('ix_nfl_defense_props_team_game_date', 'team_id', 'game_date'),
    )
