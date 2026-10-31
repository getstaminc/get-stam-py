"""widen_nba_games_1_total_to_float

nba_games_1.total was Integer, silently rounding Odds API's half-point NBA
totals (e.g. 222.5 -> 222) on every insert -- confirmed 509 of 15,037 existing
rows (3.38%) have home_points + away_points == total exactly, which almost
certainly means they're misclassified as a trend "push" when the real game
(with its original .5 total) was an over or under, since half-point totals
can't push by design. Widening to Float (matching nfl_games/mlb_games/
nhl_games, which MLB's own migration comment says NBA was meant to match
from the start) fixes this going forward; a separate backfill of 2020-present
rows is being scoped as its own follow-up, not part of this migration.

Revision ID: 445848ace83f
Revises: fd711e7e2b11
Create Date: 2026-10-31 16:05:20.051074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '445848ace83f'
down_revision: Union[str, None] = 'fd711e7e2b11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('nba_games_1', 'total', type_=sa.Float(), existing_type=sa.Integer())


def downgrade() -> None:
    op.alter_column('nba_games_1', 'total', type_=sa.Integer(), existing_type=sa.Float())
