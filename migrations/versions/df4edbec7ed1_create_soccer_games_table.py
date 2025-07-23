"""create soccer_games table

Revision ID: df4edbec7ed1
Revises: ff9d10eea272
Create Date: 2025-07-05 14:50:44.818716

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func
from soccer_utils import translate_soccer_team_name  # Assuming this function exists in soccer_utils.py


# revision identifiers, used by Alembic.
revision: str = 'df4edbec7ed1'
down_revision: Union[str, None] = 'ff9d10eea272'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'soccer_games',
        sa.Column('game_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('odds_id', sa.String(100)),
        sa.Column('league', sa.String(100), nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('home_team_name', sa.String(length=100), nullable=False),
        sa.Column('away_team_name', sa.String(length=100), nullable=False),
        # Soccer-specific fields
        sa.Column('home_goals', sa.Integer()),
        sa.Column('total_goals', sa.Integer()),
        sa.Column('away_goals', sa.Integer()),
        sa.Column('home_money_line', sa.Integer(), nullable=True),
        sa.Column('draw_money_line', sa.Integer(), nullable=True),
        sa.Column('away_money_line', sa.Integer(), nullable=True),
        sa.Column('home_spread', sa.Float()),
        sa.Column('away_spread', sa.Float()),
        sa.Column('total_over_point', sa.Float()),
        sa.Column('total_over_price', sa.Integer()),
        sa.Column('total_under_point', sa.Float()),
        sa.Column('total_under_price', sa.Integer()),
        # Half/second half goals (match NFL nullability)
        sa.Column('home_first_half_goals', sa.Integer(), nullable=True),
        sa.Column('away_first_half_goals', sa.Integer(), nullable=True),
        sa.Column('home_second_half_goals', sa.Integer(), nullable=True),
        sa.Column('away_second_half_goals', sa.Integer(), nullable=True),
        sa.Column('away_overtime', sa.Integer(), nullable=True),
        sa.Column('home_overtime', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('created_date', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('modified_date', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('game_id')
    )

def downgrade():
    op.drop_table('soccer_games')
