from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class NHLPlayerProp(Base):
    __tablename__ = 'nhl_player_props'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('nhl_players.id'), nullable=False)
    normalized_name = Column(String(255))
    game_date = Column(Date, nullable=False)
    odds_event_id = Column(String(100))
    espn_event_id = Column(String(100))
    odds_source = Column(String(50), server_default='odds_api')
    bookmaker = Column(String(50))

    odds_player_goals = Column(Numeric(4, 1))
    odds_player_goals_over_price = Column(Integer)
    odds_player_goals_under_price = Column(Integer)
    odds_player_assists = Column(Numeric(4, 1))
    odds_player_assists_over_price = Column(Integer)
    odds_player_assists_under_price = Column(Integer)
    odds_player_points = Column(Numeric(4, 1))
    odds_player_points_over_price = Column(Integer)
    odds_player_points_under_price = Column(Integer)
    odds_player_shots_on_goal = Column(Numeric(4, 1))
    odds_player_shots_on_goal_over_price = Column(Integer)
    odds_player_shots_on_goal_under_price = Column(Integer)
    odds_player_total_saves = Column(Numeric(4, 1))
    odds_player_total_saves_over_price = Column(Integer)
    odds_player_total_saves_under_price = Column(Integer)
    odds_player_goal_scorer_anytime = Column(Numeric(4, 1))
    odds_player_goal_scorer_anytime_over_price = Column(Integer)

    actual_player_goals = Column(Integer)
    actual_player_assists = Column(Integer)
    actual_player_points = Column(Integer)
    actual_player_shots_on_goal = Column(Integer)
    actual_player_total_saves = Column(Integer)
    actual_player_goal_scorer_anytime = Column(Boolean)

    player_team_name = Column(String(100))
    player_team_id = Column(Integer, ForeignKey('teams.team_id'))
    opponent_team_name = Column(String(100))
    opponent_team_id = Column(Integer, ForeignKey('teams.team_id'))

    odds_home_team = Column(String(100))
    odds_away_team = Column(String(100))
    odds_home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    odds_away_team_id = Column(Integer, ForeignKey('teams.team_id'))

    did_not_play = Column(Boolean, nullable=False, default=False)
    actuals_unavailable_reason = Column(String(30))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('player_id', 'odds_event_id', name='uq_nhl_player_props_player_odds_event'),
        Index('idx_nhl_player_props_game_date_normalized_name', 'game_date', 'normalized_name'),
        Index('ix_nhl_player_props_player_game_date', 'player_id', 'game_date'),
    )
