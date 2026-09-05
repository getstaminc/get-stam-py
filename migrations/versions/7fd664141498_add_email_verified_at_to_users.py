"""add email verified at to users

Revision ID: 7fd664141498
Revises: 994561d7b880
Create Date: 2026-08-16 21:12:03.155255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7fd664141498'
down_revision: Union[str, None] = '994561d7b880'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email_verified_at', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'email_verified_at')
