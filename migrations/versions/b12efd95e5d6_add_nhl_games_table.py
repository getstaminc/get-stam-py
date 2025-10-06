"""add nhl games table

Revision ID: b12efd95e5d6
Revises: 26d91e9120ce
Create Date: 2025-10-04 14:33:07.445117

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b12efd95e5d6'
down_revision: Union[str, None] = '26d91e9120ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
	op.create_table(
		'nhl_games',
		sa.Column('game_id', sa.Integer(), autoincrement=True, nullable=False),
		sa.Column('game_date', sa.Date(), nullable=False),
		sa.Column('game_site', sa.String(length=100), nullable=False),
		sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
		sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.team_id'), nullable=False),
		sa.Column('home_team_name', sa.String(length=100), nullable=False),
		sa.Column('away_team_name', sa.String(length=100), nullable=False),
		sa.Column('home_goals', sa.Integer(), nullable=False),
		sa.Column('away_goals', sa.Integer(), nullable=False),
		sa.Column('home_money_line', sa.Float(), nullable=True),
		sa.Column('away_money_line', sa.Float(), nullable=True),
		sa.Column('home_period_goals', sa.ARRAY(sa.Integer()), nullable=True),
		sa.Column('away_period_goals', sa.ARRAY(sa.Integer()), nullable=True),
		sa.Column('home_starting_goalie', sa.String(length=100), nullable=True),
		sa.Column('away_starting_goalie', sa.String(length=100), nullable=True),
		sa.Column('home_powerplay_goals', sa.Integer(), nullable=True),
		sa.Column('away_powerplay_goals', sa.Integer(), nullable=True),
		sa.Column('total', sa.Float(), nullable=True),
		sa.Column('overtime', sa.Boolean(), nullable=True),
		sa.Column('shoot_out', sa.Boolean(), nullable=True),
		sa.Column('playoffs', sa.Boolean(), nullable=True),
		sa.Column('sdql_game_id', sa.Integer(), unique=True, nullable=True),
		sa.Column('created_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.Column('modified_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.PrimaryKeyConstraint('game_id')
	)

def downgrade() -> None:
	op.drop_table('nhl_games')


