"""add german team names

Revision ID: 681e4f9087cc
Revises: ffb8370e86bd
Create Date: 2025-10-27 14:08:43.079579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '681e4f9087cc'
down_revision: Union[str, None] = 'ffb8370e86bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    teams = [
        "Augsburg",
        "Bayern Munich",
        "Arminia Bielefeld",
        "VfL Bochum",
        "Eintracht Braunschweig",
        "SV Darmstadt 98",
        "Borussia Dortmund",
        "Eintracht Frankfurt",
        "1. FC Köln",
        "Fortuna Düsseldorf",
        "SC Freiburg",
        "Greuther Fürth",
        "Hamburger SV",
        "Hannover 96",
        "1. FC Heidenheim",
        "Hertha Berlin",
        "TSG Hoffenheim",
        "Holstein Kiel",
        "FC Ingolstadt 04",
        "1. FC Kaiserslautern",
        "Bayer Leverkusen",
        "Borussia Monchengladbach",
        "FSV Mainz 05",
        "1. FC Nürnberg",
        "SC Paderborn",
        "RB Leipzig",
        "FC Schalke 04",
        "FC St. Pauli",
        "VfB Stuttgart",
        "Union Berlin",
        "Werder Bremen",
        "VfL Wolfsburg"
    ]

    bind = op.get_bind()
    for team_name in teams:
        # Use Postgres upsert semantics to avoid failing if a team already exists
        bind.execute(
            sa.text(
                "INSERT INTO teams (team_name, sport) VALUES (:name, :sport) "
                "ON CONFLICT (team_name, sport) DO NOTHING"
            ).bindparams(name=team_name, sport="SOCCER")
        )


def downgrade() -> None:
    teams = [
        "Augsburg",
        "Bayern Munich",
        "Arminia Bielefeld",
        "VfL Bochum",
        "Eintracht Braunschweig",
        "SV Darmstadt 98",
        "Borussia Dortmund",
        "Eintracht Frankfurt",
        "1. FC Köln",
        "Fortuna Düsseldorf",
        "SC Freiburg",
        "Greuther Fürth",
        "Hamburger SV",
        "Hannover 96",
        "1. FC Heidenheim",
        "Hertha Berlin",
        "TSG Hoffenheim",
        "Holstein Kiel",
        "FC Ingolstadt 04",
        "1. FC Kaiserslautern",
        "Bayer Leverkusen",
        "Borussia Monchengladbach",
        "FSV Mainz 05",
        "1. FC Nürnberg",
        "SC Paderborn",
        "RB Leipzig",
        "FC Schalke 04",
        "FC St. Pauli",
        "VfB Stuttgart",
        "Union Berlin",
        "Werder Bremen",
        "VfL Wolfsburg"
    ]

    bind = op.get_bind()
    for team_name in teams:
        bind.execute(
            sa.text("DELETE FROM teams WHERE team_name = :name AND sport = :sport")
            .bindparams(name=team_name, sport="SOCCER")
        )
