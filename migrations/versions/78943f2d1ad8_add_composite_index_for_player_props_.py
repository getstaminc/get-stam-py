"""add composite index for player props lookups

Revision ID: 78943f2d1ad8
Revises: db7462da32c7
Create Date: 2026-01-12 12:39:32.506825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78943f2d1ad8'
down_revision: Union[str, None] = 'db7462da32c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite index for optimized lookups by game_date and normalized_name
    op.create_index(
        'idx_nba_player_props_game_date_normalized_name',
        'nba_player_props',
        ['game_date', 'normalized_name'],
        unique=False
    )


def downgrade() -> None:
    # Remove composite index
    op.drop_index(
        'idx_nba_player_props_game_date_normalized_name',
        table_name='nba_player_props'
    )
