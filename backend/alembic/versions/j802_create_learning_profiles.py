"""create persistent shared learning profiles

Revision ID: j802_profiles
Revises: j801_threads
"""

import sqlalchemy as sa

from alembic import op

revision = "j802_profiles"
down_revision = "j801_threads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_profiles",
        sa.Column("thread_id", sa.String(length=200), nullable=False),
        sa.Column("learning_level", sa.String(length=32), nullable=True),
        sa.Column("level_source", sa.String(length=32), nullable=True),
        sa.Column("quiz_history", sa.JSON(), nullable=False),
        sa.Column("completed_topics", sa.JSON(), nullable=False),
        sa.Column("topics_mastered", sa.JSON(), nullable=False),
        sa.Column("topics_to_review", sa.JSON(), nullable=False),
        sa.Column("completed_modules", sa.JSON(), nullable=False),
        sa.Column("current_learning_path", sa.String(length=200), nullable=True),
        sa.Column("last_quiz_score", sa.Float(), nullable=True),
        sa.Column("diagnostic_completed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["conversation_threads.thread_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("thread_id"),
    )


def downgrade() -> None:
    op.drop_table("learning_profiles")
