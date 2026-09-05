"""add_nfl_player_props_actual_misc_td

Revision ID: 9d4e6a1b2c3f
Revises: 8c1d5f2a3e7b
Create Date: 2026-07-30 00:00:00.000000

Adds actual_misc_td to nfl_player_props: touchdowns that never show up in the
boxscore's per-athlete passing/rushing/receiving stats (kickoff/punt return,
fumble return, interception return, blocked kick return TDs), parsed instead
from ESPN's scoringPlays free-text feed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d4e6a1b2c3f'
down_revision: Union[str, None] = '8c1d5f2a3e7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'nfl_player_props',
        sa.Column('actual_misc_td', sa.Integer, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('nfl_player_props', 'actual_misc_td')
