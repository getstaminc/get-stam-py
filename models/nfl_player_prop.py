from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class NFLPlayerProp(Base):
    __tablename__ = 'nfl_player_props'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('nfl_players.id'), nullable=False)
    normalized_name = Column(String(255))
    game_date = Column(Date, nullable=False)
    odds_event_id = Column(String(100))
    espn_event_id = Column(String(100))
    odds_source = Column(String(50), server_default='odds_api')
    bookmaker = Column(String(50))

    # Odds data
    odds_player_pass_yds = Column(Numeric(4, 1))
    odds_player_pass_yds_over_price = Column(Integer)
    odds_player_pass_yds_under_price = Column(Integer)
    odds_player_pass_tds = Column(Numeric(4, 1))
    odds_player_pass_tds_over_price = Column(Integer)
    odds_player_pass_tds_under_price = Column(Integer)
    odds_player_rush_yds = Column(Numeric(4, 1))
    odds_player_rush_yds_over_price = Column(Integer)
    odds_player_rush_yds_under_price = Column(Integer)
    odds_player_reception_yds = Column(Numeric(4, 1))
    odds_player_reception_yds_over_price = Column(Integer)
    odds_player_reception_yds_under_price = Column(Integer)
    odds_player_receptions = Column(Numeric(4, 1))
    odds_player_receptions_over_price = Column(Integer)
    odds_player_receptions_under_price = Column(Integer)
    odds_player_anytime_td = Column(Numeric(4, 1))
    odds_player_anytime_td_over_price = Column(Integer)

    # Actual results
    actual_player_pass_yds = Column(Integer)
    actual_player_pass_tds = Column(Integer)
    actual_player_rush_yds = Column(Integer)
    actual_player_reception_yds = Column(Integer)
    actual_player_receptions = Column(Integer)
    actual_player_rushing_td = Column(Integer)
    actual_player_receiving_td = Column(Integer)
    actual_player_anytime_td = Column(Boolean)

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
        UniqueConstraint('player_id', 'odds_event_id', name='uq_nfl_player_props_player_odds_event'),
        Index('idx_nfl_player_props_game_date_normalized_name', 'game_date', 'normalized_name'),
        Index('ix_nfl_player_props_player_game_date', 'player_id', 'game_date'),
    )
