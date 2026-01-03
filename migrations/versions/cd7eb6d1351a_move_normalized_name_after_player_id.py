"""move_normalized_name_after_player_id

Revision ID: cd7eb6d1351a
Revises: 6b97fa1714d3
Create Date: 2026-01-01 13:23:03.542017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd7eb6d1351a'
down_revision: Union[str, None] = '6b97fa1714d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The table is already named nba_player_props and has normalized_name column
    # We just need to reorder columns to put normalized_name right after player_id
    
    # Create new table with desired column order
    op.execute("""
        CREATE TABLE nba_player_props_new (
            id int4 NOT NULL DEFAULT nextval('player_props_id_seq'::regclass),
            player_id int4 NOT NULL,
            normalized_name varchar(255),
            game_date date NOT NULL,
            odds_event_id varchar(100),
            espn_event_id varchar(100),
            odds_source varchar(50) DEFAULT 'odds_api'::character varying,
            bookmaker varchar(50),
            odds_player_points numeric(4,1),
            odds_player_points_over_price int4,
            odds_player_points_under_price int4,
            odds_player_rebounds numeric(4,1),
            odds_player_rebounds_over_price int4,
            odds_player_rebounds_under_price int4,
            odds_player_assists numeric(4,1),
            odds_player_assists_over_price int4,
            odds_player_assists_under_price int4,
            odds_player_threes numeric(4,1),
            odds_player_threes_over_price int4,
            odds_player_threes_under_price int4,
            actual_player_points int4,
            actual_player_rebounds int4,
            actual_player_assists int4,
            actual_player_threes int4,
            actual_player_minutes varchar(10),
            actual_player_fg varchar(10),
            actual_player_ft varchar(10),
            actual_plus_minus int4,
            player_team varchar(100),
            player_team_id int4,
            opponent_team varchar(100),
            opponent_team_id int4,
            created_at timestamp DEFAULT now(),
            updated_at timestamp DEFAULT now(),
            CONSTRAINT nba_player_props_pkey PRIMARY KEY (id),
            CONSTRAINT nba_player_props_player_id_fkey FOREIGN KEY (player_id) REFERENCES players(id),
            CONSTRAINT nba_player_props_player_team_id_fkey FOREIGN KEY (player_team_id) REFERENCES teams(team_id),
            CONSTRAINT nba_player_props_opponent_team_id_fkey FOREIGN KEY (opponent_team_id) REFERENCES teams(team_id)
        )
    """)
    
    # Copy data from old table to new table
    op.execute("""
        INSERT INTO nba_player_props_new (
            id, player_id, normalized_name, game_date, odds_event_id, espn_event_id,
            odds_source, bookmaker, odds_player_points, odds_player_points_over_price,
            odds_player_points_under_price, odds_player_rebounds, odds_player_rebounds_over_price,
            odds_player_rebounds_under_price, odds_player_assists, odds_player_assists_over_price,
            odds_player_assists_under_price, odds_player_threes, odds_player_threes_over_price,
            odds_player_threes_under_price, actual_player_points, actual_player_rebounds,
            actual_player_assists, actual_player_threes, actual_player_minutes, actual_player_fg,
            actual_player_ft, actual_plus_minus, player_team, player_team_id, opponent_team,
            opponent_team_id, created_at, updated_at
        )
        SELECT 
            id, player_id, normalized_name, game_date, odds_event_id, espn_event_id,
            odds_source, bookmaker, odds_player_points, odds_player_points_over_price,
            odds_player_points_under_price, odds_player_rebounds, odds_player_rebounds_over_price,
            odds_player_rebounds_under_price, odds_player_assists, odds_player_assists_over_price,
            odds_player_assists_under_price, odds_player_threes, odds_player_threes_over_price,
            odds_player_threes_under_price, actual_player_points, actual_player_rebounds,
            actual_player_assists, actual_player_threes, actual_player_minutes, actual_player_fg,
            actual_player_ft, actual_plus_minus, player_team, player_team_id, opponent_team,
            opponent_team_id, created_at, updated_at
        FROM nba_player_props
    """)
    
    # Drop old table with CASCADE to handle sequence dependencies
    op.execute("DROP TABLE nba_player_props CASCADE")
    
    # Rename new table
    op.execute("ALTER TABLE nba_player_props_new RENAME TO nba_player_props")
    
    # Recreate indices with new table
    op.create_index('uq_player_props_player_odds_event', 'nba_player_props', ['player_id', 'odds_event_id'], unique=True)
    op.create_index('ix_player_props_game_date', 'nba_player_props', ['game_date'])
    op.create_index('ix_player_props_player_game_date', 'nba_player_props', ['player_id', 'game_date'])
    op.create_index('idx_nba_player_props_normalized_name', 'nba_player_props', ['normalized_name'])


def downgrade() -> None:
    # Just reverse the column reordering, keeping all the other changes
    op.execute("""
        CREATE TABLE nba_player_props_old (
            id int4 NOT NULL DEFAULT nextval('player_props_id_seq'::regclass),
            player_id int4 NOT NULL,
            game_date date NOT NULL,
            odds_event_id varchar(100),
            espn_event_id varchar(100),
            odds_source varchar(50) DEFAULT 'odds_api'::character varying,
            bookmaker varchar(50),
            odds_player_points numeric(4,1),
            odds_player_points_over_price int4,
            odds_player_points_under_price int4,
            odds_player_rebounds numeric(4,1),
            odds_player_rebounds_over_price int4,
            odds_player_rebounds_under_price int4,
            odds_player_assists numeric(4,1),
            odds_player_assists_over_price int4,
            odds_player_assists_under_price int4,
            odds_player_threes numeric(4,1),
            odds_player_threes_over_price int4,
            odds_player_threes_under_price int4,
            actual_player_points int4,
            actual_player_rebounds int4,
            actual_player_assists int4,
            actual_player_threes int4,
            actual_player_minutes varchar(10),
            actual_player_fg varchar(10),
            actual_player_ft varchar(10),
            actual_plus_minus int4,
            player_team varchar(100),
            player_team_id int4,
            opponent_team varchar(100),
            opponent_team_id int4,
            created_at timestamp DEFAULT now(),
            updated_at timestamp DEFAULT now(),
            normalized_name varchar(255),
            CONSTRAINT nba_player_props_pkey PRIMARY KEY (id),
            CONSTRAINT nba_player_props_player_id_fkey FOREIGN KEY (player_id) REFERENCES players(id),
            CONSTRAINT nba_player_props_player_team_id_fkey FOREIGN KEY (player_team_id) REFERENCES teams(team_id),
            CONSTRAINT nba_player_props_opponent_team_id_fkey FOREIGN KEY (opponent_team_id) REFERENCES teams(team_id)
        )
    """)
    
    # Copy data back
    op.execute("""
        INSERT INTO nba_player_props_old SELECT 
            id, player_id, game_date, odds_event_id, espn_event_id, odds_source, bookmaker,
            odds_player_points, odds_player_points_over_price, odds_player_points_under_price,
            odds_player_rebounds, odds_player_rebounds_over_price, odds_player_rebounds_under_price,
            odds_player_assists, odds_player_assists_over_price, odds_player_assists_under_price,
            odds_player_threes, odds_player_threes_over_price, odds_player_threes_under_price,
            actual_player_points, actual_player_rebounds, actual_player_assists, actual_player_threes,
            actual_player_minutes, actual_player_fg, actual_player_ft, actual_plus_minus,
            player_team, player_team_id, opponent_team, opponent_team_id, created_at, updated_at,
            normalized_name
        FROM nba_player_props
    """)
    
    op.drop_table('nba_player_props')
    op.execute("ALTER TABLE nba_player_props_old RENAME TO nba_player_props")
    
    # Recreate indices
    op.create_index('uq_player_props_player_odds_event', 'nba_player_props', ['player_id', 'odds_event_id'], unique=True)
    op.create_index('ix_player_props_game_date', 'nba_player_props', ['game_date'])
    op.create_index('ix_player_props_player_game_date', 'nba_player_props', ['player_id', 'game_date'])
    op.create_index('idx_nba_player_props_normalized_name', 'nba_player_props', ['normalized_name'])
