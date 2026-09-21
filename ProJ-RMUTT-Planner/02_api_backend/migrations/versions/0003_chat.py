"""chat_sessions + chat_messages

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-20

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.student_id"], name="fk_chat_sessions_student_id"
        ),
    )
    op.create_index("ix_chat_sessions_student_id", "chat_sessions", ["student_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="complete"),
        sa.Column("sources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["session_id"], ["chat_sessions.id"], name="fk_chat_messages_session_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_student_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
