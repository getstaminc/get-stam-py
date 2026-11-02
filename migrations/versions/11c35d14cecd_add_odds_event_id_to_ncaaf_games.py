"""add_odds_event_id_to_ncaaf_games

Mirrors fd711e7e2b11 (same column added to nba_games_1) and a7c2e9f4b1d3
(nfl_games) - lays the groundwork for seeding ncaaf_games from the Odds API
scores endpoint instead of SportsDatabase/SDQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11c35d14cecd'
down_revision: Union[str, None] = '445848ace83f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ncaaf_games', sa.Column('odds_event_id', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_ncaaf_games_odds_event_id', 'ncaaf_games', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_ncaaf_games_odds_event_id', 'ncaaf_games', type_='unique')
    op.drop_column('ncaaf_games', 'odds_event_id')
