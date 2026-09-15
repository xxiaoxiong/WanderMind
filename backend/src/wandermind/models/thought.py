from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from wandermind.models.base import DomainModel, Metadata, TimestampedModel
from wandermind.models.enums import (
    CandidateStatus,
    FeedbackAction,
    SeedSource,
    SeedStatus,
    WonderStatus,
    WonderType,
)


class Seed(TimestampedModel):
    content: str = Field(min_length=1, max_length=20_000)
    source: SeedSource = SeedSource.EXPLICIT
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    status: SeedStatus = SeedStatus.PENDING
    source_item_id: UUID | None = None
    last_used_at: datetime | None = None
    metadata: Metadata = Field(default_factory=dict)


class WonderScores(DomainModel):
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    surprise: float = Field(default=0.0, ge=0.0, le=1.0)
    personal_relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    coherence: float = Field(default=0.0, ge=0.0, le=1.0)
    generativity: float = Field(default=0.0, ge=0.0, le=1.0)
    explanatory_power: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_potential: float = Field(default=0.0, ge=0.0, le=1.0)
    cross_domain_value: float = Field(default=0.0, ge=0.0, le=1.0)
    redundancy: float = Field(default=0.0, ge=0.0, le=1.0)
    arbitrariness: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    total: float = Field(default=0.0, ge=0.0, le=1.0)


class Candidate(TimestampedModel):
    session_id: UUID
    candidate_type: WonderType
    statement: str = Field(min_length=1, max_length=10_000)
    explanation: str = Field(min_length=1, max_length=20_000)
    seed_id: UUID
    source_items: list[UUID] = Field(default_factory=list, min_length=1)
    operator: str = Field(min_length=1, max_length=100)
    wander_path: list[UUID] = Field(default_factory=list)
    scores: WonderScores | None = None
    status: CandidateStatus = CandidateStatus.GENERATED
    metadata: Metadata = Field(default_factory=dict)


class Wonder(TimestampedModel):
    session_id: UUID
    seed_id: UUID
    candidate_id: UUID | None = None
    type: WonderType
    statement: str = Field(min_length=1, max_length=10_000)
    explanation: str = Field(min_length=1, max_length=30_000)
    why_interesting: str = Field(min_length=1, max_length=20_000)
    source_items: list[UUID] = Field(default_factory=list, min_length=1)
    connection_path: list[UUID] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    scores: WonderScores
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: WonderStatus = WonderStatus.ACTIVE
    parent_wonder_id: UUID | None = None
    metadata: Metadata = Field(default_factory=dict)


class Feedback(TimestampedModel):
    wonder_id: UUID
    action: FeedbackAction
    value: float | None = Field(default=None, ge=-1.0, le=1.0)
    note: str | None = Field(default=None, max_length=5_000)
    metadata: Metadata = Field(default_factory=dict)
