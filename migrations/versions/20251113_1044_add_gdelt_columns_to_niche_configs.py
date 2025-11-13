"""add_gdelt_columns_to_niche_configs

Revision ID: gdelt_niche_001
Revises: 0535c32de0a7
Create Date: 2025-11-13 10:44:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'gdelt_niche_001'
down_revision = '0535c32de0a7'
branch_labels = None
depends_on = None


def upgrade():
    """Add GDELT source configuration columns to niche_configs table."""
    # Add gdelt_enabled column (default to 1 = enabled)
    op.add_column('niche_configs',
        sa.Column('gdelt_enabled', sa.Integer(), nullable=True, server_default='1')
    )

    # Add gdelt_weight column (default to 0.5)
    op.add_column('niche_configs',
        sa.Column('gdelt_weight', sa.Float(), nullable=True, server_default='0.5')
    )

    # Update existing rows to have the default values
    op.execute("UPDATE niche_configs SET gdelt_enabled = 1 WHERE gdelt_enabled IS NULL")
    op.execute("UPDATE niche_configs SET gdelt_weight = 0.5 WHERE gdelt_weight IS NULL")


def downgrade():
    """Remove GDELT source configuration columns from niche_configs table."""
    op.drop_column('niche_configs', 'gdelt_weight')
    op.drop_column('niche_configs', 'gdelt_enabled')
