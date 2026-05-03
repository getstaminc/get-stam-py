from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class MLBBatterProp(Base):
    __tablename__ = 'mlb_batter_props'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('mlb_players.id'), nullable=False)
    normalized_name = Column(String(255))
    game_date = Column(Date, nullable=False)
    odds_event_id = Column(String(100))
    espn_event_id = Column(String(100))
    odds_source = Column(String(50), server_default='odds_api')
    bookmaker = Column(String(50))

    # Batter odds
    odds_batter_hits = Column(Numeric(4, 1))
    odds_batter_hits_over_price = Column(Integer)
    odds_batter_hits_under_price = Column(Integer)
    odds_batter_home_runs = Column(Numeric(4, 1), server_default='0.5')
    odds_batter_home_runs_over_price = Column(Integer)
    odds_batter_home_runs_under_price = Column(Integer)
    odds_batter_rbi = Column(Numeric(4, 1))
    odds_batter_rbi_over_price = Column(Integer)
    odds_batter_rbi_under_price = Column(Integer)
    odds_batter_runs_scored = Column(Numeric(4, 1))
    odds_batter_runs_scored_over_price = Column(Integer)
    odds_batter_runs_scored_under_price = Column(Integer)
    odds_batter_total_bases = Column(Numeric(4, 1))
    odds_batter_total_bases_over_price = Column(Integer)
    odds_batter_total_bases_under_price = Column(Integer)

    # Batter actuals
    actual_batter_hits = Column(Integer)
    actual_batter_home_runs = Column(Integer)
    actual_batter_rbi = Column(Integer)
    actual_batter_runs_scored = Column(Integer)
    actual_batter_total_bases = Column(Integer)  # always null (ESPN doesn't expose doubles/triples per player)
    actual_batter_at_bats = Column(Integer)
    actual_batter_walks = Column(Integer)
    actual_batter_strikeouts = Column(Integer)

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
        UniqueConstraint('player_id', 'odds_event_id', name='uq_mlb_batter_props_player_odds_event'),
        Index('idx_mlb_batter_props_game_date_normalized_name', 'game_date', 'normalized_name'),
        Index('ix_mlb_batter_props_player_game_date', 'player_id', 'game_date'),
    )
