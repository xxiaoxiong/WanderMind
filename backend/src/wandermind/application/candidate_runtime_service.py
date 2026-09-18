from __future__ import annotations

import json
from contextlib import suppress

from pydantic import Field, ValidationError

from wandermind.application.explore_service import DeepEvaluationService
from wandermind.cognitive.operators import OperatorContext, OperatorResult
from wandermind.cognitive.runtime_services import (
    CandidateReviewResult,
    CandidateSynthesisResult,
)
from wandermind.models import Candidate, KnowledgeItem
from wandermind.models.base import DomainModel
from wandermind.runtime import (
    AgentRuntimeAdapter,
    RuntimeErrorBase,
    RuntimeMalformedOutputError,
    RuntimeSession,
    RuntimeTask,
    SandboxMode,
    run_with_retry,
)


class CandidateSynthesisOutput(DomainModel):
    statement: str = Field(min_length=8, max_length=2_000)
    explanation: str = Field(min_length=20, max_length=6_000)
    assumptions: list[str] = Field(default_factory=list, max_length=8)
    implications: list[str] = Field(default_factory=list, max_length=8)
    questions: list[str] = Field(default_factory=list, max_length=8)


class RuntimeCandidateSynthesizer:
    def __init__(
        self,
        runtime: AgentRuntimeAdapter,
        *,
        max_retries: int = 1,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.runtime = runtime
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

    async def synthesize(
        self,
        context: OperatorContext,
        draft: OperatorResult,
        *,
        wander_session_id: str,
    ) -> CandidateSynthesisResult:
        try:
            session = await self.runtime.start_session("candidate_synthesis")
        except RuntimeErrorBase as error:
            return CandidateSynthesisResult(
                operator_result=draft,
                runtime_calls=1,
                verified=False,
                error=type(error).__name__,
            )
        task = RuntimeTask(
            prompt=_synthesis_prompt(context, draft),
            output_schema=CandidateSynthesisOutput.model_json_schema(),
            sandbox=SandboxMode.READ_ONLY,
            timeout_seconds=self.timeout_seconds,
            metadata={"wander_session_id": wander_session_id},
        )
        try:
            result = await run_with_retry(
                self.runtime,
                session,
                task,
                max_retries=self.max_retries,
            )
            try:
                output = CandidateSynthesisOutput.model_validate(result.structured)
            except ValidationError as error:
                raise RuntimeMalformedOutputError(
                    "candidate synthesis output failed validation"
                ) from error
            structured = dict(draft.structured)
            structured.update(
                {
                    "assumptions": output.assumptions,
                    "implications": output.implications,
                    "runtime_synthesis": True,
                }
            )
            return CandidateSynthesisResult(
                operator_result=OperatorResult(
                    wonder_type=draft.wonder_type,
                    statement=output.statement,
                    explanation=output.explanation,
                    structured=structured,
                    questions=output.questions,
                ),
                runtime_calls=1,
                verified=True,
                provider=_string_usage(result.usage, "provider") or session.provider,
                model=_string_usage(result.usage, "model"),
            )
        except (RuntimeErrorBase, ValidationError) as error:
            return CandidateSynthesisResult(
                operator_result=draft,
                runtime_calls=1,
                verified=False,
                provider=session.provider,
                model=_session_model(session),
                error=type(error).__name__,
            )
        finally:
            await _close_session(self.runtime, session)


class RuntimeCandidateReviewer:
    def __init__(self, deep_evaluation: DeepEvaluationService) -> None:
        self.deep_evaluation = deep_evaluation

    async def review(
        self,
        candidate: Candidate,
        context: list[KnowledgeItem],
        *,
        max_runtime_calls: int,
    ) -> CandidateReviewResult:
        try:
            evaluation = await self.deep_evaluation.evaluate(
                candidate,
                context,
                max_runtime_calls=max_runtime_calls,
                include_explorer=False,
            )
        except RuntimeErrorBase as error:
            return CandidateReviewResult(
                weaknesses=[f"Agent Runtime review failed: {type(error).__name__}"],
                verdict="reject",
                runtime_calls=min(max_runtime_calls, 2),
            )
        critic = evaluation.critic
        evidence = evaluation.evidence
        return CandidateReviewResult(
            supporting_evidence=evidence.supporting_evidence,
            counter_evidence=evidence.counter_evidence,
            source_refs=evidence.source_refs,
            uncertainty=evidence.uncertainty,
            weaknesses=critic.weakness,
            obviousness=critic.obviousness,
            factual_risk=critic.factual_risk,
            alternative_explanations=critic.alternative_explanation,
            verdict=critic.verdict.value,
            runtime_calls=min(max_runtime_calls, 2),
        )


def _synthesis_prompt(context: OperatorContext, draft: OperatorResult) -> str:
    payload = {
        "seed": context.seed.content,
        "source_items": [
            {
                "id": str(item.id),
                "title": item.title,
                "content": item.content[:3_000],
                "topics": item.topics,
                "source_ref": item.source_ref,
            }
            for item in (context.left, context.right)
        ],
        "association": context.association.model_dump(mode="json"),
        "operator_draft": draft.model_dump(mode="json"),
    }
    language = (
        "Write every human-readable value in Simplified Chinese."
        if any("\u4e00" <= character <= "\u9fff" for character in context.seed.content)
        else "Write every human-readable value in the seed's language."
    )
    return "\n".join(
        [
            "Act as WanderMind's candidate synthesis agent. Return only JSON.",
            language,
            "Improve the operator draft into one concrete, non-generic and testable connection.",
            "Use only the supplied seed and source items as factual grounding.",
            "Preserve uncertainty, name assumptions, and never claim the two domains are identical.",
            "Questions must be actionable tests or discriminating observations.",
            f"Input: {json.dumps(payload, ensure_ascii=False)}",
        ]
    )


def _string_usage(usage: dict[str, object], key: str) -> str | None:
    value = usage.get(key)
    return value if isinstance(value, str) and value else None


def _session_model(session: RuntimeSession) -> str | None:
    value = session.metadata.get("model")
    return value if isinstance(value, str) and value else None


async def _close_session(runtime: AgentRuntimeAdapter, session: RuntimeSession) -> None:
    with suppress(RuntimeErrorBase):
        await runtime.close_session(session)
