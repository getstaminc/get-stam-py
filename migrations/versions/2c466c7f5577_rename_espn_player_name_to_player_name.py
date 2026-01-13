"""rename espn_player_name to player_name

Revision ID: 2c466c7f5577
Revises: 43f680ff2677
Create Date: 2026-01-12 21:15:04.123227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c466c7f5577'
down_revision: Union[str, None] = '43f680ff2677'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename espn_player_name to player_name for source-agnostic naming
    op.alter_column('nba_players', 'espn_player_name', new_column_name='player_name')


def downgrade() -> None:
    # Revert player_name back to espn_player_name
    op.alter_column('nba_players', 'player_name', new_column_name='espn_player_name')
