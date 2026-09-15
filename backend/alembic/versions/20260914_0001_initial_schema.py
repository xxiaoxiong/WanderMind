"""Initial WanderMind schema.

Revision ID: 20260914_0001
Revises:
Create Date: 2026-09-14
"""

from sqlalchemy import Table

from alembic import op
from wandermind.infrastructure import orm
from wandermind.infrastructure.database import Base

del orm
revision = "20260914_0001"
down_revision = None
branch_labels = None
depends_on = None

INITIAL_TABLE_NAMES = {
    "knowledge_items",
    "knowledge_edges",
    "seeds",
    "wander_sessions",
    "wander_steps",
    "candidates",
    "wonders",
    "feedback",
}


def _initial_tables() -> list[Table]:
    return [table for table in Base.metadata.sorted_tables if table.name in INITIAL_TABLE_NAMES]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind, tables=_initial_tables())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=_initial_tables())
