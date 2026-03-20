"""fix mlb player props unique constraint to include player_type

Revision ID: b05ffab770c7
Revises: 7373be475d89
Create Date: 2026-03-08 21:51:09.714942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b05ffab770c7'
down_revision: Union[str, None] = '7373be475d89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_mlb_player_props_player_odds_event', 'mlb_player_props', type_='unique')
    op.create_unique_constraint(
        'uq_mlb_player_props_player_odds_event',
        'mlb_player_props',
        ['player_id', 'odds_event_id', 'player_type']
    )


def downgrade() -> None:
    op.drop_constraint('uq_mlb_player_props_player_odds_event', 'mlb_player_props', type_='unique')
    op.create_unique_constraint(
        'uq_mlb_player_props_player_odds_event',
        'mlb_player_props',
        ['player_id', 'odds_event_id']
    )
