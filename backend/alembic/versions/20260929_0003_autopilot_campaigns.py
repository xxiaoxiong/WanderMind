"""add persistent autopilot campaigns

Revision ID: 20260929_0003
Revises: 20260914_0002
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0003"
down_revision: str | None = "20260914_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "autopilot_campaigns",
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("budget", sa.JSON(), nullable=False),
        sa.Column("current_session_id", sa.Uuid(), nullable=True),
        sa.Column("cycles_started", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cycles_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_wonders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_runtime_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("promoted_knowledge_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_cycle_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_cycle_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_cycle_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["current_session_id"], ["wander_sessions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_autopilot_campaigns_current_session_id"),
        "autopilot_campaigns",
        ["current_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_autopilot_campaigns_status"),
        "autopilot_campaigns",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_autopilot_campaigns_status"), table_name="autopilot_campaigns"
    )
    op.drop_index(
        op.f("ix_autopilot_campaigns_current_session_id"),
        table_name="autopilot_campaigns",
    )
    op.drop_table("autopilot_campaigns")
