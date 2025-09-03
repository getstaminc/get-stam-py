"""add_missing_mlb_teams_giants_cardinals

Revision ID: 015d122ed2e4
Revises: e1ee33772ca0
Create Date: 2025-08-30 16:20:51.241112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '015d122ed2e4'
down_revision: Union[str, None] = 'e1ee33772ca0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade():
    # First, drop the existing unique constraint on team_name only
    op.drop_constraint('teams_team_name_key', 'teams', type_='unique')
    
    # Create a new unique constraint on (team_name, sport) combination
    op.create_unique_constraint('teams_team_name_sport_key', 'teams', ['team_name', 'sport'])
    
    # Now add the missing MLB teams with simple names
    missing_teams = ["Cardinals", "Giants"]
    
    for team_name in missing_teams:
        op.execute(f"""
            INSERT INTO teams (team_name, sport) 
            VALUES ('{team_name}', 'MLB')
        """)


def downgrade() -> None:
    # Remove the MLB teams we added
    op.execute("DELETE FROM teams WHERE team_name IN ('Cardinals', 'Giants') AND sport = 'MLB'")
    
    # Drop the new unique constraint
    op.drop_constraint('teams_team_name_sport_key', 'teams', type_='unique')
    
    # Restore the original unique constraint on team_name only
    op.create_unique_constraint('teams_team_name_key', 'teams', ['team_name'])


