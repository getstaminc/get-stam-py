"""add access codes table and user columns

Revision ID: ce57379f6e4d
Revises: 7fd664141498
Create Date: 2026-08-16 21:39:21.948072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce57379f6e4d'
down_revision: Union[str, None] = '7fd664141498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('access_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('max_redemptions', sa.Integer(), nullable=True),
        sa.Column('redemption_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('idx_access_codes_code', 'access_codes', ['code'], unique=True)

    op.add_column('users', sa.Column('access_code_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('access_code_redeemed_at', sa.TIMESTAMP(), nullable=True))
    op.create_foreign_key(
        'fk_users_access_code_id', 'users', 'access_codes', ['access_code_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_access_code_id', 'users', type_='foreignkey')
    op.drop_column('users', 'access_code_redeemed_at')
    op.drop_column('users', 'access_code_id')
    op.drop_index('idx_access_codes_code', table_name='access_codes')
    op.drop_table('access_codes')
