"""create_game_opening_lines_table

Revision ID: 9d14f3a7c2e8
Revises: f4d2b8a61c93
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9d14f3a7c2e8'
down_revision: Union[str, None] = 'f4d2b8a61c93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'game_opening_lines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sport', sa.String(length=50), nullable=False),
        sa.Column('odds_event_id', sa.String(length=100), nullable=False),
        sa.Column('home_team', sa.String(length=100), nullable=False),
        sa.Column('away_team', sa.String(length=100), nullable=False),
        sa.Column('commence_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('opening_snapshot_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('home_spread_point', sa.Float(), nullable=True),
        sa.Column('home_spread_price', sa.Integer(), nullable=True),
        sa.Column('away_spread_point', sa.Float(), nullable=True),
        sa.Column('away_spread_price', sa.Integer(), nullable=True),
        sa.Column('home_moneyline', sa.Integer(), nullable=True),
        sa.Column('away_moneyline', sa.Integer(), nullable=True),
        sa.Column('total_point', sa.Float(), nullable=True),
        sa.Column('over_price', sa.Integer(), nullable=True),
        sa.Column('under_price', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sport', 'odds_event_id', name='uq_game_opening_lines_sport_event'),
    )


def downgrade() -> None:
    op.drop_table('game_opening_lines')
