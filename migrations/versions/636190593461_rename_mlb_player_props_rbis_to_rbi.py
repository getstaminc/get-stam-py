"""rename mlb player props rbis to rbi

Revision ID: 636190593461
Revises: b05ffab770c7
Create Date: 2026-03-09 15:31:16.522630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '636190593461'
down_revision: Union[str, None] = 'b05ffab770c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('mlb_player_props', 'odds_batter_rbis', new_column_name='odds_batter_rbi')
    op.alter_column('mlb_player_props', 'odds_batter_rbis_over_price', new_column_name='odds_batter_rbi_over_price')
    op.alter_column('mlb_player_props', 'odds_batter_rbis_under_price', new_column_name='odds_batter_rbi_under_price')
    op.alter_column('mlb_player_props', 'actual_batter_rbis', new_column_name='actual_batter_rbi')


def downgrade() -> None:
    op.alter_column('mlb_player_props', 'odds_batter_rbi', new_column_name='odds_batter_rbis')
    op.alter_column('mlb_player_props', 'odds_batter_rbi_over_price', new_column_name='odds_batter_rbis_over_price')
    op.alter_column('mlb_player_props', 'odds_batter_rbi_under_price', new_column_name='odds_batter_rbis_under_price')
    op.alter_column('mlb_player_props', 'actual_batter_rbi', new_column_name='actual_batter_rbis')
