from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wandermind.infrastructure.database import Base, EmbeddingType
from wandermind.models.base import utc_now


class TimestampMixin:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class KnowledgeItemRow(TimestampMixin, Base):
    __tablename__ = "knowledge_items"
    __table_args__ = (
        Index("ix_knowledge_items_status_created", "status", "created_at"),
        Index("ix_knowledge_items_type", "type"),
    )

    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(100), default="manual")
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    entities: Mapped[list[str]] = mapped_column(JSON, default=list)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType(96), nullable=True)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    status: Mapped[str] = mapped_column(String(40), index=True)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    item_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class KnowledgeEdgeRow(TimestampMixin, Base):
    __tablename__ = "knowledge_edges"
    __table_args__ = (
        Index("ix_knowledge_edges_source_relation", "source_id", "relation_type"),
        Index("ix_knowledge_edges_target_relation", "target_id", "relation_type"),
    )

    source_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_items.id", ondelete="CASCADE")
    )
    target_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_items.id", ondelete="CASCADE")
    )
    relation_type: Mapped[str] = mapped_column(String(50))
    weight: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    edge_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class SeedRow(TimestampMixin, Base):
    __tablename__ = "seeds"

    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(40), index=True)
    source_item_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("knowledge_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seed_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class WanderSessionRow(TimestampMixin, Base):
    __tablename__ = "wander_sessions"

    seed_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("seeds.id", ondelete="CASCADE"))
    state: Mapped[str] = mapped_column(String(40), index=True)
    budget: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), index=True)
    trace: Mapped[dict[str, Any]] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class WanderStepRow(TimestampMixin, Base):
    __tablename__ = "wander_steps"
    __table_args__ = (
        Index("ix_wander_steps_session_index", "session_id", "step_index", unique=True),
    )

    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("wander_sessions.id", ondelete="CASCADE"),
    )
    step_index: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class CandidateRow(TimestampMixin, Base):
    __tablename__ = "candidates"

    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("wander_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    seed_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("seeds.id", ondelete="CASCADE"))
    candidate_type: Mapped[str] = mapped_column(String(40))
    statement: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    source_items: Mapped[list[str]] = mapped_column(JSON)
    operator: Mapped[str] = mapped_column(String(100))
    wander_path: Mapped[list[str]] = mapped_column(JSON)
    scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    candidate_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class WonderRow(TimestampMixin, Base):
    __tablename__ = "wonders"

    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("wander_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    seed_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("seeds.id", ondelete="CASCADE"))
    candidate_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(40), index=True)
    statement: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    why_interesting: Mapped[str] = mapped_column(Text)
    source_items: Mapped[list[str]] = mapped_column(JSON)
    connection_path: Mapped[list[str]] = mapped_column(JSON)
    supporting_evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    counter_evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    scores: Mapped[dict[str, Any]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(40), index=True)
    parent_wonder_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wonders.id", ondelete="SET NULL"),
        nullable=True,
    )
    wonder_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class FeedbackRow(TimestampMixin, Base):
    __tablename__ = "feedback"

    wonder_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("wonders.id", ondelete="CASCADE"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(40), index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class RuntimeSessionRow(TimestampMixin, Base):
    __tablename__ = "runtime_sessions"

    wander_session_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wander_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    runtime: Mapped[str] = mapped_column(String(60))
    purpose: Mapped[str] = mapped_column(String(60))
    external_session_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    cost: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    runtime_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
