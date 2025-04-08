"""Create nba_games table"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = 'f58aaeaf3ed3'
down_revision = '8d200c5054dd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'nba_games',
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
    pass