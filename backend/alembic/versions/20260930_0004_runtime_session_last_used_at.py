"""add runtime session last-used timestamp

Revision ID: 20260930_0004
Revises: 20260929_0003
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260930_0004"
down_revision: str | None = "20260929_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("runtime_sessions")}
    if "last_used_at" not in columns:
        op.add_column(
            "runtime_sessions",
            sa.Column(
                "last_used_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.alter_column("runtime_sessions", "last_used_at", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("runtime_sessions")}
    if "last_used_at" in columns:
        op.drop_column("runtime_sessions", "last_used_at")
