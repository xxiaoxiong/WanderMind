from typing import Any

import pytest

from wandermind.cognitive.embedding import HashEmbeddingAdapter
from wandermind.cognitive.engine import WanderEngine
from wandermind.cognitive.ingestion import IngestionService
from wandermind.cognitive.operators import OperatorSelector, default_operators
from wandermind.cognitive.runtime_services import CandidateReviewResult
from wandermind.cognitive.scoring import ThresholdDecision, ThresholdPolicy, WonderScorer
from wandermind.cognitive.state_machine import CognitiveStateMachine, InvalidStateTransition
from wandermind.models import (
    Candidate,
    CognitiveState,
    KnowledgeItem,
    Seed,
    SessionStatus,
    WanderBudget,
)
from wandermind.repositories import InMemoryRepositoryBundle


class RevisionRejectingScorer(WonderScorer):
    def __init__(self, embedding: HashEmbeddingAdapter) -> None:
        super().__init__(embedding)
        self.scored_statements: list[str] = []

    async def score(self, *args: Any, **kwargs: Any) -> tuple[Any, Any, ThresholdDecision]:
        scores, explanation, _ = await super().score(*args, **kwargs)
        self.scored_statements.append(args[0].statement)
        decision = (
            ThresholdDecision.SURFACE
            if len(self.scored_statements) == 1
            else ThresholdDecision.REJECT
        )
        return scores, explanation, decision


class GroundedRevisingReviewer:
    async def review(
        self,
        candidate: Candidate,
        context: list[KnowledgeItem],
        *,
        max_runtime_calls: int,
    ) -> CandidateReviewResult:
        return CandidateReviewResult(
            revised_statement="Revised local feedback claim that must be scored independently.",
            expanded_idea=(
                "The revision narrows the claim to a falsifiable comparison of local feedback "
                "latency and peak load across the two supplied source domains."
            ),
            supporting_evidence=["Source A support", "Source B support"],
            counter_evidence=["Different delays may invalidate the transfer."],
            supporting_source_refs=[
                item.source_ref or f"knowledge:{item.id}" for item in context
            ],
            counter_source_refs=[context[0].source_ref or f"knowledge:{context[0].id}"],
            source_refs=[item.source_ref or f"knowledge:{item.id}" for item in context],
            uncertainty=0.3,
            factual_risk=0.2,
            verdict="revise",
            runtime_calls=1,
        )


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
async def test_wander_bounds_long_seed_in_trace_without_failing() -> None:
    repositories = InMemoryRepositoryBundle()
    embedding = HashEmbeddingAdapter(32)
    seed = Seed(content=("Long seed evidence and constraints. " * 500).strip())
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
    first_reason = result.session.trace.steps[0].reason
    assert len(first_reason) <= 2_000
    assert "[truncated sha256:" in first_reason


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


@pytest.mark.asyncio
async def test_deep_wander_compares_multiple_candidates_before_completing() -> None:
    repositories = InMemoryRepositoryBundle()
    embedding = HashEmbeddingAdapter(48)
    ingestion = IngestionService(repositories.knowledge, embedding)
    for title, content in [
        ("Forest resilience", "Forests recover through diversity and distributed feedback."),
        ("Queue control", "Software queues stabilize load through local backpressure."),
        ("Public health", "Sentinel networks detect outbreaks through distributed signals."),
        ("Supply chains", "Inventory buffers absorb demand shocks across supplier networks."),
    ]:
        await ingestion.ingest_text(content, title=title)
    seed = Seed(content="Compare robust distributed responses to uncertain demand.")
    await repositories.seeds.create(seed)
    engine = WanderEngine(
        repositories,
        embedding,
        OperatorSelector(default_operators()),
        WonderScorer(
            embedding,
            thresholds=ThresholdPolicy(reject_below=0.0, explore_above=0.0, surface_above=0.0),
        ),
    )

    result = await engine.run(
        seed,
        WanderBudget(
            max_steps=6,
            max_candidates=4,
            min_candidates=3,
            target_wonders=2,
            max_stagnant_candidates=4,
            stop_on_first_wonder=False,
            max_runtime_calls=0,
        ),
    )

    assert len(result.candidates) >= 3
    assert len(result.wonders) >= 2
    assert result.session.trace.stop_reason == "target_wonders_reached"
    assert result.session.trace.final_wonder_ids == [wonder.id for wonder in result.wonders]
    assert any(step.action == "continue_after_surface" for step in result.session.trace.steps)


@pytest.mark.asyncio
async def test_runtime_revision_is_rescored_before_promotion() -> None:
    repositories = InMemoryRepositoryBundle()
    embedding = HashEmbeddingAdapter(48)
    ingestion = IngestionService(repositories.knowledge, embedding)
    for title, content, source_ref in [
        (
            "Queue control",
            "Backpressure uses local saturation signals to limit queue growth.",
            "kb://queues",
        ),
        (
            "Ecological control",
            "Local feedback can constrain resource demand in ecological systems.",
            "kb://ecology",
        ),
    ]:
        await ingestion.ingest_text(content, title=title, source_ref=source_ref)
    seed = Seed(content="Compare local feedback mechanisms without assuming equivalence.")
    await repositories.seeds.create(seed)
    scorer = RevisionRejectingScorer(embedding)
    engine = WanderEngine(
        repositories,
        embedding,
        OperatorSelector(default_operators()),
        scorer,
        candidate_reviewer=GroundedRevisingReviewer(),
    )

    result = await engine.run(
        seed,
        WanderBudget(max_steps=3, max_candidates=1, max_runtime_calls=1),
    )

    assert len(scorer.scored_statements) == 2
    assert scorer.scored_statements[1].startswith("Revised local feedback claim")
    assert result.wonders == []
    assert result.candidates[0].status.value == "rejected"
    assert result.candidates[0].metadata["runtime_revision"]["original_scores"]
