"""add international_soccer_teams

Revision ID: b460d3e1ede4
Revises: a6d92405e367
Create Date: 2025-12-17 21:09:50.115079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b460d3e1ede4'
down_revision: Union[str, None] = 'a6d92405e367'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # List of African national teams
    teams = [
        'Algeria',
        'Angola',
        'Benin',
        'Botswana',
        'Burkina Faso',
        'Cameroon',
        'Comoros',
        'DR Congo',
        'Egypt',
        'Equatorial Guinea',
        'Gabon',
        'Ivory Coast',
        'Mali',
        'Morocco',
        'Mozambique',
        'Nigeria',
        'Senegal',
        'South Africa',
        'Sudan',
        'Tanzania',
        'Tunisia',
        'Uganda',
        'Zambia',
        'Zimbabwe'
    ]

    # Insert each team into the teams table
    for team_name in teams:
        op.execute(f"INSERT INTO teams (team_name, sport) VALUES ('{team_name}', 'INTL_SOCCER')")

def downgrade():
    # List of African national teams to remove
    teams = [
        'Algeria',
        'Angola',
        'Benin',
        'Botswana',
        'Burkina Faso',
        'Cameroon',
        'Comoros',
        'DR Congo',
        'Egypt',
        'Equatorial Guinea',
        'Gabon',
        'Ivory Coast',
        'Mali',
        'Morocco',
        'Mozambique',
        'Nigeria',
        'Senegal',
        'South Africa',
        'Sudan',
        'Tanzania',
        'Tunisia',
        'Uganda',
        'Zambia',
        'Zimbabwe'
    ]

    # Remove each team from the teams table
    for team_name in teams:
        op.execute(f"DELETE FROM teams WHERE team_name = '{team_name}' AND sport = 'INTL_SOCCER'")
