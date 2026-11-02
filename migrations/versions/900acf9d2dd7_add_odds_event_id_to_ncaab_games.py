"""add_odds_event_id_to_ncaab_games

Mirrors fd711e7e2b11 (nba_games_1), a7c2e9f4b1d3 (nfl_games), and
11c35d14cecd (ncaaf_games) - lays the groundwork for seeding ncaab_games
from the Odds API scores endpoint instead of SportsDatabase/SDQL.

Revision ID: 900acf9d2dd7
Revises: 11c35d14cecd
Create Date: 2026-11-02 06:25:22.791770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '900acf9d2dd7'
down_revision: Union[str, None] = '11c35d14cecd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ncaab_games', sa.Column('odds_event_id', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_ncaab_games_odds_event_id', 'ncaab_games', ['odds_event_id'])


def downgrade() -> None:
    op.drop_constraint('uq_ncaab_games_odds_event_id', 'ncaab_games', type_='unique')
    op.drop_column('ncaab_games', 'odds_event_id')
