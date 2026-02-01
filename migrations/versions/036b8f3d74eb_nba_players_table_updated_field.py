"""nba_players table updated field

Revision ID: 036b8f3d74eb
Revises: e52d07871c8a
Create Date: 2026-01-31 15:02:07.240263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '036b8f3d74eb'
down_revision: Union[str, None] = 'e52d07871c8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
     # Create trigger function
     op.execute('''
     CREATE OR REPLACE FUNCTION update_updated_at_column()
     RETURNS TRIGGER AS $$
     BEGIN
         NEW.updated_at = now();
         RETURN NEW;
     END;
     $$ LANGUAGE plpgsql;
     ''')

     # Create trigger
     op.execute('''
     CREATE TRIGGER update_nba_players_updated_at
     BEFORE UPDATE ON nba_players
     FOR EACH ROW
     EXECUTE FUNCTION update_updated_at_column();
     ''')


def downgrade() -> None:
    # Drop trigger
    op.execute('''
    DROP TRIGGER IF EXISTS update_nba_players_updated_at ON nba_players;
    ''')
    # Drop trigger function
    op.execute('''
    DROP FUNCTION IF EXISTS update_updated_at_column();
    ''')
