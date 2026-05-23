"""add game columns to blog posts

Revision ID: 3f7a2b1c8d9e
Revises: 098abf884ce1
Create Date: 2026-05-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3f7a2b1c8d9e'
down_revision: Union[str, None] = '098abf884ce1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('blog_posts', sa.Column('sport', sa.String(length=20), nullable=True))
    op.add_column('blog_posts', sa.Column('sport_key', sa.String(length=50), nullable=True))
    op.add_column('blog_posts', sa.Column('home_team', sa.String(length=100), nullable=True))
    op.add_column('blog_posts', sa.Column('away_team', sa.String(length=100), nullable=True))
    op.add_column('blog_posts', sa.Column('odds_event_id', sa.String(length=255), nullable=True))
    op.add_column('blog_posts', sa.Column('game_date', sa.Date(), nullable=True))
    op.add_column('blog_posts', sa.Column('game_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('blog_posts', 'game_data')
    op.drop_column('blog_posts', 'game_date')
    op.drop_column('blog_posts', 'odds_event_id')
    op.drop_column('blog_posts', 'away_team')
    op.drop_column('blog_posts', 'home_team')
    op.drop_column('blog_posts', 'sport_key')
    op.drop_column('blog_posts', 'sport')
