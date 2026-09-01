"""merge heads before users table

Revision ID: ac2df78df254
Revises: a7c2e9f4b1d3, d1e2f3a4b5c6
Create Date: 2026-08-15 22:08:41.922816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac2df78df254'
down_revision: Union[str, None] = ('a7c2e9f4b1d3', 'd1e2f3a4b5c6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
