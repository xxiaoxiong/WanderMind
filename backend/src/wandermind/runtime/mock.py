from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from copy import deepcopy
from enum import StrEnum
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate

from wandermind.models.enums import RuntimeSessionStatus
from wandermind.runtime.base import (
    AgentRuntimeAdapter,
    RuntimeExecutionError,
    RuntimeInterruptedError,
    RuntimeMalformedOutputError,
    RuntimeSession,
    RuntimeStreamEvent,
    RuntimeTask,
    RuntimeTaskResult,
    RuntimeTimeoutError,
)


class MockRuntimeMode(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    MALFORMED = "malformed"


class MockRuntimeAdapter(AgentRuntimeAdapter):
    def __init__(
        self,
        *,
        mode: MockRuntimeMode = MockRuntimeMode.SUCCESS,
        response: dict[str, Any] | None = None,
        responses: dict[str, dict[str, Any]] | None = None,
        fail_times: int = 0,
    ) -> None:
        self.mode = mode
        self.response = response or {"status": "ok"}
        self.responses = responses or {}
        self.fail_times = fail_times
        self.calls = 0
        self.sessions: dict[str, RuntimeSession] = {}

    async def start_session(self, purpose: str) -> RuntimeSession:
        session = RuntimeSession(provider="mock", purpose=purpose)
        session.external_session_id = str(session.id)
        self.sessions[str(session.id)] = session
        return session

    async def resume_session(self, session: RuntimeSession) -> RuntimeSession:
        stored = self.sessions.get(str(session.id))
        if stored is None or stored.status is RuntimeSessionStatus.CLOSED:
            raise RuntimeExecutionError("mock session cannot be resumed")
        stored.status = RuntimeSessionStatus.ACTIVE
        return stored

    async def run_task(self, session: RuntimeSession, task: RuntimeTask) -> RuntimeTaskResult:
        started = time.perf_counter()
        self._ensure_active(session)
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeExecutionError("transient mock failure", retryable=True)
        if self.mode is MockRuntimeMode.FAILURE:
            raise RuntimeExecutionError("mock runtime failure")
        if self.mode is MockRuntimeMode.TIMEOUT:
            await asyncio.sleep(0)
            raise RuntimeTimeoutError("mock runtime timeout")
        if self.mode is MockRuntimeMode.MALFORMED:
            raise RuntimeMalformedOutputError("mock malformed structured output")
        response = self.responses.get(session.purpose, self.response)
        try:
            validate(instance=response, schema=task.output_schema)
        except JsonSchemaValidationError as error:
            raise RuntimeMalformedOutputError(
                f"mock output failed schema validation: {error.message}"
            ) from error
        result = RuntimeTaskResult(
            session_id=session.id,
            external_turn_id=f"mock-turn-{self.calls}",
            text="mock structured result",
            structured=deepcopy(response),
            usage={
                "runtime_calls": 1,
                "provider": session.provider,
                "duration_seconds": time.perf_counter() - started,
            },
        )
        session.status = RuntimeSessionStatus.COMPLETED
        return result

    async def stream_task(
        self,
        session: RuntimeSession,
        task: RuntimeTask,
    ) -> AsyncIterator[RuntimeStreamEvent]:
        self._ensure_active(session)
        yield RuntimeStreamEvent(type="started", data={"session_id": str(session.id)})
        result = await self.run_task(session, task)
        yield RuntimeStreamEvent(type="delta", data={"text": result.text})
        yield RuntimeStreamEvent(type="completed", data=result.model_dump(mode="json"))

    async def interrupt(self, session: RuntimeSession) -> None:
        self._ensure_active(session)
        session.status = RuntimeSessionStatus.INTERRUPTED

    async def close_session(self, session: RuntimeSession) -> None:
        session.status = RuntimeSessionStatus.CLOSED

    def _ensure_active(self, session: RuntimeSession) -> None:
        if session.status is RuntimeSessionStatus.INTERRUPTED:
            raise RuntimeInterruptedError("runtime session was interrupted")
        if session.status is RuntimeSessionStatus.CLOSED:
            raise RuntimeExecutionError("runtime session is closed")
