from __future__ import annotations

from uuid import UUID

from pydantic import Field

from wandermind.models.base import Metadata, TimestampedModel


class PatchMembership(TimestampedModel):
    patch_id: UUID
    knowledge_item_id: UUID
    semantic_distance: float = Field(ge=0.0, le=2.0)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    novelty: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = Field(default="", max_length=2_000)


class KnowledgePatch(TimestampedModel):
    seed_id: UUID
    label: str = Field(min_length=1, max_length=300)
    center_item_id: UUID | None = None
    member_ids: list[UUID] = Field(default_factory=list)
    coherence: float = Field(default=0.5, ge=0.0, le=1.0)
    exhausted: bool = False
    metadata: Metadata = Field(default_factory=dict)
