import pytest

from wandermind.cognitive.embedding import HashEmbeddingAdapter
from wandermind.cognitive.engine import WanderEngine
from wandermind.cognitive.ingestion import IngestionService
from wandermind.cognitive.operators import OperatorSelector, default_operators
from wandermind.cognitive.scoring import ThresholdPolicy, WonderScorer
from wandermind.cognitive.state_machine import CognitiveStateMachine, InvalidStateTransition
from wandermind.models import CognitiveState, Seed, SessionStatus, WanderBudget
from wandermind.repositories import InMemoryRepositoryBundle


def test_state_machine_accepts_flow_and_rejects_invalid_transition() -> None:
    machine = CognitiveStateMachine()
    assert machine.transition(CognitiveState.SEEDING) is CognitiveState.SEEDING
    assert machine.transition(CognitiveState.WANDER) is CognitiveState.WANDER
    with pytest.raises(InvalidStateTransition):
        machine.transition(CognitiveState.SURFACE)


@pytest.mark.asyncio
async def test_deterministic_wander_produces_trace_and_wonder() -> None:
    repositories = InMemoryRepositoryBundle()
    embedding = HashEmbeddingAdapter(48)
    ingestion = IngestionService(repositories.knowledge, embedding)
    for title, content in [
        (
            "Agent scheduler",
            "Agent systems allocate compute, memory, and attention with feedback loops.",
        ),
        ("Operating systems", "Operating systems schedule processes and protect scarce resources."),
        (
            "Organizations",
            "Organizations allocate authority, budgets, and attention through governance.",
        ),
        ("Ecology", "Ecological niches allocate resources through competition and adaptation."),
    ]:
        await ingestion.ingest_text(content, title=title)
    seed = Seed(content="Could agent governance emerge from resource scheduling?", priority=1.0)
    await repositories.seeds.create(seed)
    scorer = WonderScorer(
        embedding,
        thresholds=ThresholdPolicy(reject_below=0.05, explore_above=0.1, surface_above=0.2),
    )
    engine = WanderEngine(
        repositories,
        embedding,
        OperatorSelector(default_operators()),
        scorer,
    )

    result = await engine.run(seed, WanderBudget(max_steps=12, max_candidates=3))

    assert result.session.status is SessionStatus.COMPLETED
    assert result.candidates
    assert result.wonders
    assert result.session.trace.steps
    assert result.session.trace.final_wonder_ids == [result.wonders[0].id]
    assert result.session.trace.stop_reason == "high_value_found"


@pytest.mark.asyncio
async def test_wander_stops_cleanly_with_insufficient_knowledge() -> None:
    repositories = InMemoryRepositoryBundle()
    embedding = HashEmbeddingAdapter(32)
    seed = Seed(content="A lonely seed")
    await repositories.seeds.create(seed)
    engine = WanderEngine(
        repositories,
        embedding,
        OperatorSelector(default_operators()),
        WonderScorer(embedding),
    )

    result = await engine.run(seed)

    assert result.session.status is SessionStatus.STOPPED
    assert result.session.trace.stop_reason == "insufficient_knowledge"
    assert not result.wonders


@pytest.mark.asyncio
async def test_wander_records_patch_switches_and_honors_switch_budget() -> None:
    repositories = InMemoryRepositoryBundle()
    embedding = HashEmbeddingAdapter(48)
    ingestion = IngestionService(repositories.knowledge, embedding)
    for title, content, domain in [
        ("Ecology feedback", "Local feedback stabilizes ecological demand.", "ecology"),
        ("Ecology recovery", "Diverse recovery paths preserve ecological slack.", "ecology"),
        ("Queue pressure", "Software queues signal overload through backpressure.", "software"),
        ("Circuit breaker", "Circuit breakers isolate cascading software faults.", "software"),
    ]:
        await ingestion.ingest_text(content, title=title, metadata={"domain": domain})
    seed = Seed(content="Compare ecological recovery with software overload control.")
    await repositories.seeds.create(seed)
    engine = WanderEngine(
        repositories,
        embedding,
        OperatorSelector(default_operators()),
        WonderScorer(embedding, thresholds=ThresholdPolicy(surface_above=1.0)),
    )

    result = await engine.run(
        seed,
        WanderBudget(max_steps=3, max_candidates=3, max_patch_switches=1),
    )
    movement_steps = [
        step
        for step in result.session.trace.steps
        if step.action in {"patch_switch", "local_wander"}
    ]

    assert 2 <= len(result.candidates) <= 3
    assert sum(step.action == "patch_switch" for step in movement_steps) <= 1
    assert any(step.metadata.get("movement") == "controlled_remote_jump" for step in movement_steps)

    timed_seed = Seed(content="A second seed with no available wall-clock budget.")
    await repositories.seeds.create(timed_seed)
    timed_result = await engine.run(
        timed_seed,
        WanderBudget(max_steps=3, max_candidates=3, time_budget_seconds=0.000001),
    )
    assert timed_result.candidates == []
    assert timed_result.session.trace.stop_reason == "time_budget_exhausted"
