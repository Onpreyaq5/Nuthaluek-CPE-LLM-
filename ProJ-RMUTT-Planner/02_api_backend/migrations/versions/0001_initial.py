"""initial: students, student_preferences

Revision ID: 0001
Revises:
Create Date: 2026-09-19

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.String(length=20), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="student"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", name="uq_students_student_id"),
        sa.UniqueConstraint("username", name="uq_students_username"),
    )
    op.create_index("ix_students_student_id", "students", ["student_id"])

    op.create_table(
        "student_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.String(length=20), nullable=False),
        sa.Column("free_days", sa.JSON(), nullable=False),
        sa.Column("no_early_class", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_credits", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.student_id"], name="fk_student_preferences_student_id"
        ),
        sa.UniqueConstraint("student_id", name="uq_student_preferences_student_id"),
    )
    op.create_index("ix_student_preferences_student_id", "student_preferences", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_student_preferences_student_id", table_name="student_preferences")
    op.drop_table("student_preferences")
    op.drop_index("ix_students_student_id", table_name="students")
    op.drop_table("students")
