from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from wandermind.cognitive.association import AssociationEngine
from wandermind.cognitive.embedding import EmbeddingAdapter
from wandermind.cognitive.errors import EmbeddingError, EvaluationError, OperatorExecutionError
from wandermind.cognitive.operators import OperatorContext, OperatorSelector
from wandermind.cognitive.patches import PatchBuilder, marginal_novelty_gain
from wandermind.cognitive.retrieval import SemanticRetriever
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
    ) -> None:
        self.repositories = repositories
        self.embedding = embedding
        self.operator_selector = operator_selector
        self.scorer = scorer
        self.retriever = retriever or SemanticRetriever()
        self.patch_builder = patch_builder or PatchBuilder()
        self.association_engine = association_engine or AssociationEngine()

    async def run(self, seed: Seed, budget: WanderBudget | None = None) -> WanderRunResult:
        session = WanderSession(seed_id=seed.id, budget=budget or WanderBudget())
        await self.repositories.sessions.create(session)
        machine = CognitiveStateMachine()
        candidates: list[Candidate] = []
        wonders: list[Wonder] = []
        visited_ids: set[object] = set()
        visited_path: list[object] = []
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
            attempts = min(session.budget.max_candidates, session.budget.max_steps)
            previous_operators: list[str] = []
            pinned_pair = self._pinned_pair(seed, items)
            ranked_by_id = {result.item.id: result for result in ranked}
            patch_by_item: dict[UUID, KnowledgePatch] = {}
            for patch in patches:
                for item_id in patch.member_ids:
                    patch_by_item.setdefault(item_id, patch)
            patch_switches = 0
            termination_reason = "candidate_budget_exhausted"
            for attempt in range(attempts):
                if self._elapsed(started_at) >= session.budget.time_budget_seconds:
                    termination_reason = "time_budget_exhausted"
                    break
                if attempt == 0 and pinned_pair is not None:
                    left, right = pinned_pair
                    left_result = ranked_by_id[left.id]
                    right_result = ranked_by_id[right.id]
                else:
                    left_result = ranked[attempt % len(ranked)]
                    right_result = ranked[-(attempt % len(ranked)) - 1]
                    left = left_result.item
                    right = right_result.item
                if left.id == right.id:
                    continue
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
                    local_result = next(
                        (
                            result
                            for result in ranked
                            if result.item.id != left.id
                            and patch_by_item.get(result.item.id) is not None
                            and patch_by_item[result.item.id].id == left_patch_id
                        ),
                        None,
                    )
                    if local_result is None:
                        termination_reason = "patch_switch_budget_exhausted"
                        break
                    right_result = local_result
                    right = right_result.item
                    right_patch = left_patch
                    changes_patch = False
                if changes_patch:
                    patch_switches += 1
                session.metadata["patch_switches"] = patch_switches
                session.metadata["wander_moves"] = attempt + 1
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
                candidate = Candidate(
                    session_id=session.id,
                    candidate_type=operator_result.wonder_type,
                    statement=operator_result.statement,
                    explanation=operator_result.explanation,
                    seed_id=seed.id,
                    source_items=[left.id, right.id],
                    operator=operator.name,
                    wander_path=visited_path,
                    metadata={"operator_output": operator_result.structured},
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
                if decision in {ThresholdDecision.DEEP_EXPLORE, ThresholdDecision.SURFACE}:
                    self._transition(
                        session,
                        machine,
                        CognitiveState.EXPLORE,
                        "structured_explore",
                        "candidate preserved for evidence-oriented exploration",
                        candidate_ids=[candidate.id],
                    )
                    candidate.status = CandidateStatus.EXPLORED
                    await self.repositories.candidates.update(candidate)
                    self._transition(
                        session,
                        machine,
                        CognitiveState.CRITIQUE,
                        "independent_critique",
                        "checked coherence, arbitrariness, duplication, and factual risk",
                        candidate_ids=[candidate.id],
                    )
                if decision is ThresholdDecision.SURFACE and scores.hallucination_risk < 0.75:
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
                        explanation=candidate.explanation,
                        why_interesting=(
                            "It links knowledge at a non-obvious but explainable semantic distance "
                            "and opens follow-up questions."
                        ),
                        source_items=candidate.source_items,
                        connection_path=candidate.wander_path,
                        assumptions=list(operator_result.structured.get("assumptions", [])),
                        questions=operator_result.questions,
                        scores=scores,
                        confidence=(scores.coherence + scores.evidence_potential) / 2,
                        metadata={"score_explanation": score_explanation.model_dump(mode="json")},
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
                self._transition(
                    session,
                    machine,
                    CognitiveState.WANDER,
                    "continue_wandering",
                    f"candidate decision was {decision.value}",
                )
                if scores.redundancy >= 0.85:
                    termination_reason = "candidate_convergence"
                    break
                if scores.arbitrariness >= 0.80:
                    termination_reason = "arbitrariness_guard"
                    break
                if scores.hallucination_risk >= 0.75:
                    termination_reason = "hallucination_guard"
                    break
                if novelty_gain < 0.10:
                    termination_reason = "novelty_exhausted"
                    break
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
        if CognitiveState.STOPPED in self._legal_targets(machine):
            self._transition(session, machine, CognitiveState.STOPPED, "stop", reason)
        session.ended_at = utc_now()
        session.status = SessionStatus.STOPPED
        session.trace.stop_reason = reason
        await self.repositories.sessions.update(session)
        return WanderRunResult(session=session, candidates=candidates, wonders=wonders)

    def _transition(
        self,
        session: WanderSession,
        machine: CognitiveStateMachine,
        target: CognitiveState,
        action: str,
        reason: str,
        **step_fields: object,
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
        **step_fields: object,
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
