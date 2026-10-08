"""add actuals_unavailable_reason column

Revision ID: 689b5984c18e
Revises: 60525ed83a30
Create Date: 2026-10-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '689b5984c18e'
down_revision: Union[str, None] = '60525ed83a30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ['mlb_batter_props', 'mlb_pitcher_props', 'nfl_player_props']


def upgrade() -> None:
    # Marks rows where actuals can never be filled in because the game itself
    # was postponed/canceled on its scheduled date (odds were posted pre-game,
    # but ESPN has no boxscore under that date) -- e.g. 'postponed', 'canceled'.
    # NULL means no known reason (actuals are either present or still pending).
    for table in TABLES:
        op.add_column(table, sa.Column('actuals_unavailable_reason', sa.String(30), nullable=True))


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, 'actuals_unavailable_reason')
