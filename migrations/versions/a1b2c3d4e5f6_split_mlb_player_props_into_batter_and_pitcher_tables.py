"""split mlb_player_props into batter and pitcher tables

Revision ID: a1b2c3d4e5f6
Revises: 636190593461
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '636190593461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop mlb_player_name_mismatch first (FK dependency on mlb_player_props)
    op.drop_index('idx_mlb_name_mismatch_resolved', table_name='mlb_player_name_mismatch')
    op.drop_index('idx_mlb_name_mismatch_player_props', table_name='mlb_player_name_mismatch')
    op.drop_index('idx_mlb_name_mismatch_game_date', table_name='mlb_player_name_mismatch')
    op.drop_table('mlb_player_name_mismatch')

    # Drop mlb_player_props
    op.drop_index('ix_mlb_player_props_player_game_date', table_name='mlb_player_props')
    op.drop_index('idx_mlb_player_props_game_date_normalized_name', table_name='mlb_player_props')
    op.drop_table('mlb_player_props')

    # Create mlb_batter_props
    op.create_table('mlb_batter_props',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=True),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('odds_event_id', sa.String(length=100), nullable=True),
        sa.Column('espn_event_id', sa.String(length=100), nullable=True),
        sa.Column('odds_source', sa.String(length=50), server_default='odds_api', nullable=True),
        sa.Column('bookmaker', sa.String(length=50), nullable=True),
        sa.Column('odds_batter_hits', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_hits_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_hits_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_home_runs', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_home_runs_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_home_runs_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_rbi', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_rbi_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_rbi_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_runs_scored', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_runs_scored_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_runs_scored_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_total_bases', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_total_bases_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_total_bases_under_price', sa.Integer(), nullable=True),
        sa.Column('actual_batter_hits', sa.Integer(), nullable=True),
        sa.Column('actual_batter_home_runs', sa.Integer(), nullable=True),
        sa.Column('actual_batter_rbi', sa.Integer(), nullable=True),
        sa.Column('actual_batter_runs_scored', sa.Integer(), nullable=True),
        sa.Column('actual_batter_total_bases', sa.Integer(), nullable=True),
        sa.Column('actual_batter_at_bats', sa.Integer(), nullable=True),
        sa.Column('actual_batter_walks', sa.Integer(), nullable=True),
        sa.Column('actual_batter_strikeouts', sa.Integer(), nullable=True),
        sa.Column('player_team_name', sa.String(length=100), nullable=True),
        sa.Column('player_team_id', sa.Integer(), nullable=True),
        sa.Column('opponent_team_name', sa.String(length=100), nullable=True),
        sa.Column('opponent_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_home_team', sa.String(length=100), nullable=True),
        sa.Column('odds_away_team', sa.String(length=100), nullable=True),
        sa.Column('odds_home_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_away_team_id', sa.Integer(), nullable=True),
        sa.Column('did_not_play', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['odds_away_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['odds_home_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['opponent_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['mlb_players.id'], ),
        sa.ForeignKeyConstraint(['player_team_id'], ['teams.team_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_id', 'odds_event_id', name='uq_mlb_batter_props_player_odds_event'),
    )
    op.create_index('idx_mlb_batter_props_game_date_normalized_name', 'mlb_batter_props', ['game_date', 'normalized_name'], unique=False)
    op.create_index('ix_mlb_batter_props_player_game_date', 'mlb_batter_props', ['player_id', 'game_date'], unique=False)

    # Create mlb_pitcher_props
    op.create_table('mlb_pitcher_props',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=True),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('odds_event_id', sa.String(length=100), nullable=True),
        sa.Column('espn_event_id', sa.String(length=100), nullable=True),
        sa.Column('odds_source', sa.String(length=50), server_default='odds_api', nullable=True),
        sa.Column('bookmaker', sa.String(length=50), nullable=True),
        sa.Column('odds_pitcher_strikeouts', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_pitcher_strikeouts_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_strikeouts_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_earned_runs', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_pitcher_earned_runs_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_earned_runs_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_hits_allowed', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_pitcher_hits_allowed_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_hits_allowed_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_walks', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_pitcher_walks_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_walks_under_price', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_strikeouts', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_earned_runs', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_hits_allowed', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_walks', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_innings_pitched', sa.String(length=10), nullable=True),
        sa.Column('player_team_name', sa.String(length=100), nullable=True),
        sa.Column('player_team_id', sa.Integer(), nullable=True),
        sa.Column('opponent_team_name', sa.String(length=100), nullable=True),
        sa.Column('opponent_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_home_team', sa.String(length=100), nullable=True),
        sa.Column('odds_away_team', sa.String(length=100), nullable=True),
        sa.Column('odds_home_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_away_team_id', sa.Integer(), nullable=True),
        sa.Column('did_not_play', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['odds_away_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['odds_home_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['opponent_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['mlb_players.id'], ),
        sa.ForeignKeyConstraint(['player_team_id'], ['teams.team_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_id', 'odds_event_id', name='uq_mlb_pitcher_props_player_odds_event'),
    )
    op.create_index('idx_mlb_pitcher_props_game_date_normalized_name', 'mlb_pitcher_props', ['game_date', 'normalized_name'], unique=False)
    op.create_index('ix_mlb_pitcher_props_player_game_date', 'mlb_pitcher_props', ['player_id', 'game_date'], unique=False)

    # Recreate mlb_player_name_mismatch with new FK columns
    op.create_table('mlb_player_name_mismatch',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('batter_props_id', sa.Integer(), nullable=True),
        sa.Column('pitcher_props_id', sa.Integer(), nullable=True),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('odds_home_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_away_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_home_team', sa.String(length=100), nullable=True),
        sa.Column('odds_away_team', sa.String(length=100), nullable=True),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            '(batter_props_id IS NOT NULL)::int + (pitcher_props_id IS NOT NULL)::int = 1',
            name='chk_mlb_name_mismatch_exactly_one_props_id'
        ),
        sa.ForeignKeyConstraint(['batter_props_id'], ['mlb_batter_props.id'], ),
        sa.ForeignKeyConstraint(['pitcher_props_id'], ['mlb_pitcher_props.id'], ),
        sa.ForeignKeyConstraint(['odds_away_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['odds_home_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['mlb_players.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_mlb_name_mismatch_game_date', 'mlb_player_name_mismatch', ['game_date'], unique=False)
    op.create_index('idx_mlb_name_mismatch_resolved', 'mlb_player_name_mismatch', ['resolved'], unique=False)
    op.create_index('idx_mlb_name_mismatch_batter_props', 'mlb_player_name_mismatch', ['batter_props_id'], unique=False)
    op.create_index('idx_mlb_name_mismatch_pitcher_props', 'mlb_player_name_mismatch', ['pitcher_props_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_mlb_name_mismatch_pitcher_props', table_name='mlb_player_name_mismatch')
    op.drop_index('idx_mlb_name_mismatch_batter_props', table_name='mlb_player_name_mismatch')
    op.drop_index('idx_mlb_name_mismatch_resolved', table_name='mlb_player_name_mismatch')
    op.drop_index('idx_mlb_name_mismatch_game_date', table_name='mlb_player_name_mismatch')
    op.drop_table('mlb_player_name_mismatch')

    op.drop_index('ix_mlb_pitcher_props_player_game_date', table_name='mlb_pitcher_props')
    op.drop_index('idx_mlb_pitcher_props_game_date_normalized_name', table_name='mlb_pitcher_props')
    op.drop_table('mlb_pitcher_props')

    op.drop_index('ix_mlb_batter_props_player_game_date', table_name='mlb_batter_props')
    op.drop_index('idx_mlb_batter_props_game_date_normalized_name', table_name='mlb_batter_props')
    op.drop_table('mlb_batter_props')

    # Recreate mlb_player_props
    op.create_table('mlb_player_props',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=True),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('odds_event_id', sa.String(length=100), nullable=True),
        sa.Column('espn_event_id', sa.String(length=100), nullable=True),
        sa.Column('odds_source', sa.String(length=50), server_default='odds_api', nullable=True),
        sa.Column('bookmaker', sa.String(length=50), nullable=True),
        sa.Column('player_type', sa.String(length=10), nullable=True),
        sa.Column('odds_batter_hits', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_hits_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_hits_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_home_runs', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_home_runs_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_home_runs_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_rbi', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_rbi_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_rbi_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_runs_scored', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_runs_scored_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_runs_scored_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_total_bases', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_batter_total_bases_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_batter_total_bases_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_strikeouts', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_pitcher_strikeouts_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_strikeouts_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_earned_runs', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_pitcher_earned_runs_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_earned_runs_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_hits_allowed', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_pitcher_hits_allowed_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_hits_allowed_under_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_walks', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('odds_pitcher_walks_over_price', sa.Integer(), nullable=True),
        sa.Column('odds_pitcher_walks_under_price', sa.Integer(), nullable=True),
        sa.Column('actual_batter_hits', sa.Integer(), nullable=True),
        sa.Column('actual_batter_home_runs', sa.Integer(), nullable=True),
        sa.Column('actual_batter_rbi', sa.Integer(), nullable=True),
        sa.Column('actual_batter_runs_scored', sa.Integer(), nullable=True),
        sa.Column('actual_batter_total_bases', sa.Integer(), nullable=True),
        sa.Column('actual_batter_at_bats', sa.Integer(), nullable=True),
        sa.Column('actual_batter_walks', sa.Integer(), nullable=True),
        sa.Column('actual_batter_strikeouts', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_strikeouts', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_earned_runs', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_hits_allowed', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_walks', sa.Integer(), nullable=True),
        sa.Column('actual_pitcher_innings_pitched', sa.String(length=10), nullable=True),
        sa.Column('player_team_name', sa.String(length=100), nullable=True),
        sa.Column('player_team_id', sa.Integer(), nullable=True),
        sa.Column('opponent_team_name', sa.String(length=100), nullable=True),
        sa.Column('opponent_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_home_team', sa.String(length=100), nullable=True),
        sa.Column('odds_away_team', sa.String(length=100), nullable=True),
        sa.Column('odds_home_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_away_team_id', sa.Integer(), nullable=True),
        sa.Column('did_not_play', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['odds_away_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['odds_home_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['opponent_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['mlb_players.id'], ),
        sa.ForeignKeyConstraint(['player_team_id'], ['teams.team_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_id', 'odds_event_id', 'player_type', name='uq_mlb_player_props_player_odds_event'),
    )
    op.create_index('idx_mlb_player_props_game_date_normalized_name', 'mlb_player_props', ['game_date', 'normalized_name'], unique=False)
    op.create_index('ix_mlb_player_props_player_game_date', 'mlb_player_props', ['player_id', 'game_date'], unique=False)

    # Recreate mlb_player_name_mismatch with original FK
    op.create_table('mlb_player_name_mismatch',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mlb_player_props_id', sa.Integer(), nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('odds_home_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_away_team_id', sa.Integer(), nullable=True),
        sa.Column('odds_home_team', sa.String(length=100), nullable=True),
        sa.Column('odds_away_team', sa.String(length=100), nullable=True),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['mlb_player_props_id'], ['mlb_player_props.id'], ),
        sa.ForeignKeyConstraint(['odds_away_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['odds_home_team_id'], ['teams.team_id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['mlb_players.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_mlb_name_mismatch_game_date', 'mlb_player_name_mismatch', ['game_date'], unique=False)
    op.create_index('idx_mlb_name_mismatch_player_props', 'mlb_player_name_mismatch', ['mlb_player_props_id'], unique=False)
    op.create_index('idx_mlb_name_mismatch_resolved', 'mlb_player_name_mismatch', ['resolved'], unique=False)
