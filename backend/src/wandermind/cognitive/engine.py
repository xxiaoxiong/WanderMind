from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from wandermind.cognitive.association import AssociationEngine
from wandermind.cognitive.embedding import EmbeddingAdapter
from wandermind.cognitive.errors import EmbeddingError, EvaluationError, OperatorExecutionError
from wandermind.cognitive.operators import OperatorContext, OperatorSelector
from wandermind.cognitive.patches import PatchBuilder, marginal_novelty_gain
from wandermind.cognitive.retrieval import RetrievedItem, SemanticRetriever
from wandermind.cognitive.runtime_services import (
    CandidateReviewer,
    CandidateReviewResult,
    CandidateSynthesisResult,
    CandidateSynthesizer,
)
from wandermind.cognitive.scoring import ThresholdDecision, WonderScorer
from wandermind.cognitive.state_machine import CognitiveStateMachine
from wandermind.models import (
    Candidate,
    CandidateStatus,
    CognitiveState,
    KnowledgeItem,
    KnowledgePatch,
    Seed,
    SeedStatus,
    SessionStatus,
    WanderBudget,
    WanderSession,
    WanderStep,
    Wonder,
)
from wandermind.models.base import utc_now
from wandermind.repositories.protocols import RepositoryBundle


@dataclass(slots=True)
class WanderRunResult:
    session: WanderSession
    candidates: list[Candidate]
    wonders: list[Wonder]


