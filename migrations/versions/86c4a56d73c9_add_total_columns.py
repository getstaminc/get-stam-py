"""add total columns

Revision ID: 86c4a56d73c9
Revises: c674b45b084a
Create Date: 2025-08-12 12:19:21.801056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86c4a56d73c9'
down_revision: Union[str, None] = 'c674b45b084a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add the 'total' column to the nfl_games table
    op.add_column('nfl_games', sa.Column('total', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove the 'total' column from the nfl_games table
    op.drop_column('nfl_games', 'total')