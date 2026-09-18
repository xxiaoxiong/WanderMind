from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from wandermind.application.graph_service import GraphView
from wandermind.application.runtime_summary import RuntimeSummary
from wandermind.models import (
    Candidate,
    Feedback,
    FeedbackAction,
    KnowledgeEdge,
    KnowledgeItem,
    KnowledgeType,
    RelationType,
    Seed,
    SeedSource,
    WanderBudget,
    WanderSession,
    Wonder,
)


class KnowledgeCreate(BaseModel):
    content: str = Field(min_length=1, max_length=200_000)
    title: str | None = Field(default=None, max_length=300)
    type: KnowledgeType = KnowledgeType.NOTE
    source: str = Field(default="manual", min_length=1, max_length=100)
    source_ref: str | None = Field(default=None, max_length=2_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdgeCreate(BaseModel):
    source_id: UUID
    target_id: UUID
    relation_type: RelationType
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    created_by: str = Field(default="user", min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_domain(self, *, metadata: dict[str, Any]) -> KnowledgeEdge:
        values = self.model_dump(exclude={"metadata"})
        return KnowledgeEdge(**values, metadata=metadata)


class GraphViewResponse(BaseModel):
    items: list[KnowledgeItem]
    edges: list[KnowledgeEdge]

    @classmethod
    def from_view(cls, view: GraphView) -> GraphViewResponse:
        return cls(items=view.items, edges=view.edges)


class SeedCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    source: SeedSource = SeedSource.EXPLICIT
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    source_item_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_domain(self) -> Seed:
        return Seed(**self.model_dump())


class WanderCreate(BaseModel):
    seed_id: UUID | None = None
    content: str | None = Field(default=None, min_length=1, max_length=20_000)
    budget: WanderBudget = Field(default_factory=WanderBudget)

    @model_validator(mode="after")
    def reject_ambiguous_seed(self) -> WanderCreate:
        if self.seed_id is not None and self.content is not None:
            raise ValueError("provide seed_id or content, not both")
        return self


class WanderRunResponse(BaseModel):
    session: WanderSession
    candidates: list[Candidate]
    wonders: list[Wonder]
    runtime: RuntimeSummary


class FeedbackCreate(BaseModel):
    action: FeedbackAction
    value: float | None = Field(default=None, ge=-1.0, le=1.0)
    note: str | None = Field(default=None, max_length=5_000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_domain(self, wonder_id: UUID) -> Feedback:
        return Feedback(wonder_id=wonder_id, **self.model_dump())


class DeepExploreResponse(BaseModel):
    wonder: Wonder
    evaluation: dict[str, Any]


class IncubationResponse(BaseModel):
    surfaced: bool
    wonder: Wonder | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    storage: str
    runtime: str


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeItem]
    offset: int
    limit: int
