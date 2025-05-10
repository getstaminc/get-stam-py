"""Create teams table"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = '8d200c5054dd'  # Replace with the generated revision ID
down_revision = None  # This is the first migration, so no down_revision
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'teams',
        sa.Column('team_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('team_name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('sport', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('team_id')
    )


def downgrade():
    op.drop_table('teams')