"""add blog posts table

Revision ID: 098abf884ce1
Revises: 505d606f158e
Create Date: 2026-05-18 17:04:05.554349

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '098abf884ce1'
down_revision: Union[str, None] = '505d606f158e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('blog_posts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('youtube_video_id', sa.String(length=20), nullable=True),
        sa.Column('youtube_title', sa.String(length=500), nullable=True),
        sa.Column('youtube_description', sa.Text(), nullable=True),
        sa.Column('youtube_thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('youtube_published_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('slug', sa.String(length=600), nullable=False),
        sa.Column('meta_description', sa.String(length=200), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('reading_time_minutes', sa.Integer(), nullable=True),
        sa.Column('og_image_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('youtube_video_id'),
    )
    op.create_index('idx_blog_posts_slug', 'blog_posts', ['slug'], unique=True)
    op.create_index('idx_blog_posts_status_published_at', 'blog_posts', ['status', 'published_at'])


def downgrade() -> None:
    op.drop_index('idx_blog_posts_status_published_at', table_name='blog_posts')
    op.drop_index('idx_blog_posts_slug', table_name='blog_posts')
    op.drop_table('blog_posts')
