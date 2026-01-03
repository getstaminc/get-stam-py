"""rename_player_props_to_nba_player_props_add_normalized_name

Revision ID: 6b97fa1714d3
Revises: 01ce1b8d2e73
Create Date: 2026-01-01 13:17:12.190726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b97fa1714d3'
down_revision: Union[str, None] = '01ce1b8d2e73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename player_props table to nba_player_props
    op.rename_table('player_props', 'nba_player_props')
    
    # Add normalized_name column right after player_id (from players table join)
    op.add_column('nba_player_props', sa.Column('normalized_name', sa.String(255), nullable=True))
    
    # Populate normalized_name from players table
    op.execute("""
        UPDATE nba_player_props 
        SET normalized_name = (
            SELECT p.normalized_name 
            FROM players p 
            WHERE p.id = nba_player_props.player_id
        )
    """)
    
    # Create index on normalized_name for performance
    op.create_index('idx_nba_player_props_normalized_name', 'nba_player_props', ['normalized_name'])


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_nba_player_props_normalized_name', 'nba_player_props')
    
    # Remove normalized_name column
    op.drop_column('nba_player_props', 'normalized_name')
    
    # Rename table back
    op.rename_table('nba_player_props', 'player_props')