class WanderEngine:
    def __init__(
        self,
        repositories: RepositoryBundle,
        embedding: EmbeddingAdapter,
        operator_selector: OperatorSelector,
        scorer: WonderScorer,
        *,
        retriever: SemanticRetriever | None = None,
        patch_builder: PatchBuilder | None = None,
        association_engine: AssociationEngine | None = None,
        candidate_synthesizer: CandidateSynthesizer | None = None,
        candidate_reviewer: CandidateReviewer | None = None,
    ) -> None:
        self.repositories = repositories
        self.embedding = embedding
        self.operator_selector = operator_selector
        self.scorer = scorer
        self.retriever = retriever or SemanticRetriever()
        self.patch_builder = patch_builder or PatchBuilder()
        self.association_engine = association_engine or AssociationEngine()
        self.candidate_synthesizer = candidate_synthesizer
        self.candidate_reviewer = candidate_reviewer

    async def run(self, seed: Seed, budget: WanderBudget | None = None) -> WanderRunResult:
        session = WanderSession(seed_id=seed.id, budget=budget or WanderBudget())
        await self.repositories.sessions.create(session)
        machine = CognitiveStateMachine()
        candidates: list[Candidate] = []
        wonders: list[Wonder] = []
        visited_ids: set[UUID] = set()
        visited_path: list[UUID] = []
        started_at = datetime.now(UTC)
        session.started_at = started_at
        session.status = SessionStatus.RUNNING
        try:
            self._transition(session, machine, CognitiveState.SEEDING, "select_seed", seed.content)
            seed.status = SeedStatus.ACTIVE
            await self.repositories.seeds.update(seed)
            items = await self.repositories.knowledge.list(offset=0, limit=10_000)
            if len(items) < 2:
                return await self._stop(
                    session, machine, candidates, wonders, "insufficient_knowledge"
                )
            await self._ensure_embeddings(items)
            patches = self.patch_builder.build(seed, items)
            session.trace.patches = [patch.id for patch in patches]
            session.metadata["patch_membership_count"] = sum(
                len(patch.member_ids) for patch in patches
            )
            session.metadata["patches"] = [
                {
                    "id": str(patch.id),
                    "label": patch.label,
                    "patch_type": patch.metadata.get("patch_type"),
                    "member_count": len(patch.member_ids),
                    "coherence": patch.coherence,
                }
                for patch in patches
            ]
            self._transition(
                session,
                machine,
                CognitiveState.WANDER,
                "build_patches",
                f"built {len(patches)} knowledge patches",
                item_ids=[item.id for item in items[:5]],
            )
            seed_embedding = await self._embed_text(seed.content)
            ranked = self.retriever.rank(seed_embedding, items, query_text=seed.content)
            if len(ranked) < 2:
                return await self._stop(
                    session, machine, candidates, wonders, "no_retrieval_candidates"
                )
            historical_wonders = await self.repositories.wonders.list(offset=0, limit=10_000)
            feedback_history = [
                (wonder, feedback)
                for wonder in historical_wonders
                for feedback in await self.repositories.feedback.list_for_wonder(wonder.id)
            ]
            previous_operators: list[str] = []
            pinned_pair = self._pinned_pair(seed, items)
            patch_by_item: dict[UUID, KnowledgePatch] = {}
            for patch in patches:
                for item_id in patch.member_ids:
                    patch_by_item.setdefault(item_id, patch)
            patch_switches = 0
            wander_moves = 0
            runtime_calls_used = 0
            quality_guards: dict[str, int] = {}
            termination_reason = "search_space_exhausted"
            for left_result, right_result in self._candidate_pairs(ranked, pinned_pair):
                if self._elapsed(started_at) >= session.budget.time_budget_seconds:
                    termination_reason = "time_budget_exhausted"
                    break
                if len(candidates) >= session.budget.max_candidates:
                    termination_reason = "candidate_budget_exhausted"
                    break
                if wander_moves >= session.budget.max_steps:
                    termination_reason = "step_budget_exhausted"
                    break
                left = left_result.item
                right = right_result.item
                left_patch = patch_by_item.get(left.id)
                right_patch = patch_by_item.get(right.id)
                left_patch_id = left_patch.id if left_patch is not None else None
                right_patch_id = right_patch.id if right_patch is not None else None
                changes_patch = (
                    left_patch_id is not None
                    and right_patch_id is not None
                    and left_patch_id != right_patch_id
                )
                if changes_patch and patch_switches >= session.budget.max_patch_switches:
                    quality_guards["patch_switch_budget"] = (
                        quality_guards.get("patch_switch_budget", 0) + 1
                    )
                    continue
                if changes_patch:
                    patch_switches += 1
                wander_moves += 1
                session.metadata["patch_switches"] = patch_switches
                session.metadata["wander_moves"] = wander_moves
                semantic_difference = abs(left_result.distance - right_result.distance)
                novelty_gain = marginal_novelty_gain(
                    visited_ids, [left, right], semantic_difference
                )
                for item_id in (left.id, right.id):
                    if item_id not in visited_ids:
                        visited_ids.add(item_id)
                        visited_path.append(item_id)
                self._record(
                    session,
                    CognitiveState.WANDER,
                    "patch_switch" if changes_patch else "local_wander",
                    (
                        f"controlled remote jump from {left_patch.label} to {right_patch.label}"
                        if changes_patch and left_patch is not None and right_patch is not None
                        else f"selected {left.title} and {right.title} within one patch"
                    ),
                    item_ids=[left.id, right.id],
                    distance=right_result.distance,
                    novelty_gain=novelty_gain,
                    relevance=(left_result.relevance + right_result.relevance) / 2,
                    metadata={
                        "movement": "controlled_remote_jump" if changes_patch else "local",
                        "from_patch_id": str(left_patch.id) if left_patch else None,
                        "to_patch_id": str(right_patch.id) if right_patch else None,
                    },
                )
                association = self.association_engine.analyze(left, right)
                self._transition(
                    session,
                    machine,
                    CognitiveState.COLLISION,
                    "detect_collision",
                    association.explanation,
                    item_ids=[left.id, right.id],
                    distance=association.distance,
                    novelty_gain=novelty_gain,
                    collision_score=association.strength,
                )
                if association.strength < 0.15:
                    self._transition(
                        session,
                        machine,
                        CognitiveState.WANDER,
                        "discard_weak_collision",
                        "collision lacked an explainable bridge",
                    )
                    continue
                context = OperatorContext(
                    seed=seed, left=left, right=right, association=association
                )
                operator = self.operator_selector.select(context, previous_operators)
                previous_operators.append(operator.name)
                session.trace.operators.append(operator.name)
                self._transition(
                    session,
                    machine,
                    CognitiveState.GENERATE,
                    "apply_operator",
                    f"applied {operator.name}",
                    item_ids=[left.id, right.id],
                    operator=operator.name,
                )
                try:
                    operator_result = await operator.apply(context)
                except Exception as error:
                    raise OperatorExecutionError(f"operator {operator.name} failed") from error
                synthesis = CandidateSynthesisResult(operator_result=operator_result)
                if (
                    self.candidate_synthesizer is not None
                    and runtime_calls_used < session.budget.max_runtime_calls
                ):
                    self._record(
                        session,
                        CognitiveState.GENERATE,
                        "agent_synthesis",
                        "sent the grounded operator draft to the configured Agent Runtime",
                        item_ids=[left.id, right.id],
                        operator=operator.name,
                    )
                    synthesis = await self.candidate_synthesizer.synthesize(
                        context,
                        operator_result,
                        wander_session_id=str(session.id),
                    )
                    runtime_calls_used += synthesis.runtime_calls
                    operator_result = synthesis.operator_result
                    self._record(
                        session,
                        CognitiveState.GENERATE,
                        "agent_synthesis_completed"
                        if synthesis.verified
                        else "agent_synthesis_fallback",
                        (
                            f"Agent Runtime grounded the candidate via {synthesis.provider}"
                            if synthesis.verified
                            else f"used the deterministic draft after {synthesis.error or 'runtime_unavailable'}"
                        ),
                        item_ids=[left.id, right.id],
                        operator=operator.name,
                        metadata={
                            "provider": synthesis.provider,
                            "model": synthesis.model,
                            "verified": synthesis.verified,
                            "error": synthesis.error,
                        },
                    )
                session.metadata["runtime_calls_used"] = runtime_calls_used
                candidate = Candidate(
                    session_id=session.id,
                    candidate_type=operator_result.wonder_type,
                    statement=operator_result.statement,
                    explanation=operator_result.explanation,
                    seed_id=seed.id,
                    source_items=[left.id, right.id],
                    operator=operator.name,
                    wander_path=visited_path,
                    metadata={
                        "operator_output": operator_result.structured,
                        "runtime_synthesis": {
                            "verified": synthesis.verified,
                            "provider": synthesis.provider,
                            "model": synthesis.model,
                            "error": synthesis.error,
                        },
                    },
                )
                await self.repositories.candidates.create(candidate)
                candidates.append(candidate)
                session.trace.candidate_ids.append(candidate.id)
                self._transition(
                    session,
                    machine,
                    CognitiveState.SCORE,
                    "score_candidate",
                    candidate.statement,
                    candidate_ids=[candidate.id],
                )
                try:
                    scores, score_explanation, decision = await self.scorer.score(
                        candidate,
                        operator_result,
                        seed,
                        [left, right],
                        association,
                        historical_wonders,
                        knowledge_items=items,
                        feedback_history=feedback_history,
                    )
                except Exception as error:
                    raise EvaluationError("candidate scoring failed") from error
                candidate.scores = scores
                candidate.metadata["score_explanation"] = score_explanation.model_dump(mode="json")
                candidate.metadata["threshold_decision"] = decision.value
                if decision is ThresholdDecision.REJECT:
                    candidate.status = CandidateStatus.REJECTED
                elif decision is ThresholdDecision.KEEP_CANDIDATE:
                    candidate.status = CandidateStatus.FILTERED
                else:
                    candidate.status = CandidateStatus.PROMISING
                await self.repositories.candidates.update(candidate)
                review: CandidateReviewResult | None = None
                remaining_runtime_calls = session.budget.max_runtime_calls - runtime_calls_used
                if (
                    decision in {ThresholdDecision.DEEP_EXPLORE, ThresholdDecision.SURFACE}
                    and self.candidate_reviewer is not None
                    and remaining_runtime_calls >= 2
                ):
                    self._transition(
                        session,
                        machine,
                        CognitiveState.EXPLORE,
                        "runtime_evidence_validation",
                        "the configured Agent Runtime checked support and counter-evidence",
                        candidate_ids=[candidate.id],
                    )
                    review = await self.candidate_reviewer.review(
                        candidate,
                        [left, right],
                        max_runtime_calls=2,
                    )
                    runtime_calls_used += review.runtime_calls
                    session.metadata["runtime_calls_used"] = runtime_calls_used
                    candidate.status = CandidateStatus.EXPLORED
                    candidate.metadata["runtime_review"] = review.model_dump(mode="json")
                    if review.verdict != "pass":
                        candidate.status = CandidateStatus.REJECTED
                    await self.repositories.candidates.update(candidate)
                    self._transition(
                        session,
                        machine,
                        CognitiveState.CRITIQUE,
                        "runtime_independent_critique",
                        f"Agent Runtime critic verdict: {review.verdict}",
                        candidate_ids=[candidate.id],
                        metadata={
                            "verdict": review.verdict,
                            "factual_risk": review.factual_risk,
                            "obviousness": review.obviousness,
                        },
                    )
                elif (
                    decision in {ThresholdDecision.DEEP_EXPLORE, ThresholdDecision.SURFACE}
                    and self.candidate_reviewer is not None
                ):
                    candidate.metadata["runtime_review"] = {
                        "status": "skipped",
                        "reason": "runtime_budget_exhausted",
                    }
                    await self.repositories.candidates.update(candidate)
                    self._record(
                        session,
                        CognitiveState.SCORE,
                        "runtime_review_skipped",
                        "runtime budget could not fund evidence validation and an independent critic",
                        candidate_ids=[candidate.id],
                    )
                review_passed = (
                    self.candidate_reviewer is None
                    or (
                        review is not None
                        and review.verdict == "pass"
                        and review.factual_risk < 0.75
                    )
                )
                if (
                    decision is ThresholdDecision.SURFACE
                    and scores.hallucination_risk < 0.75
                    and review_passed
                ):
                    self._transition(
                        session,
                        machine,
                        CognitiveState.PERSIST,
                        "promote_candidate",
                        "candidate passed the configured surface threshold",
                        candidate_ids=[candidate.id],
                    )
                    wonder = Wonder(
                        session_id=session.id,
                        seed_id=seed.id,
                        candidate_id=candidate.id,
                        type=candidate.candidate_type,
                        statement=candidate.statement,
                        explanation=(
                            review.expanded_idea
                            if review is not None and review.expanded_idea
                            else candidate.explanation
                        ),
                        why_interesting=(
                            "It links knowledge at a non-obvious but explainable semantic distance "
                            "and opens follow-up questions."
                        ),
                        source_items=candidate.source_items,
                        connection_path=candidate.wander_path,
                        assumptions=list(operator_result.structured.get("assumptions", [])),
                        questions=operator_result.questions,
                        supporting_evidence=(review.supporting_evidence if review else []),
                        counter_evidence=(review.counter_evidence if review else []),
                        scores=scores,
                        confidence=(scores.coherence + scores.evidence_potential) / 2,
                        metadata={
                            "score_explanation": score_explanation.model_dump(mode="json"),
                            "runtime_review": review.model_dump(mode="json") if review else None,
                        },
                    )
                    await self.repositories.wonders.create(wonder)
                    candidate.status = CandidateStatus.PROMOTED
                    await self.repositories.candidates.update(candidate)
                    wonders.append(wonder)
                    session.trace.final_wonder_ids.append(wonder.id)
                    self._transition(
                        session,
                        machine,
                        CognitiveState.SURFACE,
                        "surface_wonder",
                        wonder.statement,
                        item_ids=wonder.source_items,
                        candidate_ids=[candidate.id],
                    )
                    session.ended_at = utc_now()
                    session.status = SessionStatus.COMPLETED
                    session.trace.stop_reason = "high_value_found"
                    seed.status = SeedStatus.USED
                    seed.last_used_at = utc_now()
                    await self.repositories.seeds.update(seed)
                    await self.repositories.sessions.update(session)
                    return WanderRunResult(session=session, candidates=candidates, wonders=wonders)
                guard_reason: str | None = None
                if scores.redundancy >= 0.85:
                    guard_reason = "candidate_convergence"
                elif scores.arbitrariness >= 0.80:
                    guard_reason = "arbitrariness_guard"
                elif scores.hallucination_risk >= 0.75:
                    guard_reason = "hallucination_guard"
                elif novelty_gain < 0.10:
                    guard_reason = "novelty_exhausted"
                if guard_reason is not None:
                    quality_guards[guard_reason] = quality_guards.get(guard_reason, 0) + 1
                    candidate.metadata["quality_guard"] = guard_reason
                    await self.repositories.candidates.update(candidate)
                self._transition(
                    session,
                    machine,
                    CognitiveState.WANDER,
                    "continue_wandering",
                    (
                        f"candidate hit {guard_reason}; trying a different knowledge pair"
                        if guard_reason
                        else f"candidate decision was {decision.value}"
                    ),
                )
            session.metadata["quality_guards"] = quality_guards
            return await self._stop(session, machine, candidates, wonders, termination_reason)
        except Exception as error:
            if CognitiveState.FAILED in self._legal_targets(machine):
                self._transition(
                    session,
                    machine,
                    CognitiveState.FAILED,
                    "session_failed",
                    type(error).__name__,
                )
            session.ended_at = utc_now()
            session.status = SessionStatus.FAILED
            session.trace.stop_reason = f"failure:{type(error).__name__}"
            await self.repositories.sessions.update(session)
            raise

    async def _ensure_embeddings(self, items: list[KnowledgeItem]) -> None:
        for item in items:
            if item.embedding is None:
                item.embedding = await self._embed_text(f"{item.title} {item.content}")
                item.updated_at = utc_now()
                await self.repositories.knowledge.update(item)

    async def _embed_text(self, text: str) -> list[float]:
        try:
            return await self.embedding.embed_text(text)
        except Exception as error:
            raise EmbeddingError("wander embedding failed") from error

    async def _stop(
        self,
        session: WanderSession,
        machine: CognitiveStateMachine,
        candidates: list[Candidate],
        wonders: list[Wonder],
        reason: str,
    ) -> WanderRunResult:
        completed = reason not in {"insufficient_knowledge", "no_retrieval_candidates"}
        if CognitiveState.STOPPED in self._legal_targets(machine):
            self._transition(
                session,
                machine,
                CognitiveState.STOPPED,
                "complete" if completed else "stop",
                reason,
            )
        session.ended_at = utc_now()
        session.status = SessionStatus.COMPLETED if completed else SessionStatus.STOPPED
        session.trace.stop_reason = reason
        if completed:
            seed = await self.repositories.seeds.get(session.seed_id)
            if seed is not None:
                seed.status = SeedStatus.USED
                seed.last_used_at = utc_now()
                await self.repositories.seeds.update(seed)
        await self.repositories.sessions.update(session)
        return WanderRunResult(session=session, candidates=candidates, wonders=wonders)

    def _transition(
        self,
        session: WanderSession,
        machine: CognitiveStateMachine,
        target: CognitiveState,
        action: str,
        reason: str,
        **step_fields: Any,
    ) -> None:
        machine.transition(target)
        session.state = target
        self._record(session, target, action, reason, **step_fields)

    def _record(
        self,
        session: WanderSession,
        state: CognitiveState,
        action: str,
        reason: str,
        **step_fields: Any,
    ) -> None:
        session.trace.steps.append(
            WanderStep(
                index=len(session.trace.steps),
                state=state,
                action=action,
                reason=reason,
                **step_fields,
            )
        )
        session.updated_at = utc_now()

    def _legal_targets(self, machine: CognitiveStateMachine) -> set[CognitiveState]:
        from wandermind.cognitive.state_machine import LEGAL_TRANSITIONS

        return LEGAL_TRANSITIONS[machine.state]

    def _elapsed(self, started_at: datetime) -> float:
        return (datetime.now(UTC) - started_at).total_seconds()

    def _pinned_pair(
        self,
        seed: Seed,
        items: list[KnowledgeItem],
    ) -> tuple[KnowledgeItem, KnowledgeItem] | None:
        raw_ids = seed.metadata.get("paired_item_ids")
        if not isinstance(raw_ids, list) or len(raw_ids) != 2:
            return None
        items_by_id = {str(item.id): item for item in items}
        selected = [items_by_id.get(str(item_id)) for item_id in raw_ids]
        if selected[0] is None or selected[1] is None or selected[0].id == selected[1].id:
            return None
        return selected[0], selected[1]

    def _candidate_pairs(
        self,
        ranked: list[RetrievedItem],
        pinned_pair: tuple[KnowledgeItem, KnowledgeItem] | None,
    ) -> list[tuple[RetrievedItem, RetrievedItem]]:
        ranked_by_id = {result.item.id: result for result in ranked}
        pairs: list[tuple[RetrievedItem, RetrievedItem]] = []
        seen: set[frozenset[UUID]] = set()
        if pinned_pair is not None:
            left = ranked_by_id.get(pinned_pair[0].id)
            right = ranked_by_id.get(pinned_pair[1].id)
            if left is not None and right is not None:
                pairs.append((left, right))
                seen.add(frozenset((left.item.id, right.item.id)))
        ranked_pairs = [
            (left_index, right_index, ranked[left_index], ranked[right_index])
            for left_index in range(len(ranked))
            for right_index in range(left_index + 1, len(ranked))
        ]
        ranked_pairs.sort(
            key=lambda pair: (
                abs(pair[2].distance - pair[3].distance),
                pair[2].relevance + pair[3].relevance,
            ),
            reverse=True,
        )
        for _, _, left, right in ranked_pairs:
            key = frozenset((left.item.id, right.item.id))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((left, right))
        return pairs
