"""Create nfl_games table

Revision ID: f1d16e9bed05
Revises: 72aa2fceef5e
Create Date: 2025-05-27 21:41:06.629324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1d16e9bed05'
down_revision: Union[str, None] = '72aa2fceef5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'nfl_games',
        sa.Column('game_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('game_site', sa.String(length=10), nullable=False),
        sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('home_points', sa.Integer(), nullable=False),
        sa.Column('away_points', sa.Integer(), nullable=False),
        sa.Column('total_points', sa.Float(), nullable=True),
        sa.Column('total_margin', sa.Float(), nullable=True),
        sa.Column('home_line', sa.Float(), nullable=True),
        sa.Column('away_line', sa.Float(), nullable=True),
        sa.Column('quarter_scores', sa.JSON(), nullable=True),
        sa.Column('home_halftime_points', sa.Integer(), nullable=True),
        sa.Column('away_halftime_points', sa.Integer(), nullable=True),
        sa.Column('sdql_game_id', sa.Integer(), unique=True, nullable=True),
        sa.PrimaryKeyConstraint('game_id')
    )


def downgrade() -> None:
    op.drop_table('nfl_games')
