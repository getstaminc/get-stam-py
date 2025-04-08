"""Create nba_games table

Revision ID: f58aaeaf3ed3
Revises: 8d200c5054dd
Create Date: 2025-04-08 12:13:23.301237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f58aaeaf3ed3'
down_revision: Union[str, None] = '8d200c5054dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
