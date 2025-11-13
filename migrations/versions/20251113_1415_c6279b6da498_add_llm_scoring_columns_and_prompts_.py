"""add_llm_scoring_columns_and_prompts_table

Revision ID: c6279b6da498
Revises: gdelt_niche_001
Create Date: 2025-11-13 14:15:33.641300

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c6279b6da498'
down_revision = 'gdelt_niche_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add LLM scoring columns to seed_topics table
    op.add_column('seed_topics', sa.Column('raw_score', sa.Float(), nullable=True, comment='Original score from Robot 1'))
    op.add_column('seed_topics', sa.Column('llm_score', sa.Float(), nullable=True, comment='Score from LLM (0-100)'))
    op.add_column('seed_topics', sa.Column('final_score', sa.Float(), nullable=True, comment='Weighted combination of raw_score and llm_score'))
    op.add_column('seed_topics', sa.Column('llm_reasoning', sa.Text(), nullable=True, comment='Why LLM gave this score'))
    op.add_column('seed_topics', sa.Column('profit_angle', sa.Text(), nullable=True, comment='Suggested high-CPM video title'))
    op.add_column('seed_topics', sa.Column('scored_at', sa.TIMESTAMP(), nullable=True, comment='When LLM scored it'))
    op.add_column('seed_topics', sa.Column('llm_provider', sa.String(50), nullable=True, comment='LLM provider used (gemini, openai, etc.)'))
    op.add_column('seed_topics', sa.Column('status', sa.String(20), nullable=True, server_default='pending', comment='pending, scored, rejected'))

    # Create index on status for efficient querying
    op.create_index('ix_seed_topics_status', 'seed_topics', ['status'])

    # Backfill existing topics: copy trend_score to raw_score and set status to 'pending'
    op.execute("UPDATE seed_topics SET raw_score = trend_score, status = 'pending' WHERE raw_score IS NULL")

    # Create llm_prompts table for prompt management and versioning
    op.create_table(
        'llm_prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='Prompt identifier (e.g. robot1_5_topic_scorer)'),
        sa.Column('prompt_template', sa.Text(), nullable=False, comment='The actual prompt with {variables}'),
        sa.Column('description', sa.Text(), nullable=True, comment='What this prompt does'),
        sa.Column('variables', sa.JSON(), nullable=True, comment='Available variables & their types'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1', comment='Track prompt versions'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Is this version active'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_prompt_name_version')
    )

    # Create indexes for efficient querying
    op.create_index('ix_llm_prompts_name', 'llm_prompts', ['name'])
    op.create_index('ix_llm_prompts_is_active', 'llm_prompts', ['is_active'])


def downgrade() -> None:
    # Drop llm_prompts table
    op.drop_index('ix_llm_prompts_is_active', table_name='llm_prompts')
    op.drop_index('ix_llm_prompts_name', table_name='llm_prompts')
    op.drop_table('llm_prompts')

    # Drop index on seed_topics.status
    op.drop_index('ix_seed_topics_status', table_name='seed_topics')

    # Drop LLM scoring columns from seed_topics
    op.drop_column('seed_topics', 'status')
    op.drop_column('seed_topics', 'llm_provider')
    op.drop_column('seed_topics', 'scored_at')
    op.drop_column('seed_topics', 'profit_angle')
    op.drop_column('seed_topics', 'llm_reasoning')
    op.drop_column('seed_topics', 'final_score')
    op.drop_column('seed_topics', 'llm_score')
    op.drop_column('seed_topics', 'raw_score')
