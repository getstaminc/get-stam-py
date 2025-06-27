"""add epl teams

Revision ID: ff9d10eea272
Revises: 8c6e7038bfcb
Create Date: 2025-06-26 20:42:44.056729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff9d10eea272'
down_revision: Union[str, None] = '8c6e7038bfcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # List of EPL teams
    teams = [
        'Arsenal',
        'Aston Villa',
        'Birmingham City',
        'Blackburn',
        'Bolton',
        'Bournemouth',
        'Brentford',
        'Brighton and Hove Albion',
        'Burnley',
        'Cardiff City',
        'Chelsea',
        'Crystal Palace',
        'Everton',
        'Fulham',
        'Huddersfield Town',
        'Hull City',
        'Ipswich Town',
        'Leeds United',
        'Leicester City',
        'Liverpool',
        'Luton',
        'Manchester City',
        'Manchester United',
        'Middlesbrough',
        'Newcastle United',
        'Norwich City',
        'Nottingham Forest',
        'Queens Park Rangers',
        'Reading',
        'Sheffield United',
        'Southampton',
        'Stoke City',
        'Sunderland',
        'Swansea City',
        'Tottenham Hotspur',
        'Watford',
        'West Bromwich Albion',
        'West Ham United',
        'Wigan Athletic',
        'Wolverhampton Wanderers'
    ]

    # Insert each team into the teams table
    for team_name in teams:
        op.execute(f"INSERT INTO teams (team_name, sport) VALUES ('{team_name}', 'EPL')")

def downgrade():
    # List of EPL teams to remove
    teams = [
        'Arsenal',
        'Aston Villa',
        'Birmingham City',
        'Blackpool',
        'Bolton',
        'Bournemouth',
        'Brentford',
        'Brighton and Hove Albion',
        'Burnley',
        'Cardiff City',
        'Chelsea',
        'Crystal Palace',
        'Everton',
        'Fulham',
        'Huddersfield Town',
        'Hull City',
        'Ipswich Town',
        'Leeds United',
        'Leicester City',
        'Liverpool',
        'Luton',
        'Manchester City',
        'Manchester United',
        'Middlesbrough',
        'Newcastle United',
        'Norwich City',
        'Nottingham Forest',
        'Queens Park Rangers',
        'Reading',
        'Sheffield United',
        'Southampton',
        'Stoke City',
        'Sunderland',
        'Swansea City',
        'Tottenham Hotspur',
        'Watford',
        'West Bromwich Albion',
        'West Ham United',
        'Wigan Athletic',
        'Wolverhampton Wanderers'
    ]

    # Remove each team from the teams table
    for team_name in teams:
        op.execute(f"DELETE FROM teams WHERE team_name = '{team_name}' AND sport = 'EPL'")
