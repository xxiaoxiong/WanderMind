from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from wandermind.api import create_app
from wandermind.application.autopilot_quality import AutopilotQualityPolicy
from wandermind.application.container import ApplicationContainer, in_memory_container
from wandermind.infrastructure.config import Settings
from wandermind.models import (
    AutopilotStatus,
    KnowledgeStatus,
    SessionStatus,
    WanderBudget,
    Wonder,
    WonderScores,
    WonderStatus,
    WonderType,
)


async def _wait_until(
    check: Callable[[], Awaitable[bool]],
    *,
    deadline_seconds: float = 3.0,
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
        autopilot_cycle_delay_seconds=0,
    )


def _mock_runtime_quality_policy() -> AutopilotQualityPolicy:
    return AutopilotQualityPolicy(
        minimum_total=0.5,
        minimum_confidence=0.5,
        minimum_coherence=0.55,
        maximum_arbitrariness=0.9,
    )


async def _add_knowledge(container: ApplicationContainer) -> None:
    ingestion = container.ingestion
    for title, content in [
        ("Ecology", "Distributed ecological feedback protects scarce resources."),
        ("Queues", "Backpressure prevents distributed workers from overload."),
        ("Cities", "Neighborhood sensors distribute early warning capacity."),
    ]:
        await ingestion.ingest_text(content, title=title)


def _reviewed_wonder(*, factual_risk: float = 0.2) -> Wonder:
    return Wonder(
        session_id=uuid4(),
        seed_id=uuid4(),
        type=WonderType.HYPOTHESIS,
        statement="Local feedback may reduce overload if the proposed mechanism survives testing.",
        explanation="The claim is framed as a falsifiable structural-transfer hypothesis.",
        why_interesting="It creates a measurable comparison without claiming equivalence.",
        source_items=[uuid4(), uuid4()],
        supporting_evidence=["Both sources describe observable local feedback."],
        counter_evidence=["Different delays could invalidate the transfer."],
        questions=["Does earlier feedback reduce peak queue depth?"],
        scores=WonderScores(
            novelty=0.8,
            surprise=0.7,
            personal_relevance=0.7,
            coherence=0.8,
            generativity=0.8,
            explanatory_power=0.8,
            evidence_potential=0.8,
            cross_domain_value=0.8,
            redundancy=0.2,
            arbitrariness=0.2,
            hallucination_risk=0.1,
            total=0.75,
        ),
        confidence=0.75,
        metadata={
            "promotion_basis": "runtime_review",
            "runtime_review": {
                "verdict": "pass",
                "uncertainty": 0.4,
                "factual_risk": factual_risk,
            },
        },
    )


def test_autopilot_quality_gate_requires_low_risk_independent_review() -> None:
    policy = AutopilotQualityPolicy()

    accepted = policy.evaluate(_reviewed_wonder())
    rejected = policy.evaluate(_reviewed_wonder(factual_risk=0.8))

    assert accepted.accepted is True
    assert accepted.reasons == ()
    assert rejected.accepted is False
    assert "factual_risk_too_high" in rejected.reasons


@pytest.mark.asyncio
async def test_autopilot_quarantines_previous_low_quality_feedback() -> None:
    container = in_memory_container(_settings())
    wonder = _reviewed_wonder(factual_risk=0.8)
    await container.repositories.wonders.create(wonder)
    item = await container.ingestion.ingest_text(
        "A previously promoted but weak autonomous hypothesis.",
        title="Weak autonomous hypothesis",
        source="autopilot",
        source_ref=f"wonder://{wonder.id}",
        metadata={"source_wonder_id": str(wonder.id)},
    )
    wonder.metadata["autopilot_promoted_knowledge_id"] = str(item.id)
    await container.repositories.wonders.update(wonder)

    await container.autopilot.start()

    reconciled_item = await container.repositories.knowledge.get(item.id)
    reconciled_wonder = await container.repositories.wonders.get(wonder.id)
    assert reconciled_item is not None
    assert reconciled_wonder is not None
    assert reconciled_item.status is KnowledgeStatus.REJECTED
    assert reconciled_item.metadata["epistemic_status"] == "quality_rejected"
    assert reconciled_wonder.status is WonderStatus.INCUBATING
    assert reconciled_wonder.metadata["autopilot_promotion_retracted"] is True
    await container.autopilot.shutdown()


