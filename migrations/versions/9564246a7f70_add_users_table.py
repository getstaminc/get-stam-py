"""add users table

Revision ID: 9564246a7f70
Revises: ac2df78df254
Create Date: 2026-08-15 22:09:00.322882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9564246a7f70'
down_revision: Union[str, None] = 'ac2df78df254'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='America/New_York'),
        sa.Column('theme_preference', sa.String(length=10), nullable=False, server_default='light'),
        sa.Column('plan', sa.String(length=10), nullable=False, server_default='free'),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('subscription_status', sa.String(length=50), nullable=True),
        sa.Column('trial_ends_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stripe_event_created_at', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('stripe_customer_id'),
        sa.UniqueConstraint('stripe_subscription_id'),
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
