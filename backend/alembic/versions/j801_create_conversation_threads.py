"""create conversation thread records

Revision ID: j801_threads
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "j801_threads"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_threads",
        sa.Column("thread_id", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("thread_id"),
    )


def downgrade() -> None:
    op.drop_table("conversation_threads")
