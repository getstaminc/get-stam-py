"""Add missing NBA teams

Revision ID: c584ec6c7ac4
Revises: 66039e76b732
Create Date: 2025-04-08 15:40:13.633091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c584ec6c7ac4'
down_revision: Union[str, None] = '66039e76b732'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert the missing teams
    op.execute("INSERT INTO teams (team_name, sport) VALUES ('Nuggets', 'NBA')")
    op.execute("INSERT INTO teams (team_name, sport) VALUES ('Pacers', 'NBA')")


def downgrade():
    # Remove the missing teams
    op.execute("DELETE FROM teams WHERE team_name = 'Nuggets'")
    op.execute("DELETE FROM teams WHERE team_name = 'Pacers'")
