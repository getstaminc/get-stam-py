"""create mlb games table

Revision ID: 9c03298fda01
Revises: 317ce53953ff
Create Date: 2025-08-26 22:31:42.764526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = '9c03298fda01'
down_revision: Union[str, None] = '317ce53953ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'mlb_games',
        sa.Column('game_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('game_site', sa.String(length=100), nullable=False), 
        sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('home_team_name', sa.String(length=100), nullable=False),
        sa.Column('away_team_name', sa.String(length=100), nullable=False),
        sa.Column('home_runs', sa.Integer(), nullable=False),
        sa.Column('away_runs', sa.Integer(), nullable=False),
        sa.Column('total', sa.Float(), nullable=True),  # Match NFL/NBA float type
        sa.Column('total_runs', sa.Float(), nullable=True),  # Match NBA float type
        sa.Column('total_margin', sa.Float(), nullable=True),  # Match NBA float type
        sa.Column('home_line', sa.Float(), nullable=True),
        sa.Column('away_line', sa.Float(), nullable=True),
        sa.Column('home_money_line', sa.Integer(), nullable=True),  # moneyline odds
        sa.Column('away_money_line', sa.Integer(), nullable=True),  # moneyline odds
        sa.Column('playoffs', sa.Boolean(), nullable=True),  # Match NBA boolean type
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('home_first_5_line', sa.Float(), nullable=True),
        sa.Column('away_first_5_line', sa.Float(), nullable=True),
        sa.Column('total_first_5', sa.Integer(), nullable=True),
        sa.Column('first_5_over_odds', sa.Integer(), nullable=True),
        sa.Column('first_5_under_odds', sa.Integer(), nullable=True),
        sa.Column('home_starting_pitcher', sa.String(length=100), nullable=True),
        sa.Column('away_starting_pitcher', sa.String(length=100), nullable=True),
        sa.Column('home_inning_runs', sa.JSON(), nullable=True),  # array of runs per inning
        sa.Column('away_inning_runs', sa.JSON(), nullable=True),  # array of runs per inning
        sa.Column('home_first_5_runs', sa.Integer(), nullable =True),  # sum of first 5 innings
        sa.Column('away_first_5_runs', sa.Integer(), nullable=True),  # sum of first 5 innings
        sa.Column('home_remaining_runs', sa.Integer(), nullable=True),  # sum of innings 6+
        sa.Column('away_remaining_runs', sa.Integer(), nullable=True),  # sum of innings 6+
        sa.Column('sdql_game_id', sa.Integer(), unique=True, nullable=True),
        sa.Column('created_date', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('modified_date', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('game_id')
    )


def downgrade() -> None:
    op.drop_table('mlb_games')
