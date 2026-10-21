"""add_odds_event_id_to_nhl_games

Revision ID: a1e8f3c92b47
Revises: 689b5984c18e
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1e8f3c92b47'
down_revision: Union[str, None] = '689b5984c18e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('nhl_games', sa.Column('odds_event_id', sa.String(100), nullable=True))
    op.create_unique_constraint('uq_nhl_games_odds_event_id', 'nhl_games', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_nhl_games_odds_event_id', 'nhl_games', type_='unique')
    op.drop_column('nhl_games', 'odds_event_id')
