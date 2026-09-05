"""add_odds_event_id_to_nfl_games

Revision ID: a7c2e9f4b1d3
Revises: 9d4e6a1b2c3f
Create Date: 2026-08-10 00:00:00.000000

Mirrors 505d606f158e (same column added to mlb_games) - lays the groundwork
for eventually seeding nfl_games from the Odds API scores endpoint instead of
SportsDatabase/SDQL, same pattern as jobs/mlb_seed_yesterdays_games_odds_api.py.
No seed job changes yet - just the column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a7c2e9f4b1d3'
down_revision: Union[str, None] = '9d4e6a1b2c3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('nfl_games', sa.Column('odds_event_id', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_nfl_games_odds_event_id', 'nfl_games', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_nfl_games_odds_event_id', 'nfl_games', type_='unique')
    op.drop_column('nfl_games', 'odds_event_id')
