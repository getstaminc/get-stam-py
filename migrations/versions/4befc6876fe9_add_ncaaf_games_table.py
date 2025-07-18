"""add ncaaf games table

Revision ID: 4befc6876fe9
Revises: 9885458f3f43
Create Date: 2025-06-17 09:50:14.634930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = '4befc6876fe9'
down_revision: Union[str, None] = '9885458f3f43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ncaaf_games',
        sa.Column('game_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('game_site', sa.String(length=10), nullable=False),
        sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('home_team_name', sa.String(length=100), nullable=False),  # Pretty name for home team
        sa.Column('away_team_name', sa.String(length=100), nullable=False),  # Pretty name for away team
        sa.Column('home_points', sa.Integer(), nullable=False),
        sa.Column('away_points', sa.Integer(), nullable=False),
        sa.Column('total_points', sa.Float(), nullable=True),
        sa.Column('total_margin', sa.Float(), nullable=True),
        sa.Column('home_line', sa.Float(), nullable=True),
        sa.Column('away_line', sa.Float(), nullable=True),
        sa.Column('home_quarter_scores', sa.JSON(), nullable=True),  # Add this column
        sa.Column('away_quarter_scores', sa.JSON(), nullable=True),  # Add this column
        sa.Column('home_first_half_points', sa.Integer(), nullable=True),  # Renamed from home_halftime_points
        sa.Column('away_first_half_points', sa.Integer(), nullable=True),  # Renamed from away_halftime_points
        sa.Column('home_second_half_points', sa.Integer(), nullable=True),  # New column
        sa.Column('away_second_half_points', sa.Integer(), nullable=True),  # New column
        sa.Column('home_overtime_points', sa.Integer(), nullable=True),  # New column
        sa.Column('away_overtime_points', sa.Integer(), nullable=True),  # New column
        sa.Column('home_money_line', sa.Integer(), nullable=True),  # Added this column
        sa.Column('away_money_line', sa.Integer(), nullable=True),  # Added this column
        sa.Column('playoffs', sa.Boolean(), nullable=True),  # Added this column
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('sdql_game_id', sa.Integer(), nullable=True),
        sa.Column('created_date', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),  # Auto-populated on creation
        sa.Column('modified_date', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),  # Auto-updated on modification
        sa.PrimaryKeyConstraint('game_id')
    )


def downgrade() -> None:
    op.drop_table('ncaaf_games')
