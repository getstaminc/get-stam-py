"""Insert NFL teams into teams table

Revision ID: 72aa2fceef5e
Revises: 5aaa9bf7a2fa
Create Date: 2025-05-27 21:20:36.526202

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72aa2fceef5e'
down_revision: Union[str, None] = '5aaa9bf7a2fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # List of NFL teams extracted from the games data
    teams = [
        'Colts', 'Texans', 'Ravens', 'Steelers', 'Bengals', 'Browns', 'Cardinals', 'Seahawks',
        'Chargers', 'Chiefs', 'Commanders', 'Cowboys', 'Dolphins', 'Bills', 'Fortyniners', 'Rams',
        'Giants', 'Eagles', 'Lions', 'Vikings', 'Packers', 'Bears', 'Panthers', 'Buccaneers',
        'Patriots', 'Jets', 'Raiders', 'Broncos', 'Saints', 'Falcons', 'Titans', 'Jaguars'
    ]

    # Insert each team into the teams table
    for team_name in teams:
        op.execute(f"INSERT INTO teams (team_name, sport) VALUES ('{team_name}', 'NFL')")


def downgrade():
    # List of NFL teams to remove
    teams = [
        'Colts', 'Texans', 'Ravens', 'Steelers', 'Bengals', 'Browns', 'Cardinals', 'Seahawks',
        'Chargers', 'Chiefs', 'Commanders', 'Cowboys', 'Dolphins', 'Bills', 'Fortyniners', 'Rams',
        'Giants', 'Eagles', 'Lions', 'Vikings', 'Packers', 'Bears', 'Panthers', 'Buccaneers',
        'Patriots', 'Jets', 'Raiders', 'Broncos', 'Saints', 'Falcons', 'Titans', 'Jaguars'
    ]

    # Remove each team from the teams table
    for team_name in teams:
        op.execute(f"DELETE FROM teams WHERE team_name = '{team_name}'")
