from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from wandermind.models.base import Metadata, TimestampedModel, utc_now
from wandermind.models.enums import AutopilotStatus
from wandermind.models.session import WanderBudget


def default_autopilot_budget() -> WanderBudget:
    return WanderBudget(
        max_steps=32,
        max_patch_switches=12,
        max_candidates=12,
        min_candidates=5,
        target_wonders=3,
        max_stagnant_candidates=8,
        stop_on_first_wonder=False,
        max_runtime_calls=24,
        time_budget_seconds=1_800,
    )


class AutopilotCampaign(TimestampedModel):
    objective: str = Field(min_length=1, max_length=20_000)
    status: AutopilotStatus = AutopilotStatus.ACTIVE
    budget: WanderBudget = Field(default_factory=default_autopilot_budget)
    current_session_id: UUID | None = None
    cycles_started: int = Field(default=0, ge=0)
    cycles_completed: int = Field(default=0, ge=0)
    total_candidates: int = Field(default=0, ge=0)
    total_wonders: int = Field(default=0, ge=0)
    total_runtime_calls: int = Field(default=0, ge=0)
    promoted_knowledge_count: int = Field(default=0, ge=0)
    consecutive_failures: int = Field(default=0, ge=0)
    started_at: datetime = Field(default_factory=utc_now)
    last_cycle_started_at: datetime | None = None
    last_cycle_completed_at: datetime | None = None
    next_cycle_at: datetime | None = None
    last_error: str | None = Field(default=None, max_length=2_000)
    metadata: Metadata = Field(default_factory=dict)
