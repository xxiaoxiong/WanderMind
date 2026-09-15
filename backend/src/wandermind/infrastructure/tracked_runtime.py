from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import structlog

from wandermind.infrastructure.observability import RUNTIME_CALLS
from wandermind.models.base import utc_now
from wandermind.repositories.protocols import RuntimeSessionRepository
from wandermind.runtime.base import (
    AgentRuntimeAdapter,
    RuntimeSession,
    RuntimeStreamEvent,
    RuntimeTask,
    RuntimeTaskResult,
)


class TrackedRuntimeAdapter(AgentRuntimeAdapter):
    def __init__(
        self,
        delegate: AgentRuntimeAdapter,
        repository: RuntimeSessionRepository,
    ) -> None:
        self.delegate = delegate
        self.repository = repository

    async def start_session(self, purpose: str) -> RuntimeSession:
        session = await self.delegate.start_session(purpose)
        await self.repository.create(session)
        return session

    async def resume_session(self, session: RuntimeSession) -> RuntimeSession:
        resumed = await self.delegate.resume_session(session)
        self._touch(resumed)
        await self.repository.update(resumed)
        return resumed

    async def run_task(self, session: RuntimeSession, task: RuntimeTask) -> RuntimeTaskResult:
        self._bind_wander_session(session, task)
        started = time.perf_counter()
        try:
            result = await self.delegate.run_task(session, task)
        except Exception as error:
            duration = time.perf_counter() - started
            self._record_failure(session, duration, error)
            await self.repository.update(session)
            RUNTIME_CALLS.labels(session.purpose, "failed").inc()
            structlog.get_logger("runtime").warning(
                "runtime_task_failed",
                runtime_session_id=str(session.id),
                task_id=str(task.id),
                wander_session_id=str(session.wander_session_id),
                provider=session.provider,
                purpose=session.purpose,
                duration_seconds=duration,
                error_type=type(error).__name__,
            )
            raise
        duration = time.perf_counter() - started
        result.usage.setdefault("runtime_calls", 1)
        result.usage.setdefault("provider", session.provider)
        result.usage.setdefault("duration_seconds", duration)
        self._record_usage(session, result.usage)
        await self.repository.update(session)
        RUNTIME_CALLS.labels(session.purpose, "completed").inc()
        structlog.get_logger("runtime").info(
            "runtime_task_completed",
            runtime_session_id=str(session.id),
            task_id=str(task.id),
            wander_session_id=str(session.wander_session_id),
            provider=session.provider,
            purpose=session.purpose,
            duration_seconds=duration,
        )
        return result

    async def stream_task(
        self,
        session: RuntimeSession,
        task: RuntimeTask,
    ) -> AsyncIterator[RuntimeStreamEvent]:
        self._bind_wander_session(session, task)
        started = time.perf_counter()
        outcome = "failed"
        usage: dict[str, Any] = {}
        try:
            async for event in self.delegate.stream_task(session, task):
                if event.type == "completed":
                    raw_usage = event.data.get("usage", {})
                    if isinstance(raw_usage, dict):
                        usage = raw_usage
                    outcome = "completed"
                yield event
        finally:
            duration = time.perf_counter() - started
            usage.setdefault("runtime_calls", 1)
            usage.setdefault("provider", session.provider)
            usage.setdefault("duration_seconds", duration)
            self._record_usage(session, usage)
            await self.repository.update(session)
            RUNTIME_CALLS.labels(session.purpose, outcome).inc()

    async def interrupt(self, session: RuntimeSession) -> None:
        await self.delegate.interrupt(session)
        self._touch(session)
        await self.repository.update(session)

    async def close_session(self, session: RuntimeSession) -> None:
        await self.delegate.close_session(session)
        self._touch(session)
        await self.repository.update(session)

    def _bind_wander_session(self, session: RuntimeSession, task: RuntimeTask) -> None:
        raw_session_id = task.metadata.get("wander_session_id")
        if raw_session_id is None:
            return
        try:
            session.wander_session_id = UUID(str(raw_session_id))
        except ValueError:
            session.metadata["invalid_wander_session_id"] = str(raw_session_id)

    def _record_usage(self, session: RuntimeSession, usage: dict[str, Any]) -> None:
        for key in (
            "runtime_calls",
            "duration_seconds",
            "input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            value = usage.get(key)
            previous = session.cost.get(key, 0)
            if isinstance(value, int | float) and isinstance(previous, int | float):
                session.cost[key] = previous + value
        session.cost["provider"] = session.provider
        session.cost["last_usage"] = usage
        self._touch(session)

    def _record_failure(self, session: RuntimeSession, duration: float, error: Exception) -> None:
        session.cost["runtime_calls"] = int(session.cost.get("runtime_calls", 0)) + 1
        session.cost["duration_seconds"] = (
            float(session.cost.get("duration_seconds", 0.0)) + duration
        )
        session.cost["failures"] = int(session.cost.get("failures", 0)) + 1
        session.cost["provider"] = session.provider
        session.metadata["last_error"] = type(error).__name__
        self._touch(session)

    def _touch(self, session: RuntimeSession) -> None:
        now = utc_now()
        session.last_used_at = now
        session.updated_at = now
