"""add odds team id columns to nba player props

Revision ID: 989844439625
Revises: 2c466c7f5577
Create Date: 2026-01-12 21:39:06.450955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '989844439625'
down_revision: Union[str, None] = '2c466c7f5577'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add team ID columns to nba_player_props
    op.add_column('nba_player_props', sa.Column('odds_home_team_id', sa.Integer(), nullable=True))
    op.add_column('nba_player_props', sa.Column('odds_away_team_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraints to teams table
    op.create_foreign_key(
        'fk_nba_player_props_odds_home_team',
        'nba_player_props', 'teams',
        ['odds_home_team_id'], ['team_id']
    )
    op.create_foreign_key(
        'fk_nba_player_props_odds_away_team',
        'nba_player_props', 'teams',
        ['odds_away_team_id'], ['team_id']
    )


def downgrade() -> None:
    # Drop foreign key constraints
    op.drop_constraint('fk_nba_player_props_odds_away_team', 'nba_player_props', type_='foreignkey')
    op.drop_constraint('fk_nba_player_props_odds_home_team', 'nba_player_props', type_='foreignkey')
    
    # Drop columns
    op.drop_column('nba_player_props', 'odds_away_team_id')
    op.drop_column('nba_player_props', 'odds_home_team_id')
