"""widen_ncaab_games_total_to_float

ncaab_games.total was Integer, silently rounding Odds API's/SDQL's half-point
NCAAB totals (e.g. 147.5 -> 148) on every insert -- confirmed 1,383 of 57,784
existing rows (2.39%) have home_points + away_points == total exactly, which
almost certainly means they're misclassified as a trend "push" when the real
total (with its original .5) was an over or under, since half-point totals
can't push by design. Same bug class already fixed for nba_games_1
(445848ace83f), just discovered again during the final whole-branch review of
this migration's own job 2 fix. Widening to Float; a historical backfill is a
separate follow-up, not part of this migration.

Revision ID: 1a457cb4b044
Revises: 900acf9d2dd7
Create Date: 2026-11-02 08:53:50.340502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a457cb4b044'
down_revision: Union[str, None] = '900acf9d2dd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('ncaab_games', 'total', type_=sa.Float(), existing_type=sa.Integer())


def downgrade() -> None:
    op.alter_column('ncaab_games', 'total', type_=sa.Integer(), existing_type=sa.Float())
