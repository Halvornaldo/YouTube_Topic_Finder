"""add_template_tracking_columns_to_niche_configs

Revision ID: 4a856a04a1ce
Revises: 51def9469a47
Create Date: 2025-11-11 19:35:43.362603

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a856a04a1ce'
down_revision = '51def9469a47'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add template and ownership tracking columns to niche_configs
    op.add_column('niche_configs', sa.Column('is_template', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('niche_configs', sa.Column('created_by', sa.String(length=100), nullable=True))
    op.add_column('niche_configs', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    # Remove template and ownership tracking columns from niche_configs
    op.drop_column('niche_configs', 'version')
    op.drop_column('niche_configs', 'created_by')
    op.drop_column('niche_configs', 'is_template')
