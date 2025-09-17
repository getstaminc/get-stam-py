"""2 add european teams

Revision ID: 775f3bdda1b3
Revises: 795c9b17d5cc
Create Date: 2025-09-16 21:27:17.174006

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '775f3bdda1b3'
down_revision: Union[str, None] = '795c9b17d5cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # List of European teams
    teams = [
        'PSV Eindhoven',
        'Union Saint-Gilloise',
        'Athletic Bilbao',
        'Arsenal',
        'Benfica',
        'Qarabağ FK',
        'Juventus',
        'Borussia Dortmund',
        'Villarreal',
        'Real Madrid',
        'Marseille',
        'Slavia Praha',
        'Bodø/Glimt',
        'Olympiakos Piraeus',
        'Pafos FC',
        'Ajax',
        'Inter Milan',
        'Paris Saint Germain',
        'Atalanta BC',
        'Atlético Madrid',
        'Bayern Munich',
        'Club Brugge',
        'AS Monaco',
        'FC Copenhagen',
        'Bayer Leverkusen',
        'Barcelona',
        'Eintracht Frankfurt',
        'Galatasaray',
        'Sporting Lisbon',
        'FC Kairat',
        'Napoli'
    ]

    # Insert each team into the teams table
    for team_name in teams:
        op.execute(f"INSERT INTO teams (team_name, sport) VALUES ('{team_name}', 'SOCCER')")

def downgrade():
    # List of European teams to remove
    teams = [
        'PSV Eindhoven',
        'Union Saint-Gilloise',
        'Athletic Bilbao',
        'Arsenal',
        'Benfica',
        'Qarabağ FK',
        'Juventus',
        'Borussia Dortmund',
        'Villarreal',
        'Real Madrid',
        'Marseille',
        'Slavia Praha',
        'Bodø/Glimt',
        'Olympiakos Piraeus',
        'Pafos FC',
        'Ajax',
        'Inter Milan',
        'Paris Saint Germain',
        'Atalanta BC',
        'Atlético Madrid',
        'Bayern Munich',
        'Club Brugge',
        'AS Monaco',
        'FC Copenhagen',
        'Bayer Leverkusen',
        'Barcelona',
        'Eintracht Frankfurt',
        'Galatasaray',
        'Sporting Lisbon',
        'FC Kairat',
        'Napoli'
    ]

    # Remove each team from the teams table
    for team_name in teams:
        op.execute(f"DELETE FROM teams WHERE team_name = '{team_name}' AND sport = 'SOCCER'")

