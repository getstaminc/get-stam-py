"""add_nhl_player_props_tables

Revision ID: f4d2b8a61c93
Revises: a1e8f3c92b47
Create Date: 2026-10-20 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4d2b8a61c93'
down_revision: Union[str, None] = 'a1e8f3c92b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'nhl_players',
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

    op.create_table(
        'nhl_player_aliases',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nhl_players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('source', 'normalized_name', name='uq_nhl_player_aliases_source_normalized'),
    )

    op.create_table(
        'nhl_player_props',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nhl_players.id'), nullable=False),
        sa.Column('normalized_name', sa.String(255)),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('odds_event_id', sa.String(100)),
        sa.Column('espn_event_id', sa.String(100)),
        sa.Column('odds_source', sa.String(50), server_default='odds_api'),
        sa.Column('bookmaker', sa.String(50)),

        # Skater scoring
        sa.Column('odds_player_goals', sa.Numeric(4, 1)),
        sa.Column('odds_player_goals_over_price', sa.Integer),
        sa.Column('odds_player_goals_under_price', sa.Integer),
        sa.Column('odds_player_assists', sa.Numeric(4, 1)),
        sa.Column('odds_player_assists_over_price', sa.Integer),
        sa.Column('odds_player_assists_under_price', sa.Integer),
        sa.Column('odds_player_points', sa.Numeric(4, 1)),
        sa.Column('odds_player_points_over_price', sa.Integer),
        sa.Column('odds_player_points_under_price', sa.Integer),
        sa.Column('odds_player_shots_on_goal', sa.Numeric(4, 1)),
        sa.Column('odds_player_shots_on_goal_over_price', sa.Integer),
        sa.Column('odds_player_shots_on_goal_under_price', sa.Integer),

        # Goalie
        sa.Column('odds_player_total_saves', sa.Numeric(4, 1)),
        sa.Column('odds_player_total_saves_over_price', sa.Integer),
        sa.Column('odds_player_total_saves_under_price', sa.Integer),

        # Anytime goal (binary yes/no market, no under column)
        sa.Column('odds_player_goal_scorer_anytime', sa.Numeric(4, 1)),
        sa.Column('odds_player_goal_scorer_anytime_over_price', sa.Integer),

        # Actuals
        sa.Column('actual_player_goals', sa.Integer),
        sa.Column('actual_player_assists', sa.Integer),
        sa.Column('actual_player_points', sa.Integer),
        sa.Column('actual_player_shots_on_goal', sa.Integer),
        sa.Column('actual_player_total_saves', sa.Integer),
        sa.Column('actual_player_goal_scorer_anytime', sa.Boolean),

        sa.Column('player_team_name', sa.String(100)),
        sa.Column('player_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('opponent_team_name', sa.String(100)),
        sa.Column('opponent_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),

        sa.Column('odds_home_team', sa.String(100)),
        sa.Column('odds_away_team', sa.String(100)),
        sa.Column('odds_home_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_away_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),

        sa.Column('did_not_play', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('actuals_unavailable_reason', sa.String(30)),

        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.UniqueConstraint('player_id', 'odds_event_id', name='uq_nhl_player_props_player_odds_event'),
    )

    op.create_table(
        'nhl_player_name_mismatch',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('nhl_player_props_id', sa.Integer, sa.ForeignKey('nhl_player_props.id'), nullable=False),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('odds_home_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_away_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_home_team', sa.String(100)),
        sa.Column('odds_away_team', sa.String(100)),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('nhl_players.id')),
        sa.Column('resolved', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('ix_nhl_players_normalized_name', 'nhl_players', ['normalized_name'])
    op.create_index('ix_nhl_player_aliases_normalized_name', 'nhl_player_aliases', ['normalized_name'])
    op.create_index('idx_nhl_player_props_game_date_normalized_name', 'nhl_player_props', ['game_date', 'normalized_name'])
    op.create_index('ix_nhl_player_props_player_game_date', 'nhl_player_props', ['player_id', 'game_date'])
    op.create_index('idx_nhl_name_mismatch_game_date', 'nhl_player_name_mismatch', ['game_date'])
    op.create_index('idx_nhl_name_mismatch_resolved', 'nhl_player_name_mismatch', ['resolved'])
    op.create_index('idx_nhl_name_mismatch_player_props', 'nhl_player_name_mismatch', ['nhl_player_props_id'])


def downgrade() -> None:
    op.drop_index('idx_nhl_name_mismatch_player_props', 'nhl_player_name_mismatch')
    op.drop_index('idx_nhl_name_mismatch_resolved', 'nhl_player_name_mismatch')
    op.drop_index('idx_nhl_name_mismatch_game_date', 'nhl_player_name_mismatch')
    op.drop_index('ix_nhl_player_props_player_game_date', 'nhl_player_props')
    op.drop_index('idx_nhl_player_props_game_date_normalized_name', 'nhl_player_props')
    op.drop_index('ix_nhl_player_aliases_normalized_name', 'nhl_player_aliases')
    op.drop_index('ix_nhl_players_normalized_name', 'nhl_players')

    op.drop_table('nhl_player_name_mismatch')
    op.drop_table('nhl_player_props')
    op.drop_table('nhl_player_aliases')
    op.drop_table('nhl_players')
