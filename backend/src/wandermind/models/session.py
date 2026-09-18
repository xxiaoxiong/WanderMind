from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from wandermind.models.base import DomainModel, IdentifiedModel, Metadata, utc_now
from wandermind.models.enums import CognitiveState, SessionStatus


class WanderBudget(DomainModel):
    max_steps: int = Field(default=8, ge=1, le=100)
    max_patch_switches: int = Field(default=2, ge=0, le=20)
    max_candidates: int = Field(default=5, ge=1, le=100)
    max_runtime_calls: int = Field(default=4, ge=0, le=100)
    time_budget_seconds: float = Field(default=30.0, gt=0, le=3_600)


class WanderStep(IdentifiedModel):
    index: int = Field(ge=0)
    state: CognitiveState
    action: str = Field(min_length=1, max_length=200)
    reason: str = Field(default="", max_length=2_000)
    item_ids: list[UUID] = Field(default_factory=list)
    operator: str | None = Field(default=None, max_length=100)
    distance: float | None = Field(default=None, ge=0.0, le=2.0)
    novelty_gain: float | None = Field(default=None, ge=0.0, le=1.0)
    relevance: float | None = Field(default=None, ge=0.0, le=1.0)
    collision_score: float | None = Field(default=None, ge=0.0, le=1.0)
    candidate_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Metadata = Field(default_factory=dict)


class WanderTrace(DomainModel):
    steps: list[WanderStep] = Field(default_factory=list)
    patches: list[UUID] = Field(default_factory=list)
    operators: list[str] = Field(default_factory=list)
    candidate_ids: list[UUID] = Field(default_factory=list)
    final_wonder_ids: list[UUID] = Field(default_factory=list)
    stop_reason: str | None = None


class WanderSession(IdentifiedModel):
    seed_id: UUID
    state: CognitiveState = CognitiveState.IDLE
    budget: WanderBudget = Field(default_factory=WanderBudget)
    status: SessionStatus = SessionStatus.PENDING
    trace: WanderTrace = Field(default_factory=WanderTrace)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: Metadata = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_terminal_timestamps(self) -> WanderSession:
        terminal = {SessionStatus.COMPLETED, SessionStatus.STOPPED, SessionStatus.FAILED}
        if self.status in terminal and self.ended_at is None:
            raise ValueError("terminal session requires ended_at")
        return self
