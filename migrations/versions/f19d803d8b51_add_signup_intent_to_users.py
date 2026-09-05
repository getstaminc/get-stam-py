"""add signup intent to users

Revision ID: f19d803d8b51
Revises: ce57379f6e4d
Create Date: 2026-08-17 11:10:37.165233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f19d803d8b51'
down_revision: Union[str, None] = 'ce57379f6e4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('signup_intent', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'signup_intent')
