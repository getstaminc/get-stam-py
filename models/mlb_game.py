from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Time, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from .base import Base


class MLBGame(Base):
    __tablename__ = 'mlb_games'

    game_id = Column(Integer, primary_key=True, autoincrement=True)
    game_date = Column(Date, nullable=False)
    game_site = Column(String(100), nullable=False)
    home_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    home_team_name = Column(String(100), nullable=False)
    away_team_name = Column(String(100), nullable=False)
    home_runs = Column(Integer, nullable=False)
    away_runs = Column(Integer, nullable=False)
    total = Column(Float)
    total_runs = Column(Float)
    total_margin = Column(Float)
    home_line = Column(Float)
    away_line = Column(Float)
    home_money_line = Column(Integer)
    away_money_line = Column(Integer)
    playoffs = Column(Boolean)
    start_time = Column(Time)
    home_first_5_line = Column(Float)
    away_first_5_line = Column(Float)
    total_first_5 = Column(Integer)
    first_5_over_odds = Column(Integer)
    first_5_under_odds = Column(Integer)
    home_starting_pitcher = Column(String(100))
    away_starting_pitcher = Column(String(100))
    home_inning_runs = Column(JSON)
    away_inning_runs = Column(JSON)
    home_first_5_runs = Column(Integer)
    away_first_5_runs = Column(Integer)
    home_remaining_runs = Column(Integer)
    away_remaining_runs = Column(Integer)
    sdql_game_id = Column(Integer, unique=True)
    odds_event_id = Column(String(100), unique=True)
    created_date = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    modified_date = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