@pytest.mark.asyncio
async def test_autopilot_runs_cycles_and_feeds_wonders_back_into_knowledge() -> None:
    container = in_memory_container(_settings())
    container.autopilot.quality_policy = _mock_runtime_quality_policy()
    await _add_knowledge(container)
    budget = WanderBudget(
        max_steps=12,
        max_patch_switches=4,
        max_candidates=2,
        min_candidates=2,
        target_wonders=1,
        max_stagnant_candidates=3,
        stop_on_first_wonder=False,
        max_runtime_calls=4,
        time_budget_seconds=30,
    )

    started = await container.autopilot.start_or_resume(
        objective="Continuously find falsifiable cross-domain mechanisms.",
        budget=budget,
    )
    assert started.campaign is not None
    assert started.campaign.status is AutopilotStatus.ACTIVE
    assert started.current_session is not None

    async def first_cycle_terminal() -> bool:
        snapshot = await container.autopilot.snapshot()
        return bool(
            snapshot.current_session
            and snapshot.current_session.status
            in {SessionStatus.COMPLETED, SessionStatus.STOPPED, SessionStatus.FAILED}
        )

    await _wait_until(first_cycle_terminal)
    await container.autopilot.tick()
    completed = await container.autopilot.snapshot()
    assert completed.campaign is not None
    assert completed.campaign.cycles_completed == 1
    assert completed.campaign.total_candidates >= 2
    assert completed.campaign.total_wonders >= 1
    assert completed.campaign.promoted_knowledge_count >= 1
    assert completed.generated_knowledge_count >= 1
    assert completed.knowledge_count > 3

    await container.autopilot.tick()
    second_cycle = await container.autopilot.snapshot()
    assert second_cycle.campaign is not None
    assert second_cycle.campaign.cycles_started == 2
    assert second_cycle.current_seed is not None
    paired_ids = second_cycle.current_seed.metadata["paired_item_ids"]
    knowledge = await container.repositories.knowledge.list(offset=0, limit=100)
    generated_ids = {str(item.id) for item in knowledge if item.source == "autopilot"}
    assert generated_ids.intersection(paired_ids)

    paused = await container.autopilot.pause()
    assert paused.campaign is not None
    assert paused.campaign.status is AutopilotStatus.PAUSED
    assert paused.current_session is None
    await container.wander_coordinator.shutdown()


@pytest.mark.asyncio
async def test_autopilot_supervisor_continuously_chains_cycles_without_manual_ticks() -> None:
    container = in_memory_container(_settings())
    container.autopilot.quality_policy = _mock_runtime_quality_policy()
    await _add_knowledge(container)
    container.autopilot.poll_interval_seconds = 0.01
    container.autopilot.cycle_delay_seconds = 0
    container.autopilot.budget = WanderBudget(
        max_steps=8,
        max_patch_switches=3,
        max_candidates=2,
        min_candidates=2,
        target_wonders=1,
        max_stagnant_candidates=3,
        stop_on_first_wonder=False,
        max_runtime_calls=4,
        time_budget_seconds=30,
    )

    await container.autopilot.start()
    await container.autopilot.start_or_resume()

    async def two_cycles_committed() -> bool:
        snapshot = await container.autopilot.snapshot()
        return bool(
            snapshot.worker_running
            and snapshot.campaign
            and snapshot.campaign.cycles_completed >= 2
            and snapshot.campaign.cycles_started >= 3
        )

    await _wait_until(two_cycles_committed)
    paused = await container.autopilot.pause()
    assert paused.campaign is not None
    assert paused.campaign.cycles_completed >= 2
    assert paused.campaign.total_candidates >= 4
    assert paused.campaign.promoted_knowledge_count >= 1
    await container.autopilot.shutdown()
    await container.wander_coordinator.shutdown()


@pytest.mark.asyncio
async def test_autopilot_api_exposes_persistent_control_and_progress() -> None:
    settings = _settings()
    container = in_memory_container(settings)
    await _add_knowledge(container)
    app = create_app(settings, container=container)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        started = await client.post(
            "/api/v1/autopilot/start",
            json={
                "objective": "Keep exploring without supervision.",
                "budget": {
                    "max_steps": 8,
                    "max_patch_switches": 3,
                    "max_candidates": 2,
                    "min_candidates": 2,
                    "target_wonders": 1,
                    "max_stagnant_candidates": 3,
                    "stop_on_first_wonder": False,
                    "max_runtime_calls": 4,
                    "time_budget_seconds": 30,
                },
            },
        )
        assert started.status_code == 200
        assert started.json()["campaign"]["status"] == "active"
        assert started.json()["current_session"]["status"] in {"pending", "running"}

        status = await client.get("/api/v1/autopilot/status")
        assert status.status_code == 200
        assert status.json()["campaign"]["cycles_started"] == 1

        paused = await client.post("/api/v1/autopilot/pause")
        assert paused.status_code == 200
        assert paused.json()["campaign"]["status"] == "paused"
        assert paused.json()["current_session"] is None
    await container.wander_coordinator.shutdown()
