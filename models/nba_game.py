from sqlalchemy import Column, Integer, String, Float, Date, JSON, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from . import Base

class NBA_Game(Base):
    __tablename__ = 'nba_games'

    game_id = Column(Integer, primary_key=True, autoincrement=True)
    game_date = Column(Date, nullable=False)
    game_site = Column(String(50), nullable=False)
    home_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    home_points = Column(Integer, nullable=False)  # Points for NBA
    away_points = Column(Integer, nullable=False)
    total_points = Column(Float, nullable=False)
    total_margin = Column(Float, nullable=False)
    home_line = Column(Float, nullable=False)
    away_line = Column(Float, nullable=False)
    quarter_scores = Column(JSON, nullable=False)  # Quarter scores for NBA
    home_halftime_points = Column(Integer, nullable=False)
    away_halftime_points = Column(Integer, nullable=False)
    sdql_game_id = Column(String(255), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)  # Timestamp for when the record was created