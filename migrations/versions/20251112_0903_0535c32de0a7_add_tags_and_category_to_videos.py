"""add_tags_and_category_to_videos

Revision ID: 0535c32de0a7
Revises: 4a856a04a1ce
Create Date: 2025-11-12 09:03:34.333203

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0535c32de0a7'
down_revision = '4a856a04a1ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add category_id and tags columns to videos table
    op.add_column('videos', sa.Column('category_id', sa.String(length=10), nullable=True))
    op.add_column('videos', sa.Column('tags', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove category_id and tags columns from videos table
    op.drop_column('videos', 'tags')
    op.drop_column('videos', 'category_id')
