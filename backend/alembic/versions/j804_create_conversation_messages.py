"""create product conversation history

Revision ID: j804_messages
Revises: j802_profiles
"""

import sqlalchemy as sa

from alembic import op

revision = "j804_messages"
down_revision = "j802_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.String(length=200), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("script", sa.String(length=16), nullable=True),
        sa.Column("route", sa.String(length=64), nullable=True),
        sa.Column("knowledge_source", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["conversation_threads.thread_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "thread_id", "turn_index", "role", name="uq_conversation_message_turn_role"
        ),
    )


def downgrade() -> None:
    op.drop_table("conversation_messages")
