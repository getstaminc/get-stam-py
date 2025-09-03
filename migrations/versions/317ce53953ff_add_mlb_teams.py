"""add mlb teams

Revision ID: 317ce53953ff
Revises: 3ffdfc45f1c8
Create Date: 2025-08-26 21:31:55.844876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '317ce53953ff'
down_revision: Union[str, None] = '3ffdfc45f1c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # List of MLB teams extracted from the games data
    teams = [
        "Angels", "Astros", "Athletics", "Blue Jays", "Braves", "Brewers", 
        "Cardinals", "Cubs", "Diamondbacks", "Dodgers", "Giants", "Guardians", 
        "Mariners", "Marlins", "Mets", "Nationals", "Orioles", "Padres", 
        "Phillies", "Pirates", "Rangers", "Rays", "Red Sox", "Reds", 
        "Rockies", "Royals", "Tigers", "Twins", "White Sox", "Yankees"
    ]

    # Insert each team into the teams table, skip if already exists
    for team_name in teams:
        op.execute(f"""
            INSERT INTO teams (team_name, sport) 
            VALUES ('{team_name}', 'MLB') 
            ON CONFLICT (team_name) DO NOTHING
        """)


def downgrade() -> None:
    # Remove MLB teams
    op.execute("DELETE FROM teams WHERE sport = 'MLB'")

