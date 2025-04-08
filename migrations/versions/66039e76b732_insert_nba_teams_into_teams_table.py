"""Insert NBA teams into teams table

Revision ID: 66039e76b732
Revises: f58aaeaf3ed3
Create Date: 2025-04-08 12:31:24.442358

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66039e76b732'
down_revision: Union[str, None] = 'f58aaeaf3ed3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # List of NBA teams
    teams = [
        'Bucks', 'Bulls', 'Cavaliers', 'Celtics', 'Clippers', 'Grizzlies',
        'Hawks', 'Heat', 'Hornets', 'Jazz', 'Kings', 'Knicks', 'Lakers',
        'Magic', 'Mavericks', 'Nets', 'Pelicans', 'Pistons', 'Raptors',
        'Rockets', 'Seventysixers', 'Spurs', 'Suns', 'Thunder', 'Timberwolves',
        'Trailblazers', 'Warriors', 'Wizards'
    ]

    # Insert each team into the teams table
    for team_name in teams:
        op.execute(f"INSERT INTO teams (team_name, sport) VALUES ('{team_name}', 'NBA')")


def downgrade():
    # List of NBA teams
    teams = [
        'Bucks', 'Bulls', 'Cavaliers', 'Celtics', 'Clippers', 'Grizzlies',
        'Hawks', 'Heat', 'Hornets', 'Jazz', 'Kings', 'Knicks', 'Lakers',
        'Magic', 'Mavericks', 'Nets', 'Pelicans', 'Pistons', 'Raptors',
        'Rockets', 'Seventysixers', 'Spurs', 'Suns', 'Thunder', 'Timberwolves',
        'Trailblazers', 'Warriors', 'Wizards'
    ]

    # Remove each team from the teams table
    for team_name in teams:
        op.execute(f"DELETE FROM teams WHERE team_name = '{team_name}'")
