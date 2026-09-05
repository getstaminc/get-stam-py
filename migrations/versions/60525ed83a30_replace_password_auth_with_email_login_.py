"""replace password auth with email login codes

Revision ID: 60525ed83a30
Revises: f19d803d8b51
Create Date: 2026-08-25 20:54:51.621798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60525ed83a30'
down_revision: Union[str, None] = 'f19d803d8b51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('login_code_hash', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('login_code_expires_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('users', sa.Column('login_code_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.drop_column('users', 'password_hash')


def downgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.drop_column('users', 'login_code_attempts')
    op.drop_column('users', 'login_code_expires_at')
    op.drop_column('users', 'login_code_hash')
