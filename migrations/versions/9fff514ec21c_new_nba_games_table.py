"""new nba games table

Revision ID: 9fff514ec21c
Revises: fdfb3430afb2
Create Date: 2025-10-28 13:18:56.923583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fff514ec21c'
down_revision: Union[str, None] = 'fdfb3430afb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create sequence used by game_id (dedicated to nba_games_1 to avoid collisions)
    op.execute("CREATE SEQUENCE IF NOT EXISTS nba_games_1_game_id_seq;")

    op.create_table(
    'nba_games_1',
    sa.Column('game_id', sa.Integer(), nullable=False, server_default=sa.text("nextval('nba_games_1_game_id_seq'::regclass)")),
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
    sa.ForeignKeyConstraint(['home_team_id'], ['teams.team_id'], name='nba_games_1_home_team_id_fkey'),
    sa.ForeignKeyConstraint(['away_team_id'], ['teams.team_id'], name='nba_games_1_away_team_id_fkey'),
        sa.PrimaryKeyConstraint('game_id'),
    )

    # unique index on sdql_game_id (create only if it doesn't already exist)
    conn = op.get_bind()
    exists = conn.execute(sa.text("SELECT to_regclass('public.nba_games_1_sdql_game_id_key')")).scalar()
    if not exists:
        # create the index on the table we just created (nba_games_1) with a unique name
        op.create_index('nba_games_1_sdql_game_id_key', 'nba_games_1', ['sdql_game_id'], unique=True)


def downgrade() -> None:
    # drop index (only if exists), table and sequence
    conn = op.get_bind()
    # If index exists and is attached to nba_games_1, drop it. Do NOT drop
    # an index that belongs to another table (e.g. an existing `nba_games`).
    idx_table = conn.execute(
        sa.text("SELECT tablename FROM pg_indexes WHERE indexname = :name"),
        {"name": "nba_games_1_sdql_game_id_key"}
    ).scalar()

    if idx_table == 'nba_games_1':
        try:
            op.drop_index('nba_games_1_sdql_game_id_key', table_name='nba_games_1')
        except Exception:
            # best-effort: if op.drop_index fails, try raw DROP INDEX on that specific name
            try:
                conn.execute(sa.text("DROP INDEX IF EXISTS public.nba_games_1_sdql_game_id_key"))
            except Exception:
                pass
    elif idx_table is not None:
        # index exists but not on our newly-created table; leave it alone to avoid
        # impacting other tables
        print(f"[alembic] leaving existing index nba_games_1_sdql_game_id_key on table {idx_table}")

    # drop the table we created earlier
    op.drop_table('nba_games_1')

    # sequence is safe to drop if exists, but only if no other table depends on it.
    # Check information_schema for any column defaults referencing the sequence.
    seq_deps = conn.execute(sa.text(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE column_default LIKE :seq_name
        """
    ), {"seq_name": "%nba_games_1_game_id_seq%"}).fetchall()

    # Filter out the table we created in this migration (nba_games_1).
    other_deps = [r for r in seq_deps if r[0] != 'nba_games_1']

    if other_deps:
        # There are other tables that depend on this sequence. Do not drop it.
        print(f"[alembic] not dropping sequence nba_games_1_game_id_seq; dependent objects found: {other_deps}")
    else:
        # safe to drop our dedicated sequence
        op.execute("DROP SEQUENCE IF EXISTS nba_games_1_game_id_seq;")
