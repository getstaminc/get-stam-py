"""add_player_props_tables

Revision ID: 01ce1b8d2e73
Revises: b460d3e1ede4
Create Date: 2025-12-30 21:58:32.263413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01ce1b8d2e73'
down_revision: Union[str, None] = 'b460d3e1ede4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create players table (canonical player identity)
    op.create_table(
        'players',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('espn_player_id', sa.String(50), unique=True, nullable=True),  # NULLABLE for odds-first ingestion
        sa.Column('espn_player_name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('position', sa.String(10)),
        sa.Column('team_id', sa.Integer, sa.ForeignKey('teams.team_id')),  # FK to teams table
        sa.Column('first_seen_date', sa.Date, nullable=False),
        sa.Column('last_seen_date', sa.Date, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())  # Auto-update
    )

    # Create player_aliases table (name mapping per source)
    op.create_table(
        'player_aliases',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),  # 'odds_api', 'espn', 'manual'
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('source', 'normalized_name', name='uq_player_aliases_source_normalized')
    )

    # Create player_props table (game-specific records)
    op.create_table(
        'player_props',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('players.id'), nullable=False),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('odds_event_id', sa.String(100)),  # Odds API event ID (nullable)
        sa.Column('espn_event_id', sa.String(100)),  # ESPN event ID (nullable)
        
        # Source tracking
        sa.Column('odds_source', sa.String(50), server_default='odds_api'),
        sa.Column('bookmaker', sa.String(50)),  # fanduel, draftkings, bovada, etc
        
        # Odds data (from Odds API)
        sa.Column('odds_player_points', sa.Numeric(4,1)),
        sa.Column('odds_player_points_over_price', sa.Integer),
        sa.Column('odds_player_points_under_price', sa.Integer),
        sa.Column('odds_player_rebounds', sa.Numeric(4,1)),
        sa.Column('odds_player_rebounds_over_price', sa.Integer),
        sa.Column('odds_player_rebounds_under_price', sa.Integer),
        sa.Column('odds_player_assists', sa.Numeric(4,1)),
        sa.Column('odds_player_assists_over_price', sa.Integer),
        sa.Column('odds_player_assists_under_price', sa.Integer),
        sa.Column('odds_player_threes', sa.Numeric(4,1)),
        sa.Column('odds_player_threes_over_price', sa.Integer),
        sa.Column('odds_player_threes_under_price', sa.Integer),
        
        # Actual results (from ESPN)
        sa.Column('actual_player_points', sa.Integer),
        sa.Column('actual_player_rebounds', sa.Integer),
        sa.Column('actual_player_assists', sa.Integer),
        sa.Column('actual_player_threes', sa.Integer),
        sa.Column('actual_player_minutes', sa.String(10)),
        sa.Column('actual_player_fg', sa.String(10)),
        sa.Column('actual_player_ft', sa.String(10)),
        sa.Column('actual_plus_minus', sa.Integer),
        
        # Team info
        sa.Column('player_team', sa.String(100)),
        sa.Column('player_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),  # FK to teams table
        sa.Column('opponent_team', sa.String(100)),
        sa.Column('opponent_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),  # FK to teams table
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),  # Auto-update
        
        sa.UniqueConstraint('player_id', 'odds_event_id', name='uq_player_props_player_odds_event')
    )

    # Create indexes for performance
    op.create_index('ix_players_normalized_name', 'players', ['normalized_name'])
    op.create_index('ix_player_aliases_normalized_name', 'player_aliases', ['normalized_name'])
    op.create_index('ix_player_props_game_date', 'player_props', ['game_date'])
    op.create_index('ix_player_props_player_game_date', 'player_props', ['player_id', 'game_date'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_player_props_player_game_date', 'player_props')
    op.drop_index('ix_player_props_game_date', 'player_props')
    op.drop_index('ix_player_aliases_normalized_name', 'player_aliases')
    op.drop_index('ix_players_normalized_name', 'players')
    
    # Drop tables in reverse order
    op.drop_table('player_props')
    op.drop_table('player_aliases')
    op.drop_table('players')
