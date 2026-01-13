"""add espon_team_id column

Revision ID: db7462da32c7
Revises: 7c55f14ab5ec
Create Date: 2026-01-07 10:27:17.754853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db7462da32c7'
down_revision: Union[str, None] = '7c55f14ab5ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add espn_team_id column to teams table
    op.add_column('teams', sa.Column('espn_team_id', sa.String(10), nullable=True))
    
    # Add unique constraint for ESPN ID per sport (where not null)
    op.create_index(
        'ix_teams_espn_id_sport', 
        'teams', 
        ['espn_team_id', 'sport'], 
        unique=True,
        postgresql_where=sa.text('espn_team_id IS NOT NULL')
    )
    
    print("Added espn_team_id column to teams table")


def downgrade() -> None:
    # Remove the unique index first
    op.drop_index('ix_teams_espn_id_sport', 'teams')
    
    # Remove the espn_team_id column
    op.drop_column('teams', 'espn_team_id')
    
    print("Removed espn_team_id column from teams table")
