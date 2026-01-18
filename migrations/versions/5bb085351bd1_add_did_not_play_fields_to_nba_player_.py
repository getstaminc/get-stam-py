"""add_did_not_play_fields_to_nba_player_props

Revision ID: 5bb085351bd1
Revises: 989844439625
Create Date: 2026-01-17 21:07:04.040205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bb085351bd1'
down_revision: Union[str, None] = '989844439625'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add did_not_play boolean column (defaults to False)
    op.add_column('nba_player_props', 
        sa.Column('did_not_play', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('nba_player_props', 'did_not_play')
