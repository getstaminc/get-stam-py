"""add_odds_event_id_to_mlb_games

Revision ID: 505d606f158e
Revises: a1b2c3d4e5f6
Create Date: 2026-04-02 21:12:52.993263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '505d606f158e'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mlb_games', sa.Column('odds_event_id', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_mlb_games_odds_event_id', 'mlb_games', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_mlb_games_odds_event_id', 'mlb_games', type_='unique')
    op.drop_column('mlb_games', 'odds_event_id')
