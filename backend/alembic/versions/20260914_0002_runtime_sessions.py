"""add runtime session persistence

Revision ID: 20260914_0002
Revises: 20260914_0001
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260914_0002"
down_revision: str | None = "20260914_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_exists = inspector.has_table("runtime_sessions")
    if not table_exists:
        op.create_table(
            "runtime_sessions",
            sa.Column("wander_session_id", sa.Uuid(), nullable=True),
            sa.Column("runtime", sa.String(length=60), nullable=False),
            sa.Column("purpose", sa.String(length=60), nullable=False),
            sa.Column("external_session_id", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("cost", sa.JSON(), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["wander_session_id"],
                ["wander_sessions.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    existing_indexes = (
        {index["name"] for index in inspector.get_indexes("runtime_sessions")}
        if table_exists
        else set()
    )
    for name, columns in (
        ("ix_runtime_sessions_status", ["status"]),
        ("ix_runtime_sessions_wander_session_id", ["wander_session_id"]),
    ):
        if name not in existing_indexes:
            op.create_index(op.f(name), "runtime_sessions", columns, unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_runtime_sessions_wander_session_id"), table_name="runtime_sessions")
    op.drop_index(op.f("ix_runtime_sessions_status"), table_name="runtime_sessions")
    op.drop_table("runtime_sessions")
