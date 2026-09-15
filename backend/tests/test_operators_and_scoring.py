from uuid import uuid4

import pytest

from wandermind.cognitive.association import Association, AssociationType
from wandermind.cognitive.embedding import HashEmbeddingAdapter
from wandermind.cognitive.operators import OperatorContext, OperatorSelector, default_operators
from wandermind.cognitive.scoring import ThresholdDecision, ThresholdPolicy, WonderScorer
from wandermind.models import (
    Candidate,
    Feedback,
    FeedbackAction,
    KnowledgeItem,
    Seed,
    Wonder,
    WonderScores,
    WonderType,
)


def make_context(distance: float = 0.65) -> OperatorContext:
    left = KnowledgeItem(
        title="Agent scheduling",
        content="Agents allocate compute and attention using feedback.",
        topics=["agents", "scheduling"],
        embedding=[1.0, 0.0],
    )
    right = KnowledgeItem(
        title="Organizational governance",
        content="Organizations allocate authority and resources using feedback.",
        topics=["organizations", "governance"],
        embedding=[0.5, 0.5],
    )
    association = Association(
        type=AssociationType.ANALOGY_CANDIDATE,
        strength=0.8,
        distance=distance,
        shared_terms=["allocate", "feedback", "resources"],
        explanation="Both allocate scarce resources through feedback.",
    )
    return OperatorContext(
        seed=Seed(content="How should agents govern resources?"),
        left=left,
        right=right,
        association=association,
    )


@pytest.mark.asyncio
async def test_all_default_operators_return_structured_results() -> None:
    context = make_context()

    for operator in default_operators():
        result = await operator.apply(context)
        assert result.statement
        assert result.explanation
        assert result.structured
        assert result.wonder_type in set(WonderType)

    analogy = await default_operators()[0].apply(context)
    assert analogy.structured["break_points"]


def test_operator_selector_prefers_analogy_for_remote_pair() -> None:
    selected = OperatorSelector(default_operators()).select(make_context())

    assert selected.name == "analogy"


@pytest.mark.asyncio
async def test_scorer_rewards_semantic_sweet_spot_over_random_or_obvious() -> None:
    adapter = HashEmbeddingAdapter(32)
    scorer = WonderScorer(adapter, thresholds=ThresholdPolicy(surface_above=0.9))
    context = make_context()
    result = await default_operators()[0].apply(context)
    candidate = Candidate(
        session_id=uuid4(),
        candidate_type=result.wonder_type,
        statement=result.statement,
        explanation=result.explanation,
        seed_id=context.seed.id,
        source_items=[context.left.id, context.right.id],
        operator="analogy",
    )

    interesting, _, _ = await scorer.score(
        candidate,
        result,
        context.seed,
        [context.left, context.right],
        context.association,
        [],
    )
    obvious_context = make_context(distance=0.05)
    obvious, _, _ = await scorer.score(
        candidate,
        result,
        obvious_context.seed,
        [obvious_context.left, obvious_context.right],
        obvious_context.association,
        [],
    )
    random_context = make_context(distance=1.8)
    random, _, _ = await scorer.score(
        candidate,
        result,
        random_context.seed,
        [random_context.left, random_context.right],
        random_context.association,
        [],
    )

    assert interesting.surprise > obvious.surprise
    assert interesting.surprise > random.surprise


@pytest.mark.asyncio
async def test_scorer_penalizes_unsupported_absolute_seed_claims() -> None:
    adapter = HashEmbeddingAdapter(32)
    scorer = WonderScorer(adapter)
    context = make_context()
    result = await default_operators()[0].apply(context)
    candidate = Candidate(
        session_id=uuid4(),
        candidate_type=result.wonder_type,
        statement=result.statement,
        explanation=result.explanation,
        seed_id=context.seed.id,
        source_items=[context.left.id, context.right.id],
        operator="analogy",
    )
    risky_seed = Seed(content="Prove this unrelated mechanism always causes the outcome.")
    scores, explanation, _ = await scorer.score(
        candidate,
        result,
        risky_seed,
        [context.left, context.right],
        context.association,
        [],
    )
    assert scores.hallucination_risk >= 0.6
    assert explanation.penalties["hallucination_risk"].value == scores.hallucination_risk


@pytest.mark.asyncio
async def test_scorer_never_surfaces_direct_restatements() -> None:
    adapter = HashEmbeddingAdapter(32)
    scorer = WonderScorer(adapter)
    context = make_context()
    context.seed.content = "How does agent scheduling allocate compute?"
    result = await default_operators()[0].apply(context)
    candidate = Candidate(
        session_id=uuid4(),
        candidate_type=result.wonder_type,
        statement=result.statement,
        explanation=result.explanation,
        seed_id=context.seed.id,
        source_items=[context.left.id, context.right.id],
        operator="analogy",
    )

    scores, _, decision = await scorer.score(
        candidate,
        result,
        context.seed,
        [context.left, context.right],
        context.association,
        [],
    )

    assert scores.redundancy >= 0.85
    assert decision is not ThresholdDecision.SURFACE


@pytest.mark.asyncio
async def test_scorer_never_surfaces_arbitrary_framing() -> None:
    adapter = HashEmbeddingAdapter(32)
    scorer = WonderScorer(adapter)
    context = make_context()
    context.seed.content = "Why is purple secretly a scheduling algorithm for spoons?"
    result = await default_operators()[0].apply(context)
    candidate = Candidate(
        session_id=uuid4(),
        candidate_type=result.wonder_type,
        statement=result.statement,
        explanation=result.explanation,
        seed_id=context.seed.id,
        source_items=[context.left.id, context.right.id],
        operator="analogy",
    )

    scores, _, decision = await scorer.score(
        candidate,
        result,
        context.seed,
        [context.left, context.right],
        context.association,
        [],
    )

    assert scores.arbitrariness == 1.0
    assert decision is not ThresholdDecision.SURFACE


@pytest.mark.asyncio
async def test_scorer_uses_explicit_feedback_as_a_relevance_signal() -> None:
    adapter = HashEmbeddingAdapter(32)
    scorer = WonderScorer(adapter)
    context = make_context()
    result = await default_operators()[0].apply(context)
    candidate = Candidate(
        session_id=uuid4(),
        candidate_type=result.wonder_type,
        statement=result.statement,
        explanation=result.explanation,
        seed_id=context.seed.id,
        source_items=[context.left.id, context.right.id],
        operator="analogy",
    )
    historical = Wonder(
        session_id=uuid4(),
        seed_id=uuid4(),
        type=WonderType.CONNECTION,
        statement=result.statement,
        explanation=result.explanation,
        why_interesting="A prior related idea.",
        source_items=[context.left.id, context.right.id],
        scores=WonderScores(total=0.7),
    )
    positive, _, _ = await scorer.score(
        candidate,
        result,
        context.seed,
        [context.left, context.right],
        context.association,
        [historical],
        feedback_history=[
            (historical, Feedback(wonder_id=historical.id, action=FeedbackAction.INTERESTING))
        ],
    )
    negative, _, _ = await scorer.score(
        candidate,
        result,
        context.seed,
        [context.left, context.right],
        context.association,
        [historical],
        feedback_history=[
            (historical, Feedback(wonder_id=historical.id, action=FeedbackAction.NOT_INTERESTING))
        ],
    )

    assert positive.personal_relevance > negative.personal_relevance
