"""Update nba_games table: rename quarter_scores and add away_quarter_scores

Revision ID: 0d53b6f42a64
Revises: c584ec6c7ac4
Create Date: 2025-04-08 20:44:19.553120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d53b6f42a64'
down_revision: Union[str, None] = 'c584ec6c7ac4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename quarter_scores to home_quarter_scores
    op.alter_column('nba_games', 'quarter_scores', new_column_name='home_quarter_scores')

    # Add away_quarter_scores column
    op.add_column('nba_games', sa.Column('away_quarter_scores', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Revert away_quarter_scores column
    op.drop_column('nba_games', 'away_quarter_scores')

    # Rename home_quarter_scores back to quarter_scores
    op.alter_column('nba_games', 'home_quarter_scores', new_column_name='quarter_scores')