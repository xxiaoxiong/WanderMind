from uuid import uuid4

import pytest

from wandermind.application.evaluation import CriticVerdict, EvidenceOutput, ExplorerOutput
from wandermind.application.explore_service import (
    CriticService,
    DeepEvaluationService,
    EvidenceService,
    ExplorerService,
)
from wandermind.infrastructure.security import redact_secrets
from wandermind.infrastructure.tracked_runtime import TrackedRuntimeAdapter
from wandermind.models import Candidate, KnowledgeItem, WonderType
from wandermind.repositories.in_memory import InMemoryRuntimeSessionRepository
from wandermind.runtime import (
    MockRuntimeAdapter,
    MockRuntimeMode,
    RuntimeInterruptedError,
    RuntimeMalformedOutputError,
    RuntimeTask,
    RuntimeTimeoutError,
    run_with_retry,
)
from wandermind.runtime.codex_app_server import CodexRuntimeAdapter, _parse_structured


def candidate() -> Candidate:
    return Candidate(
        session_id=uuid4(),
        candidate_type=WonderType.CONNECTION,
        statement="Agent scheduling may resemble organizational governance.",
        explanation="Both allocate scarce resources through feedback.",
        seed_id=uuid4(),
        source_items=[uuid4(), uuid4()],
        operator="analogy",
    )


def test_secret_redaction_is_recursive() -> None:
    assert redact_secrets(
        {"nested": {"api_token": "hidden"}, "items": [{"password": "hidden"}]}
    ) == {"nested": {"api_token": "[REDACTED]"}, "items": [{"password": "[REDACTED]"}]}


@pytest.mark.asyncio
async def test_mock_runtime_lifecycle_stream_and_retry() -> None:
    runtime = MockRuntimeAdapter(response={"value": "ok"}, fail_times=1)
    session = await runtime.start_session("test")
    task = RuntimeTask(
        prompt="return data",
        output_schema={
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "string"}},
        },
    )

    result = await run_with_retry(runtime, session, task, max_retries=1, backoff_seconds=0)

    assert result.structured == {"value": "ok"}
    assert runtime.calls == 2
    resumed = await runtime.resume_session(session)
    events = [event.type async for event in runtime.stream_task(resumed, task)]
    assert events == ["started", "delta", "completed"]
    await runtime.close_session(session)


@pytest.mark.asyncio
async def test_tracked_runtime_persists_session_usage_and_linkage() -> None:
    repository = InMemoryRuntimeSessionRepository()
    runtime = TrackedRuntimeAdapter(
        MockRuntimeAdapter(response={"value": "ok"}),
        repository,
    )
    wander_session_id = uuid4()
    session = await runtime.start_session("test")
    result = await runtime.run_task(
        session,
        RuntimeTask(
            prompt="return data",
            output_schema={
                "type": "object",
                "required": ["value"],
                "properties": {"value": {"type": "string"}},
            },
            metadata={"wander_session_id": str(wander_session_id)},
        ),
    )
    await runtime.close_session(session)

    stored = await repository.get(session.id)
    assert result.usage["provider"] == "mock"
    assert stored is not None
    assert stored.wander_session_id == wander_session_id
    assert stored.cost["runtime_calls"] == 1
    assert stored.cost["duration_seconds"] >= 0
    assert stored.status.value == "closed"


@pytest.mark.asyncio
async def test_mock_runtime_failure_modes() -> None:
    task = RuntimeTask(prompt="x", output_schema={"type": "object"})
    timeout_runtime = MockRuntimeAdapter(mode=MockRuntimeMode.TIMEOUT)
    timeout_session = await timeout_runtime.start_session("timeout")
    with pytest.raises(RuntimeTimeoutError):
        await timeout_runtime.run_task(timeout_session, task)

    malformed_runtime = MockRuntimeAdapter(response={"wrong": True})
    malformed_session = await malformed_runtime.start_session("malformed")
    strict_task = RuntimeTask(
        prompt="x",
        output_schema={"type": "object", "required": ["value"]},
    )
    with pytest.raises(RuntimeMalformedOutputError):
        await malformed_runtime.run_task(malformed_session, strict_task)

    interrupted_runtime = MockRuntimeAdapter()
    interrupted_session = await interrupted_runtime.start_session("interrupt")
    await interrupted_runtime.interrupt(interrupted_session)
    with pytest.raises(RuntimeInterruptedError):
        await interrupted_runtime.run_task(interrupted_session, task)


