"""Fix NBA team names in teams table

Revision ID: <new_revision_id>
Revises: 550f6543b0ab
Create Date: 2025-04-07 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '550f6543b0ab'
down_revision = '550f6543b0ab'
branch_labels = None
depends_on = None


def upgrade():
    # Delete all existing rows in the teams table
    op.execute("DELETE FROM teams")

    # Insert the correct team names
    teams = [
        'Bucks', 'Bulls', 'Cavaliers', 'Celtics', 'Clippers', 'Grizzlies',
        'Hawks', 'Heat', 'Hornets', 'Jazz', 'Kings', 'Knicks', 'Lakers',
        'Magic', 'Mavericks', 'Nets', 'Pelicans', 'Pistons', 'Raptors',
        'Rockets', 'Seventysixers', 'Spurs', 'Suns', 'Thunder', 'Timberwolves',
        'Trailblazers', 'Warriors', 'Wizards'
    ]

    for team_name in teams:
        op.execute(
            f"INSERT INTO teams (team_name, sport) VALUES ('{team_name}', 'NBA')"
        )


def downgrade():
    # Delete all rows in the teams table
    op.execute("DELETE FROM teams")