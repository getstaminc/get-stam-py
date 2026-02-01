"""create nba_player_name_mismatch table

Revision ID: e52d07871c8a
Revises: 5bb085351bd1
Create Date: 2026-01-23 20:39:24.989087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e52d07871c8a'
down_revision: Union[str, None] = '5bb085351bd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create nba_player_name_mismatch table to track players that couldn't be matched
    between odds data and ESPN actual data.
    """
    op.create_table(
        'nba_player_name_mismatch',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('nba_player_props_id', sa.Integer(), nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('odds_home_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_away_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_home_team', sa.String(100), nullable=True),
        sa.Column('odds_away_team', sa.String(100), nullable=True),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
    )
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_name_mismatch_player_props',
        'nba_player_name_mismatch', 'nba_player_props',
        ['nba_player_props_id'], ['id']
    )
    
    op.create_foreign_key(
        'fk_name_mismatch_player',
        'nba_player_name_mismatch', 'nba_players',
        ['player_id'], ['id']
    )
    
    op.create_foreign_key(
        'fk_name_mismatch_home_team',
        'nba_player_name_mismatch', 'teams',
        ['odds_home_team_id'], ['team_id']
    )
    
    op.create_foreign_key(
        'fk_name_mismatch_away_team',
        'nba_player_name_mismatch', 'teams',
        ['odds_away_team_id'], ['team_id']
    )
    
    # Add indexes for common queries
    op.create_index(
        'idx_name_mismatch_game_date',
        'nba_player_name_mismatch',
        ['game_date']
    )
    
    op.create_index(
        'idx_name_mismatch_resolved',
        'nba_player_name_mismatch',
        ['resolved']
    )
    
    op.create_index(
        'idx_name_mismatch_player_props',
        'nba_player_name_mismatch',
        ['nba_player_props_id']
    )


def downgrade() -> None:
    """
    Drop nba_player_name_mismatch table.
    """
    op.drop_table('nba_player_name_mismatch')
