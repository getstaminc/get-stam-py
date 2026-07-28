"""add_nfl_player_props_tables

Revision ID: 4b37a816aa06
Revises: 5c9d3e2f1a0b
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b37a816aa06'
down_revision: Union[str, None] = '5c9d3e2f1a0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create nfl_players table (canonical player identity)
    op.create_table(
        'nfl_players',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('espn_player_id', sa.String(50), unique=True, nullable=True),
        sa.Column('player_name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('position', sa.String(10)),
        sa.Column('team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('first_seen_date', sa.Date, nullable=False),
        sa.Column('last_seen_date', sa.Date, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create nfl_player_aliases table (name mapping per source)
    op.create_table(
        'nfl_player_aliases',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nfl_players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('source', 'normalized_name', name='uq_nfl_player_aliases_source_normalized'),
    )

    # Create nfl_player_props table (single table covering all skill-position props)
    op.create_table(
        'nfl_player_props',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nfl_players.id'), nullable=False),
        sa.Column('normalized_name', sa.String(255)),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('odds_event_id', sa.String(100)),
        sa.Column('espn_event_id', sa.String(100)),

        # Source tracking
        sa.Column('odds_source', sa.String(50), server_default='odds_api'),
        sa.Column('bookmaker', sa.String(50)),

        # Odds data (from Odds API)
        sa.Column('odds_player_pass_yds', sa.Numeric(4, 1)),
        sa.Column('odds_player_pass_yds_over_price', sa.Integer),
        sa.Column('odds_player_pass_yds_under_price', sa.Integer),
        sa.Column('odds_player_pass_tds', sa.Numeric(4, 1)),
        sa.Column('odds_player_pass_tds_over_price', sa.Integer),
        sa.Column('odds_player_pass_tds_under_price', sa.Integer),
        sa.Column('odds_player_rush_yds', sa.Numeric(4, 1)),
        sa.Column('odds_player_rush_yds_over_price', sa.Integer),
        sa.Column('odds_player_rush_yds_under_price', sa.Integer),
        sa.Column('odds_player_reception_yds', sa.Numeric(4, 1)),
        sa.Column('odds_player_reception_yds_over_price', sa.Integer),
        sa.Column('odds_player_reception_yds_under_price', sa.Integer),
        sa.Column('odds_player_receptions', sa.Numeric(4, 1)),
        sa.Column('odds_player_receptions_over_price', sa.Integer),
        sa.Column('odds_player_receptions_under_price', sa.Integer),
        sa.Column('odds_player_anytime_td', sa.Numeric(4, 1)),
        sa.Column('odds_player_anytime_td_over_price', sa.Integer),

        # Actual results (from ESPN)
        sa.Column('actual_player_pass_yds', sa.Integer),
        sa.Column('actual_player_pass_tds', sa.Integer),
        sa.Column('actual_player_rush_yds', sa.Integer),
        sa.Column('actual_player_reception_yds', sa.Integer),
        sa.Column('actual_player_receptions', sa.Integer),
        sa.Column('actual_player_rushing_td', sa.Integer),
        sa.Column('actual_player_receiving_td', sa.Integer),
        sa.Column('actual_player_anytime_td', sa.Boolean),

        # Team info
        sa.Column('player_team_name', sa.String(100)),
        sa.Column('player_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('opponent_team_name', sa.String(100)),
        sa.Column('opponent_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),

        # Odds API team info
        sa.Column('odds_home_team', sa.String(100)),
        sa.Column('odds_away_team', sa.String(100)),
        sa.Column('odds_home_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_away_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),

        sa.Column('did_not_play', sa.Boolean, nullable=False, server_default=sa.false()),

        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.UniqueConstraint('player_id', 'odds_event_id', name='uq_nfl_player_props_player_odds_event'),
    )

    # Create nfl_player_name_mismatch table
    op.create_table(
        'nfl_player_name_mismatch',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('nfl_player_props_id', sa.Integer, sa.ForeignKey('nfl_player_props.id'), nullable=False),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('odds_home_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_away_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_home_team', sa.String(100)),
        sa.Column('odds_away_team', sa.String(100)),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nfl_players.id')),
        sa.Column('resolved', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Indexes
    op.create_index('ix_nfl_players_normalized_name', 'nfl_players', ['normalized_name'])
    op.create_index('ix_nfl_player_aliases_normalized_name', 'nfl_player_aliases', ['normalized_name'])
    op.create_index('idx_nfl_player_props_game_date_normalized_name', 'nfl_player_props', ['game_date', 'normalized_name'])
    op.create_index('ix_nfl_player_props_player_game_date', 'nfl_player_props', ['player_id', 'game_date'])
    op.create_index('idx_nfl_name_mismatch_game_date', 'nfl_player_name_mismatch', ['game_date'])
    op.create_index('idx_nfl_name_mismatch_resolved', 'nfl_player_name_mismatch', ['resolved'])
    op.create_index('idx_nfl_name_mismatch_player_props', 'nfl_player_name_mismatch', ['nfl_player_props_id'])


def downgrade() -> None:
    op.drop_index('idx_nfl_name_mismatch_player_props', 'nfl_player_name_mismatch')
    op.drop_index('idx_nfl_name_mismatch_resolved', 'nfl_player_name_mismatch')
    op.drop_index('idx_nfl_name_mismatch_game_date', 'nfl_player_name_mismatch')
    op.drop_index('ix_nfl_player_props_player_game_date', 'nfl_player_props')
    op.drop_index('idx_nfl_player_props_game_date_normalized_name', 'nfl_player_props')
    op.drop_index('ix_nfl_player_aliases_normalized_name', 'nfl_player_aliases')
    op.drop_index('ix_nfl_players_normalized_name', 'nfl_players')

    op.drop_table('nfl_player_name_mismatch')
    op.drop_table('nfl_player_props')
    op.drop_table('nfl_player_aliases')
    op.drop_table('nfl_players')
