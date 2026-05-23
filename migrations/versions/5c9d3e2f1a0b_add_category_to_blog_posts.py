"""add category to blog posts

Revision ID: 5c9d3e2f1a0b
Revises: 3f7a2b1c8d9e
Create Date: 2026-05-22 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '5c9d3e2f1a0b'
down_revision: Union[str, None] = '3f7a2b1c8d9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('blog_posts', sa.Column('category', sa.String(length=50), nullable=True))
    op.create_index('idx_blog_posts_category', 'blog_posts', ['category'])


def downgrade() -> None:
    op.drop_index('idx_blog_posts_category', table_name='blog_posts')
    op.drop_column('blog_posts', 'category')
