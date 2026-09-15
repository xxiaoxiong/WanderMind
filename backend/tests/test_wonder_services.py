from __future__ import annotations

from uuid import uuid4

import pytest

from wandermind.application.evaluation import (
    CriticOutput,
    CriticVerdict,
    DeepEvaluationResult,
    EvidenceOutput,
    ExplorerOutput,
)
from wandermind.application.wonder_service import FeedbackService, WonderPromotionService
from wandermind.models import (
    Candidate,
    CandidateStatus,
    Feedback,
    FeedbackAction,
    Seed,
    WanderSession,
    Wonder,
    WonderScores,
    WonderStatus,
    WonderType,
)
from wandermind.repositories import InMemoryRepositoryBundle


async def make_candidate(repositories: InMemoryRepositoryBundle, total: float = 0.8) -> Candidate:
    seed = await repositories.seeds.create(Seed(content="A seed"))
    session = await repositories.sessions.create(WanderSession(seed_id=seed.id))
    candidate = Candidate(
        session_id=session.id,
        seed_id=seed.id,
        candidate_type=WonderType.CONNECTION,
        statement="A useful connection",
        explanation="Two systems share a measurable feedback structure.",
        source_items=[uuid4(), uuid4()],
        operator="analogy",
        scores=WonderScores(total=total, coherence=0.8, evidence_potential=0.7),
    )
    return await repositories.candidates.create(candidate)


@pytest.mark.asyncio
async def test_promotion_requires_threshold_and_independent_pass() -> None:
    repositories = InMemoryRepositoryBundle()
    service = WonderPromotionService(repositories, threshold=0.6)
    candidate = await make_candidate(repositories)
    evaluation = DeepEvaluationResult(
        explorer=ExplorerOutput(
            expanded_idea="Expanded and testable connection",
            follow_up_questions=["What measurement distinguishes the mechanisms?"],
        ),
        evidence=EvidenceOutput(
            supporting_evidence=["Local record supports the shared feedback mechanism."],
            source_refs=["kb://feedback"],
            uncertainty=0.2,
        ),
        critic=CriticOutput(verdict=CriticVerdict.PASS, factual_risk=0.2),
    )
    wonder = await service.promote(candidate, evaluation)
    assert wonder is not None
    assert wonder.explanation == "Expanded and testable connection"
    assert wonder.supporting_evidence
    assert candidate.status is CandidateStatus.PROMOTED

    weak = await make_candidate(repositories, total=0.2)
    assert await service.promote(weak, evaluation) is None

    rejected = await make_candidate(repositories)
    rejection = evaluation.model_copy(
        update={"critic": CriticOutput(verdict=CriticVerdict.REJECT, factual_risk=0.9)}
    )
    assert await service.promote(rejected, rejection) is None
    assert rejected.status is CandidateStatus.REJECTED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        (FeedbackAction.SAVE_FOR_LATER, WonderStatus.SAVED),
        (FeedbackAction.ALREADY_KNEW, WonderStatus.DISMISSED),
        (FeedbackAction.TOO_RANDOM, WonderStatus.DISMISSED),
        (FeedbackAction.IRRELEVANT, WonderStatus.DISMISSED),
        (FeedbackAction.CONTINUE_EXPLORE, WonderStatus.INCUBATING),
        (FeedbackAction.INSPIRED_NEW_IDEA, WonderStatus.INCUBATING),
        (FeedbackAction.VERY_INTERESTING, WonderStatus.ACTIVE),
    ],
)
async def test_feedback_actions_update_wonder_status(
    action: FeedbackAction,
    expected_status: WonderStatus,
) -> None:
    repositories = InMemoryRepositoryBundle()
    candidate = await make_candidate(repositories)
    assert candidate.scores is not None
    wonder = await repositories.wonders.create(
        Wonder(
            session_id=candidate.session_id,
            seed_id=candidate.seed_id,
            candidate_id=candidate.id,
            type=WonderType.CONNECTION,
            statement=candidate.statement,
            explanation=candidate.explanation,
            why_interesting="Worth testing",
            source_items=candidate.source_items,
            scores=candidate.scores,
        )
    )
    stored = await FeedbackService(repositories).submit(
        Feedback(wonder_id=wonder.id, action=action)
    )
    assert stored.action is action
    assert wonder.status is expected_status
