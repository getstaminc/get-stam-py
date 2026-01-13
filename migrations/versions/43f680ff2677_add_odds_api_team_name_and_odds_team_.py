"""add odds_api_team_name and odds_team and home_team

Revision ID: 43f680ff2677
Revises: 78943f2d1ad8
Create Date: 2026-01-12 21:05:37.684242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43f680ff2677'
down_revision: Union[str, None] = '78943f2d1ad8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add odds_api_team_name to teams table for matching Odds API team names
    op.add_column('teams', sa.Column('odds_api_team_name', sa.String(100), nullable=True))
    
    # Add odds team columns to nba_player_props for fuzzy matching verification
    op.add_column('nba_player_props', sa.Column('odds_home_team', sa.String(100), nullable=True))
    op.add_column('nba_player_props', sa.Column('odds_away_team', sa.String(100), nullable=True))


def downgrade() -> None:
    # Remove odds team columns from nba_player_props
    op.drop_column('nba_player_props', 'odds_away_team')
    op.drop_column('nba_player_props', 'odds_home_team')
    
    # Remove odds_api_team_name from teams
    op.drop_column('teams', 'odds_api_team_name')