def test_codex_structured_parser_and_sandbox_default() -> None:
    schema = {
        "type": "object",
        "required": ["answer"],
        "properties": {"answer": {"type": "string"}},
    }

    assert _parse_structured('{"answer":"yes"}', schema) == {"answer": "yes"}
    with pytest.raises(RuntimeMalformedOutputError):
        _parse_structured('{"wrong":true}', schema)
    adapter = CodexRuntimeAdapter(executable="codex", cwd=".")
    task = RuntimeTask(prompt="x", output_schema=schema)
    assert adapter._sandbox_policy(task) == {"type": "readOnly", "networkAccess": False}


@pytest.mark.asyncio
async def test_explorer_evidence_and_critic_validate_outputs() -> None:
    item = KnowledgeItem(title="Context", content="Context content")
    explorer_runtime = MockRuntimeAdapter(
        response=ExplorerOutput(
            expanded_idea="Expanded",
            implications=["Implication"],
            follow_up_questions=["Question?"],
        ).model_dump(mode="json")
    )
    explorer = await ExplorerService(explorer_runtime).explore(candidate(), [item])
    assert explorer.expanded_idea == "Expanded"
    assert all(session.status.value == "closed" for session in explorer_runtime.sessions.values())

    evidence_runtime = MockRuntimeAdapter(
        response=EvidenceOutput(
            supporting_evidence=["Unsupported text"],
            source_refs=[],
            uncertainty=0.2,
        ).model_dump(mode="json")
    )
    evidence = await EvidenceService(evidence_runtime).collect(candidate(), [item])
    assert evidence.supporting_evidence == []
    assert evidence.uncertainty >= 0.8
    assert all(session.status.value == "closed" for session in evidence_runtime.sessions.values())

    invented_reference_runtime = MockRuntimeAdapter(
        response=EvidenceOutput(
            supporting_evidence=["Invented support"],
            source_refs=["https://invented.example/source"],
            uncertainty=0.1,
        ).model_dump(mode="json")
    )
    invented_reference = await EvidenceService(invented_reference_runtime).collect(
        candidate(),
        [
            KnowledgeItem(
                title="Sourced context",
                content="Context content",
                source_ref="https://trusted.example/source",
            )
        ],
    )
    assert invented_reference.source_refs == []
    assert invented_reference.supporting_evidence == []
    assert invented_reference.uncertainty >= 0.8

    critic_runtime = MockRuntimeAdapter(mode=MockRuntimeMode.FAILURE)
    critic = await CriticService(critic_runtime).critique(candidate(), evidence)
    assert critic.verdict is CriticVerdict.REJECT
    assert critic.factual_risk == 1.0
    assert all(session.status.value == "closed" for session in critic_runtime.sessions.values())


@pytest.mark.asyncio
async def test_deep_evaluation_honors_zero_runtime_call_budget() -> None:
    runtime = MockRuntimeAdapter()
    service = DeepEvaluationService(
        ExplorerService(runtime),
        EvidenceService(runtime),
        CriticService(runtime),
    )

    result = await service.evaluate(
        candidate(),
        [KnowledgeItem(title="Context", content="Context content")],
        max_runtime_calls=0,
    )

    assert runtime.calls == 0
    assert result.explorer is None
    assert result.evidence.error == "runtime_budget_exhausted"
    assert result.critic.verdict is CriticVerdict.REJECT
