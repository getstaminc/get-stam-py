"""Insert NBA teams into teams table

Revision ID: <new_revision_id>
Revises: d43083648ae1
Create Date: 2025-04-07 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '<new_revision_id>'
down_revision = 'd43083648ae1'
branch_labels = None
depends_on = None


def upgrade():
    # List of NBA teams
    teams = [
        'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets',
        'Chicago Bulls', 'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets',
        'Detroit Pistons', 'Golden State Warriors', 'Houston Rockets', 'Indiana Pacers',
        'Los Angeles Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies', 'Miami Heat',
        'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans',
        'New York Knicks', 'Oklahoma City Thunder', 'Orlando Magic', 'Philadelphia 76ers',
        'Phoenix Suns', 'Portland Trail Blazers', 'Sacramento Kings', 'San Antonio Spurs',
        'Toronto Raptors', 'Utah Jazz', 'Washington Wizards'
    ]

    # Insert teams into the teams table
    for team_name in teams:
        op.execute(
            f"INSERT INTO teams (team_name, sport) VALUES ('{team_name}', 'NBA')"
        )


def downgrade():
    # List of NBA teams
    teams = [
        'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets',
        'Chicago Bulls', 'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets',
        'Detroit Pistons', 'Golden State Warriors', 'Houston Rockets', 'Indiana Pacers',
        'Los Angeles Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies', 'Miami Heat',
        'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans',
        'New York Knicks', 'Oklahoma City Thunder', 'Orlando Magic', 'Philadelphia 76ers',
        'Phoenix Suns', 'Portland Trail Blazers', 'Sacramento Kings', 'San Antonio Spurs',
        'Toronto Raptors', 'Utah Jazz', 'Washington Wizards'
    ]

    # Remove teams from the teams table
    for team_name in teams:
        op.execute(
            f"DELETE FROM teams WHERE team_name = '{team_name}'"
        )