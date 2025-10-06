"""add nhl teams

Revision ID: 26d91e9120ce
Revises: 775f3bdda1b3
Create Date: 2025-10-03 21:35:43.260206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26d91e9120ce'
down_revision: Union[str, None] = '775f3bdda1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # List of NHL teams extracted from the games data
    teams = [
        "Avalanche",
        "Sabres",
        "Blue Jackets",
        "Red Wings",
        "Capitals",
        "Wild",
        "Flames",
        "Islanders",
        "Maple Leafs",
        "Jets",
        "Ducks",
        "Knights",
        "Flyers",
        "Kraken",
        "Canucks",
        "Panthers",
        "Hurricanes",
        "Rangers",
        "Bruins",
        "Sharks",
        "Lightning",
        "Stars",
        "Senators",
        "Blackhawks",
        "Blues",
        "Predators",
        "Oilers",
        "Penguins",
        "Kings",
        "Devils",
        "Mammoth"
    ]

    # Insert each team into the teams table, skip if already exists
    for team_name in teams:
        op.execute(f"""
            INSERT INTO teams (team_name, sport) 
            VALUES ('{team_name}', 'NHL') 
            ON CONFLICT (team_name, sport) DO NOTHING
        """)


def downgrade() -> None:
    pass
