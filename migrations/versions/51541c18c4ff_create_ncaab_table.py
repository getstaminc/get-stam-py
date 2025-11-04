"""create ncaab table

Revision ID: 51541c18c4ff
Revises: 9f9c537c56f3
Create Date: 2025-10-31 21:27:29.048222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51541c18c4ff'
down_revision: Union[str, None] = '9f9c537c56f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a dedicated sequence for ncaab_games primary key to avoid collisions
    op.execute("CREATE SEQUENCE IF NOT EXISTS ncaab_games_game_id_seq;")

    op.create_table(
        'ncaab_games',
        sa.Column('game_id', sa.Integer(), nullable=False, server_default=sa.text("nextval('ncaab_games_game_id_seq'::regclass)")),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('game_site', sa.String(length=10), nullable=False),
        sa.Column('home_team_id', sa.Integer(), nullable=False),
        sa.Column('away_team_id', sa.Integer(), nullable=False),
        sa.Column('home_team_name', sa.String(length=100), nullable=False),
        sa.Column('away_team_name', sa.String(length=100), nullable=False),
        sa.Column('home_points', sa.Integer(), nullable=False),
        sa.Column('away_points', sa.Integer(), nullable=False),
        sa.Column('total_points', sa.Float(), nullable=True),
        sa.Column('total_margin', sa.Float(), nullable=True),
        sa.Column('home_line', sa.Float(), nullable=True),
        sa.Column('away_line', sa.Float(), nullable=True),
        sa.Column('home_quarter_scores', sa.JSON(), nullable=True),
        sa.Column('away_quarter_scores', sa.JSON(), nullable=True),
        sa.Column('home_first_half_points', sa.Integer(), nullable=True),
        sa.Column('away_first_half_points', sa.Integer(), nullable=True),
        sa.Column('home_second_half_points', sa.Integer(), nullable=True),
        sa.Column('away_second_half_points', sa.Integer(), nullable=True),
        sa.Column('home_overtime_points', sa.Integer(), nullable=True),
        sa.Column('away_overtime_points', sa.Integer(), nullable=True),
        sa.Column('home_money_line', sa.Integer(), nullable=True),
        sa.Column('away_money_line', sa.Integer(), nullable=True),
        sa.Column('playoffs', sa.Boolean(), nullable=True),
        sa.Column('sdql_game_id', sa.Integer(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('created_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('modified_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['home_team_id'], ['teams.team_id'], name='ncaab_games_home_team_id_fkey'),
        sa.ForeignKeyConstraint(['away_team_id'], ['teams.team_id'], name='ncaab_games_away_team_id_fkey'),
        sa.PrimaryKeyConstraint('game_id'),
    )

    # Create unique index on sdql_game_id if it doesn't already exist
    conn = op.get_bind()
    exists = conn.execute(sa.text("SELECT to_regclass('public.ncaab_games_sdql_game_id_key')")).scalar()
    if not exists:
        op.create_index('ncaab_games_sdql_game_id_key', 'ncaab_games', ['sdql_game_id'], unique=True)


def downgrade() -> None:
    conn = op.get_bind()

    # If index exists and is attached to ncaab_games, drop it. Do NOT drop an index that belongs to another table.
    idx_table = conn.execute(
        sa.text("SELECT tablename FROM pg_indexes WHERE indexname = :name"),
        {"name": "ncaab_games_sdql_game_id_key"}
    ).scalar()

    if idx_table == 'ncaab_games':
        try:
            op.drop_index('ncaab_games_sdql_game_id_key', table_name='ncaab_games')
        except Exception:
            try:
                conn.execute(sa.text("DROP INDEX IF EXISTS public.ncaab_games_sdql_game_id_key"))
            except Exception:
                pass
    elif idx_table is not None:
        print(f"[alembic] leaving existing index ncaab_games_sdql_game_id_key on table {idx_table}")

    # Drop the ncaab_games table
    op.drop_table('ncaab_games')

    # Drop the sequence if no other objects depend on it
    seq_deps = conn.execute(sa.text(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE column_default LIKE :seq_name
        """
    ), {"seq_name": "%ncaab_games_game_id_seq%"}).fetchall()

    other_deps = [r for r in seq_deps if r[0] != 'ncaab_games']
    if other_deps:
        print(f"[alembic] not dropping sequence ncaab_games_game_id_seq; dependent objects found: {other_deps}")
    else:
        op.execute("DROP SEQUENCE IF EXISTS ncaab_games_game_id_seq;")
