from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from wandermind.models.base import Metadata, TimestampedModel
from wandermind.models.enums import KnowledgeStatus, KnowledgeType, RelationType


class KnowledgeItem(TimestampedModel):
    type: KnowledgeType = KnowledgeType.NOTE
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=200_000)
    summary: str = Field(default="", max_length=2_000)
    source: str = Field(default="manual", min_length=1, max_length=100)
    source_ref: str | None = Field(default=None, max_length=2_000)
    topics: list[str] = Field(default_factory=list, max_length=100)
    entities: list[str] = Field(default_factory=list, max_length=100)
    embedding: list[float] | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    event_time: datetime | None = None
    metadata: Metadata = Field(default_factory=dict)

    @field_validator("topics", "entities")
    @classmethod
    def normalize_labels(cls, values: list[str]) -> list[str]:
        unique: dict[str, None] = {}
        for value in values:
            normalized = " ".join(value.split()).strip()
            if normalized:
                unique.setdefault(normalized, None)
        return list(unique)


class KnowledgeEdge(TimestampedModel):
    source_id: UUID
    target_id: UUID
    relation_type: RelationType
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    created_by: str = Field(default="system", min_length=1, max_length=100)
    metadata: Metadata = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_self_loop(self) -> KnowledgeEdge:
        if self.source_id == self.target_id:
            raise ValueError("knowledge edge cannot be a self-loop")
        return self
