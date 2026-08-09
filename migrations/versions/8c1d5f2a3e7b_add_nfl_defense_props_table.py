"""add_nfl_defense_props_table

Revision ID: 8c1d5f2a3e7b
Revises: 4b37a816aa06
Create Date: 2026-07-28 00:00:00.000000

Team D/ST (defense/special-teams) entries were incorrectly landing in
nfl_player_props via fake nfl_players rows, because the Odds API's
player_anytime_td market includes team defenses as valid entrants. This
migration creates a dedicated team-scoped nfl_defense_props table and moves
any existing D/ST rows out of nfl_player_props / nfl_players into it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c1d5f2a3e7b'
down_revision: Union[str, None] = '4b37a816aa06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'nfl_defense_props',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('team_id', sa.Integer, sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('team_name', sa.String(100)),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('odds_event_id', sa.String(100)),
        sa.Column('espn_event_id', sa.String(100)),

        sa.Column('odds_source', sa.String(50), server_default='odds_api'),
        sa.Column('bookmaker', sa.String(50)),

        sa.Column('odds_anytime_td', sa.Numeric(4, 1)),
        sa.Column('odds_anytime_td_over_price', sa.Integer),

        sa.Column('actual_total_tackles', sa.Integer),
        sa.Column('actual_solo_tackles', sa.Integer),
        sa.Column('actual_sacks', sa.Numeric(4, 1)),
        sa.Column('actual_tackles_for_loss', sa.Integer),
        sa.Column('actual_passes_defended', sa.Integer),
        sa.Column('actual_qb_hits', sa.Integer),
        sa.Column('actual_defensive_touchdowns', sa.Integer),
        sa.Column('actual_interceptions', sa.Integer),
        sa.Column('actual_interception_yards', sa.Integer),
        sa.Column('actual_interception_touchdowns', sa.Integer),
        sa.Column('actual_kick_returns', sa.Integer),
        sa.Column('actual_kick_return_yards', sa.Integer),
        sa.Column('actual_yards_per_kick_return', sa.Numeric(4, 1)),
        sa.Column('actual_long_kick_return', sa.Integer),
        sa.Column('actual_kick_return_touchdowns', sa.Integer),
        sa.Column('actual_punt_returns', sa.Integer),
        sa.Column('actual_punt_return_yards', sa.Integer),
        sa.Column('actual_yards_per_punt_return', sa.Numeric(4, 1)),
        sa.Column('actual_long_punt_return', sa.Integer),
        sa.Column('actual_punt_return_touchdowns', sa.Integer),
        sa.Column('actual_anytime_td', sa.Boolean),

        sa.Column('opponent_team_name', sa.String(100)),
        sa.Column('opponent_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),

        sa.Column('odds_home_team', sa.String(100)),
        sa.Column('odds_away_team', sa.String(100)),
        sa.Column('odds_home_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),
        sa.Column('odds_away_team_id', sa.Integer, sa.ForeignKey('teams.team_id')),

        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.UniqueConstraint('team_id', 'odds_event_id', name='uq_nfl_defense_props_team_odds_event'),
    )

    op.create_index('idx_nfl_defense_props_game_date', 'nfl_defense_props', ['game_date'])
    op.create_index('ix_nfl_defense_props_team_game_date', 'nfl_defense_props', ['team_id', 'game_date'])

    _migrate_existing_dst_rows()


def _migrate_existing_dst_rows() -> None:
    """Move any D/ST rows already sitting in nfl_player_props (with a fake
    nfl_players entry) into nfl_defense_props, then clean up the fake player."""
    conn = op.get_bind()

    dst_rows = conn.execute(sa.text("""
        SELECT pp.id AS prop_id, pp.player_id, pp.game_date, pp.odds_event_id, pp.espn_event_id,
               pp.odds_source, pp.bookmaker, pp.odds_player_anytime_td AS odds_anytime_td,
               pp.odds_player_anytime_td_over_price AS odds_anytime_td_over_price,
               pp.odds_home_team, pp.odds_away_team, pp.odds_home_team_id, pp.odds_away_team_id,
               p.player_name
        FROM nfl_player_props pp
        JOIN nfl_players p ON pp.player_id = p.id
        WHERE p.player_name ILIKE '%D/ST'
    """)).mappings().fetchall()

    for row in dst_rows:
        team_name = row['player_name']
        if team_name.lower().endswith('d/st'):
            team_name = team_name[:-len('D/ST')].strip()

        team_id_row = conn.execute(sa.text("""
            SELECT team_id FROM teams WHERE odds_api_team_name = :name AND sport = 'NFL'
        """), {'name': team_name}).fetchone()

        if not team_id_row:
            # Can't resolve a team for this row - leave it in nfl_player_props
            # for manual follow-up rather than losing/misfiling it.
            continue

        team_id = team_id_row[0]
        is_home = team_name == row['odds_home_team']
        opponent_team_name = row['odds_away_team'] if is_home else row['odds_home_team']
        opponent_team_id = row['odds_away_team_id'] if is_home else row['odds_home_team_id']

        conn.execute(sa.text("""
            INSERT INTO nfl_defense_props (
                team_id, team_name, game_date, odds_event_id, espn_event_id, odds_source, bookmaker,
                odds_anytime_td, odds_anytime_td_over_price,
                opponent_team_name, opponent_team_id,
                odds_home_team, odds_away_team, odds_home_team_id, odds_away_team_id,
                created_at, updated_at
            ) VALUES (
                :team_id, :team_name, :game_date, :odds_event_id, :espn_event_id, :odds_source, :bookmaker,
                :odds_anytime_td, :odds_anytime_td_over_price,
                :opponent_team_name, :opponent_team_id,
                :odds_home_team, :odds_away_team, :odds_home_team_id, :odds_away_team_id,
                NOW(), NOW()
            )
            ON CONFLICT (team_id, odds_event_id) DO NOTHING
        """), {
            'team_id': team_id,
            'team_name': team_name,
            'game_date': row['game_date'],
            'odds_event_id': row['odds_event_id'],
            'espn_event_id': row['espn_event_id'],
            'odds_source': row['odds_source'],
            'bookmaker': row['bookmaker'],
            'odds_anytime_td': row['odds_anytime_td'],
            'odds_anytime_td_over_price': row['odds_anytime_td_over_price'],
            'opponent_team_name': opponent_team_name,
            'opponent_team_id': opponent_team_id,
            'odds_home_team': row['odds_home_team'],
            'odds_away_team': row['odds_away_team'],
            'odds_home_team_id': row['odds_home_team_id'],
            'odds_away_team_id': row['odds_away_team_id'],
        })

        conn.execute(sa.text(
            "DELETE FROM nfl_player_name_mismatch WHERE nfl_player_props_id = :id"
        ), {'id': row['prop_id']})
        conn.execute(sa.text("DELETE FROM nfl_player_props WHERE id = :id"), {'id': row['prop_id']})

        remaining = conn.execute(sa.text(
            "SELECT COUNT(*) FROM nfl_player_props WHERE player_id = :id"
        ), {'id': row['player_id']}).scalar()

        if remaining == 0:
            conn.execute(sa.text("DELETE FROM nfl_player_aliases WHERE player_id = :id"), {'id': row['player_id']})
            conn.execute(sa.text("DELETE FROM nfl_players WHERE id = :id"), {'id': row['player_id']})


def downgrade() -> None:
    # Data-loss on downgrade: rows migrated into nfl_defense_props are not moved
    # back into nfl_player_props / nfl_players.
    op.drop_index('ix_nfl_defense_props_team_game_date', 'nfl_defense_props')
    op.drop_index('idx_nfl_defense_props_game_date', 'nfl_defense_props')
    op.drop_table('nfl_defense_props')
