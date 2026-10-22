from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ARRAY, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from .base import Base


class NHL_Game(Base):
    __tablename__ = 'nhl_games'

    game_id = Column(Integer, primary_key=True, autoincrement=True)
    game_date = Column(Date, nullable=False)
    game_site = Column(String(100), nullable=False)
    home_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    home_team_name = Column(String(100), nullable=False)
    away_team_name = Column(String(100), nullable=False)
    home_goals = Column(Integer, nullable=False)
    away_goals = Column(Integer, nullable=False)
    home_money_line = Column(Float)
    away_money_line = Column(Float)
    home_period_goals = Column(ARRAY(Integer))
    away_period_goals = Column(ARRAY(Integer))
    home_starting_goalie = Column(String(100))
    away_starting_goalie = Column(String(100))
    home_powerplay_goals = Column(Integer)
    away_powerplay_goals = Column(Integer)
    total = Column(Float)
    overtime = Column(Boolean)
    shoot_out = Column(Boolean)
    playoffs = Column(Boolean)
    sdql_game_id = Column(Integer, unique=True)
    odds_event_id = Column(String(100), unique=True)
    created_date = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    modified_date = Column(TIMESTAMP, server_default=func.now(), nullable=False)
