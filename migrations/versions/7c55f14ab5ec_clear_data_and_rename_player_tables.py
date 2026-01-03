"""clear_data_and_rename_player_tables

Revision ID: 7c55f14ab5ec
Revises: cd7eb6d1351a
Create Date: 2026-01-02 13:48:05.380792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c55f14ab5ec'
down_revision: Union[str, None] = 'cd7eb6d1351a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear all data from tables in proper order (respecting foreign keys)
    print("Clearing data from nba_player_props table...")
    op.execute("DELETE FROM nba_player_props")
    
    print("Clearing data from player_aliases table...")
    op.execute("DELETE FROM player_aliases")
    
    print("Clearing data from players table...")
    op.execute("DELETE FROM players")
    
    # Reset sequences to start from 1
    print("Resetting sequences...")
    op.execute("ALTER SEQUENCE nba_player_props_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE player_aliases_id_seq RESTART WITH 1") 
    op.execute("ALTER SEQUENCE players_id_seq RESTART WITH 1")
    
    # Drop foreign key constraints that reference the tables we're about to rename
    print("Dropping foreign key constraints...")
    op.drop_constraint('nba_player_props_player_id_fkey', 'nba_player_props', type_='foreignkey')
    op.drop_constraint('player_aliases_player_id_fkey', 'player_aliases', type_='foreignkey')
    
    # Rename tables
    print("Renaming tables...")
    op.rename_table('players', 'nba_players')
    op.rename_table('player_aliases', 'nba_player_aliases')
    
    # Rename sequences to match new table names
    print("Renaming sequences...")
    op.execute("ALTER SEQUENCE players_id_seq RENAME TO nba_players_id_seq")
    op.execute("ALTER SEQUENCE player_aliases_id_seq RENAME TO nba_player_aliases_id_seq")
    
    # Recreate foreign key constraints with new table names
    print("Recreating foreign key constraints...")
    op.create_foreign_key(
        'nba_player_props_player_id_fkey',
        'nba_player_props', 'nba_players',
        ['player_id'], ['id']
    )
    op.create_foreign_key(
        'nba_player_aliases_player_id_fkey', 
        'nba_player_aliases', 'nba_players',
        ['player_id'], ['id'],
        ondelete='CASCADE'
    )
    
    print("Migration completed successfully!")


def downgrade() -> None:
    # Reverse the process for downgrade
    print("Reversing migration...")
    
    # Drop foreign key constraints
    op.drop_constraint('nba_player_props_player_id_fkey', 'nba_player_props', type_='foreignkey')
    op.drop_constraint('nba_player_aliases_player_id_fkey', 'nba_player_aliases', type_='foreignkey')
    
    # Rename tables back
    op.rename_table('nba_players', 'players')
    op.rename_table('nba_player_aliases', 'player_aliases')
    
    # Rename sequences back
    op.execute("ALTER SEQUENCE nba_players_id_seq RENAME TO players_id_seq")
    op.execute("ALTER SEQUENCE nba_player_aliases_id_seq RENAME TO player_aliases_id_seq")
    
    # Recreate original foreign key constraints
    op.create_foreign_key(
        'nba_player_props_player_id_fkey',
        'nba_player_props', 'players',
        ['player_id'], ['id']
    )
    op.create_foreign_key(
        'player_aliases_player_id_fkey',
        'player_aliases', 'players', 
        ['player_id'], ['id'],
        ondelete='CASCADE'
    )
