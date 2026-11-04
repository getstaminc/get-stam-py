"""add_odds_event_id_to_nba_games_1

Revision ID: fd711e7e2b11
Revises: 9d14f3a7c2e8
Create Date: 2026-10-31 15:29:24.867171

Mirrors a7c2e9f4b1d3 (same column added to nfl_games) and 505d606f158e
(mlb_games) - lays the groundwork for seeding nba_games_1 from the Odds API
scores endpoint instead of SportsDatabase/SDQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd711e7e2b11'
down_revision: Union[str, None] = '9d14f3a7c2e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('nba_games_1', sa.Column('odds_event_id', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_nba_games_1_odds_event_id', 'nba_games_1', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_nba_games_1_odds_event_id', 'nba_games_1', type_='unique')
    op.drop_column('nba_games_1', 'odds_event_id')
