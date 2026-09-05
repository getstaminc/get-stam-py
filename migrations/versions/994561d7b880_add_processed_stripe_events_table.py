"""add processed stripe events table

Revision ID: 994561d7b880
Revises: 9564246a7f70
Create Date: 2026-08-15 22:09:40.640559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '994561d7b880'
down_revision: Union[str, None] = '9564246a7f70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('processed_stripe_events',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('processed_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('processed_stripe_events')
