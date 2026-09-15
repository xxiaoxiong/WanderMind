from __future__ import annotations

from wandermind.application.evaluation import CriticVerdict, DeepEvaluationResult
from wandermind.models import (
    Candidate,
    CandidateStatus,
    Feedback,
    FeedbackAction,
    Wonder,
    WonderStatus,
)
from wandermind.repositories.protocols import RepositoryBundle


class WonderPromotionService:
    def __init__(self, repositories: RepositoryBundle, *, threshold: float = 0.58) -> None:
        self.repositories = repositories
        self.threshold = threshold

    async def promote(
        self,
        candidate: Candidate,
        evaluation: DeepEvaluationResult,
    ) -> Wonder | None:
        if candidate.scores is None or candidate.scores.total < self.threshold:
            return None
        if evaluation.critic.verdict is not CriticVerdict.PASS:
            candidate.status = CandidateStatus.REJECTED
            await self.repositories.candidates.update(candidate)
            return None
        evidence = evaluation.evidence
        confidence = (candidate.scores.coherence + candidate.scores.evidence_potential) / 2
        if not evidence.source_refs:
            confidence = min(confidence, 0.45)
        expanded = (
            evaluation.explorer.expanded_idea if evaluation.explorer else candidate.explanation
        )
        wonder = Wonder(
            session_id=candidate.session_id,
            seed_id=candidate.seed_id,
            candidate_id=candidate.id,
            type=candidate.candidate_type,
            statement=candidate.statement,
            explanation=expanded,
            why_interesting="The candidate passed independent critique and the configured score threshold.",
            source_items=candidate.source_items,
            connection_path=candidate.wander_path,
            supporting_evidence=evidence.supporting_evidence,
            counter_evidence=evidence.counter_evidence,
            assumptions=[],
            questions=(evaluation.explorer.follow_up_questions if evaluation.explorer else []),
            scores=candidate.scores,
            confidence=confidence,
            metadata={
                "source_refs": evidence.source_refs,
                "critic": evaluation.critic.model_dump(mode="json"),
                "evidence_status": evidence.status.value,
            },
        )
        await self.repositories.wonders.create(wonder)
        candidate.status = CandidateStatus.PROMOTED
        await self.repositories.candidates.update(candidate)
        return wonder


class FeedbackService:
    def __init__(self, repositories: RepositoryBundle) -> None:
        self.repositories = repositories

    async def submit(self, feedback: Feedback) -> Feedback:
        wonder = await self.repositories.wonders.get(feedback.wonder_id)
        if wonder is None:
            raise KeyError(feedback.wonder_id)
        if feedback.action in {FeedbackAction.SAVE, FeedbackAction.SAVE_FOR_LATER}:
            wonder.status = WonderStatus.SAVED
        elif feedback.action in {
            FeedbackAction.NOT_INTERESTING,
            FeedbackAction.ALREADY_KNEW,
            FeedbackAction.OBVIOUS,
            FeedbackAction.RANDOM,
            FeedbackAction.TOO_RANDOM,
            FeedbackAction.WRONG,
            FeedbackAction.IRRELEVANT,
        }:
            wonder.status = WonderStatus.DISMISSED
        elif feedback.action in {
            FeedbackAction.CONTINUE,
            FeedbackAction.CONTINUE_EXPLORE,
            FeedbackAction.INSPIRED_NEW_IDEA,
        }:
            wonder.status = WonderStatus.INCUBATING
        wonder.metadata["last_feedback"] = feedback.action.value
        await self.repositories.wonders.update(wonder)
        return await self.repositories.feedback.create(feedback)
