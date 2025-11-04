"""add spanish games

Revision ID: 93cd539532d8
Revises: 651f58c7c1dd
Create Date: 2025-11-03 20:51:20.367906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93cd539532d8'
down_revision: Union[str, None] = '651f58c7c1dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    teams = [
        "Alavés",
        "Almería",
        "Athletic Bilbao",
        "Atlético Madrid",
        "Barcelona",
        "Real Betis",
        "Cádiz CF",
        "Celta Vigo",
        "Córdoba",
        "SD Eibar",
        "Elche CF",
        "Espanyol",
        "Getafe",
        "Girona",
        "Granada CF",
        "Hercules CF",
        "SD Huesca",
        "Deportivo La Coruña",
        "Las Palmas",
        "Leganés",
        "Levante",
        "Málaga",
        "Mallorca",
        "CA Osasuna",
        "Oviedo",
        "Real Madrid",
        "Real Racing Club de Santander",
        "Sevilla",
        "Real Sociedad",
        "Sporting Gijón",
        "Valencia",
        "Real Valladolid CF",
        "Rayo Vallecano",
        "Villarreal",
        "Zaragoza",
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
        "Alavés",
        "Almería",
        "Athletic Bilbao",
        "Atlético Madrid",
        "Barcelona",
        "Real Betis",
        "Cádiz CF",
        "Celta Vigo",
        "Córdoba",
        "SD Eibar",
        "Elche CF",
        "Espanyol",
        "Getafe",
        "Girona",
        "Granada CF",
        "Hercules CF",
        "SD Huesca",
        "Deportivo La Coruña",
        "Las Palmas",
        "Leganés",
        "Levante",
        "Málaga",
        "Mallorca",
        "CA Osasuna",
        "Oviedo",
        "Real Madrid",
        "Real Racing Club de Santander",
        "Sevilla",
        "Real Sociedad",
        "Sporting Gijón",
        "Valencia",
        "Real Valladolid CF",
        "Rayo Vallecano",
        "Villarreal",
        "Zaragoza",
    ]

    bind = op.get_bind()
    for team_name in teams:
        bind.execute(
            sa.text("DELETE FROM teams WHERE team_name = :name AND sport = :sport")
            .bindparams(name=team_name, sport="SOCCER")
        )

