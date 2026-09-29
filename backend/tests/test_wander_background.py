from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from wandermind.api import create_app
from wandermind.application.container import in_memory_container
from wandermind.infrastructure.config import Settings
from wandermind.infrastructure.tracked_runtime import TrackedRuntimeAdapter
from wandermind.models import Seed, SessionStatus, WanderBudget
from wandermind.runtime.base import RuntimeSession, RuntimeTask, RuntimeTaskResult
from wandermind.runtime.mock import MockRuntimeAdapter


async def _wait_until(
    check: Callable[[], Awaitable[bool]],
    *,
    deadline_seconds: float = 2.0,
) -> None:
    deadline = perf_counter() + deadline_seconds
    while perf_counter() < deadline:
        if await check():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not reached before timeout")


def _settings() -> Settings:
    return Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        auto_create_schema=False,
        wonder_threshold=0.0,
        cheap_score_threshold=0.0,
    )


async def _add_knowledge(client: AsyncClient) -> None:
    for title, content in [
        ("Ecology", "Distributed ecological feedback protects scarce resources."),
        ("Queues", "Backpressure prevents distributed workers from overload."),
        ("Cities", "Neighborhood sensors distribute early warning capacity."),
        ("Markets", "Inventory buffers reduce propagation of demand shocks."),
    ]:
        response = await client.post(
            "/api/v1/knowledge",
            json={"title": title, "content": content},
        )
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_background_wander_returns_immediately_checkpoints_and_stops() -> None:
    settings = _settings()
    container = in_memory_container(settings)
    tracked_runtime = container.runtime
    assert isinstance(tracked_runtime, TrackedRuntimeAdapter)
    delegate = tracked_runtime.delegate
    assert isinstance(delegate, MockRuntimeAdapter)
    original_run_task = delegate.run_task

    async def delayed_run_task(
        session: RuntimeSession,
        task: RuntimeTask,
    ) -> RuntimeTaskResult:
        await asyncio.sleep(0.25)
        return await original_run_task(session, task)

    delegate.run_task = delayed_run_task  # type: ignore[method-assign]
    app = create_app(settings, container=container)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _add_knowledge(client)
        started = perf_counter()
        response = await client.post(
            "/api/v1/wander/start",
            json={
                "content": "How can distributed systems absorb overload?",
                "budget": {
                    "max_steps": 8,
                    "max_candidates": 4,
                    "min_candidates": 3,
                    "target_wonders": 2,
                    "stop_on_first_wonder": False,
                    "max_runtime_calls": 8,
                    "time_budget_seconds": 30,
                },
            },
        )
        elapsed = perf_counter() - started
        assert response.status_code == 202
        assert elapsed < 0.2
        session_id = UUID(response.json()["id"])

        async def has_live_checkpoint() -> bool:
            session = await container.repositories.sessions.get(session_id)
            return bool(
                session
                and session.status is SessionStatus.RUNNING
                and session.trace.steps
                and container.wander_coordinator.is_active(session_id)
            )

        await _wait_until(has_live_checkpoint)
        stopped = await client.post(f"/api/v1/wander/{session_id}/stop")
        assert stopped.status_code == 200
        assert stopped.json()["status"] == "stopped"
        assert stopped.json()["trace"]["stop_reason"] == "manual_stop"
        assert not container.wander_coordinator.is_active(session_id)

        stream = await client.get(f"/api/v1/wander/{session_id}/stream")
        assert "event: wander_step" in stream.text
        assert "event: completed" in stream.text
        assert '"status": "stopped"' in stream.text


@pytest.mark.asyncio
async def test_coordinator_recovers_pending_session() -> None:
    settings = _settings()
    container = in_memory_container(settings)
    for title, content in [
        ("Ecology", "Ecological systems use local feedback and diversity."),
        ("Software", "Software systems use local backpressure and redundancy."),
    ]:
        await container.ingestion.ingest_text(content, title=title)
    seed = await container.repositories.seeds.create(Seed(content="Find a robust shared mechanism."))
    session = await container.wander_engine.create_session(
        seed,
        WanderBudget(max_candidates=1, max_runtime_calls=2, time_budget_seconds=10),
    )

    await container.wander_coordinator.recover()

    async def is_terminal() -> bool:
        stored = await container.repositories.sessions.get(session.id)
        return bool(
            stored
            and stored.status
            in {SessionStatus.COMPLETED, SessionStatus.STOPPED, SessionStatus.FAILED}
        )

    await _wait_until(is_terminal)
    recovered = await container.repositories.sessions.get(session.id)
    assert recovered is not None
    assert recovered.status is SessionStatus.COMPLETED
    assert recovered.metadata["recovered_after_restart"] is True
    assert recovered.trace.steps
    await container.wander_coordinator.shutdown()
