"""create study_log table

Revision ID: 202607160001
Revises:
Create Date: 2026-07-16 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607160001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("engine_used", sa.Text(), nullable=False),
        sa.Column("subject_tag", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_study_log_telegram_id", "study_log", ["telegram_id"])
    op.create_index("idx_study_log_created_at", "study_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_study_log_created_at", table_name="study_log")
    op.drop_index("idx_study_log_telegram_id", table_name="study_log")
    op.drop_table("study_log")
