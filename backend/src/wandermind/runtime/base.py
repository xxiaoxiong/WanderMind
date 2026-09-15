from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from wandermind.models.base import DomainModel, TimestampedModel, utc_now
from wandermind.models.enums import RuntimeSessionStatus


class SandboxMode(StrEnum):
    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"


class RuntimeErrorBase(RuntimeError):
    retryable = False


class RuntimeUnavailableError(RuntimeErrorBase):
    pass


class RuntimeTimeoutError(RuntimeErrorBase):
    retryable = True


class RuntimeInterruptedError(RuntimeErrorBase):
    pass


class RuntimeMalformedOutputError(RuntimeErrorBase):
    retryable = True


class RuntimeExecutionError(RuntimeErrorBase):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class RuntimeSession(TimestampedModel):
    provider: str
    purpose: str
    external_session_id: str | None = None
    status: RuntimeSessionStatus = RuntimeSessionStatus.ACTIVE
    wander_session_id: UUID | None = None
    last_used_at: datetime = Field(default_factory=utc_now)
    cost: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeTask(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    prompt: str = Field(min_length=1, max_length=100_000)
    output_schema: dict[str, Any]
    sandbox: SandboxMode = SandboxMode.READ_ONLY
    timeout_seconds: float = Field(default=60.0, gt=0, le=3_600)
    workspace_roots: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeTaskResult(DomainModel):
    session_id: UUID
    external_turn_id: str | None = None
    text: str
    structured: dict[str, Any]
    usage: dict[str, Any] = Field(default_factory=dict)


class RuntimeStreamEvent(DomainModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentRuntimeAdapter(ABC):
    @abstractmethod
    async def start_session(self, purpose: str) -> RuntimeSession:
        raise NotImplementedError

    @abstractmethod
    async def resume_session(self, session: RuntimeSession) -> RuntimeSession:
        raise NotImplementedError

    @abstractmethod
    async def run_task(self, session: RuntimeSession, task: RuntimeTask) -> RuntimeTaskResult:
        raise NotImplementedError

    @abstractmethod
    def stream_task(
        self,
        session: RuntimeSession,
        task: RuntimeTask,
    ) -> AsyncIterator[RuntimeStreamEvent]:
        raise NotImplementedError

    @abstractmethod
    async def interrupt(self, session: RuntimeSession) -> None:
        raise NotImplementedError

    @abstractmethod
    async def close_session(self, session: RuntimeSession) -> None:
        raise NotImplementedError


async def run_with_retry(
    adapter: AgentRuntimeAdapter,
    session: RuntimeSession,
    task: RuntimeTask,
    *,
    max_retries: int,
    backoff_seconds: float = 0.05,
) -> RuntimeTaskResult:
    import asyncio

    attempts = 0
    while True:
        try:
            return await adapter.run_task(session, task)
        except RuntimeErrorBase as error:
            if not error.retryable or attempts >= max_retries:
                raise
            attempts += 1
            await asyncio.sleep(backoff_seconds * attempts)
