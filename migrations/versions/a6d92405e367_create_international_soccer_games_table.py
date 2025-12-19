"""create_international_soccer_games_table

Revision ID: a6d92405e367
Revises: 29c6e86d59ed
Create Date: 2025-12-13 21:21:38.971097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6d92405e367'
down_revision: Union[str, None] = '29c6e86d59ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequence for international_soccer_games
    op.execute("CREATE SEQUENCE IF NOT EXISTS international_soccer_games_game_id_seq")
    
    # Create international_soccer_games table
    op.create_table('international_soccer_games',
        sa.Column('game_id', sa.Integer(), nullable=False, server_default=sa.text("nextval('international_soccer_games_game_id_seq'::regclass)")),
        sa.Column('odds_id', sa.String(length=100), nullable=True),
        sa.Column('league', sa.String(length=100), nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('home_team_id', sa.Integer(), nullable=False),
        sa.Column('away_team_id', sa.Integer(), nullable=False),
        sa.Column('home_team_name', sa.String(length=100), nullable=False),
        sa.Column('away_team_name', sa.String(length=100), nullable=False),
        sa.Column('home_goals', sa.Integer(), nullable=True),
        sa.Column('total_goals', sa.Integer(), nullable=True),
        sa.Column('away_goals', sa.Integer(), nullable=True),
        sa.Column('home_money_line', sa.Integer(), nullable=True),
        sa.Column('draw_money_line', sa.Integer(), nullable=True),
        sa.Column('away_money_line', sa.Integer(), nullable=True),
        sa.Column('home_spread', sa.Float(), nullable=True),
        sa.Column('away_spread', sa.Float(), nullable=True),
        sa.Column('total_over_point', sa.Float(), nullable=True),
        sa.Column('total_over_price', sa.Integer(), nullable=True),
        sa.Column('total_under_point', sa.Float(), nullable=True),
        sa.Column('total_under_price', sa.Integer(), nullable=True),
        sa.Column('home_first_half_goals', sa.Integer(), nullable=True),
        sa.Column('away_first_half_goals', sa.Integer(), nullable=True),
        sa.Column('home_second_half_goals', sa.Integer(), nullable=True),
        sa.Column('away_second_half_goals', sa.Integer(), nullable=True),
        sa.Column('away_overtime', sa.Integer(), nullable=True),
        sa.Column('home_overtime', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('created_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('modified_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['away_team_id'], ['teams.team_id'], name='international_soccer_games_away_team_id_fkey'),
        sa.ForeignKeyConstraint(['home_team_id'], ['teams.team_id'], name='international_soccer_games_home_team_id_fkey'),
        sa.PrimaryKeyConstraint('game_id')
    )


def downgrade() -> None:
    # Drop the table
    op.drop_table('international_soccer_games')
    
    # Drop the sequence
    op.execute("DROP SEQUENCE IF EXISTS international_soccer_games_game_id_seq")
