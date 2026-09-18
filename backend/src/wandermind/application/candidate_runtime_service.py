from __future__ import annotations

import json
from contextlib import suppress
from typing import Literal

from pydantic import Field, ValidationError

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
    assumptions: list[str] = Field(max_length=8)
    implications: list[str] = Field(max_length=8)
    questions: list[str] = Field(max_length=8)


class CandidateReviewOutput(DomainModel):
    expanded_idea: str = Field(min_length=20, max_length=6_000)
    supporting_evidence: list[str] = Field(max_length=8)
    counter_evidence: list[str] = Field(max_length=8)
    source_refs: list[str] = Field(max_length=8)
    uncertainty: float = Field(ge=0.0, le=1.0)
    weaknesses: list[str] = Field(max_length=8)
    obviousness: float = Field(ge=0.0, le=1.0)
    factual_risk: float = Field(ge=0.0, le=1.0)
    alternative_explanations: list[str] = Field(max_length=8)
    verdict: Literal["pass", "revise", "reject"]


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

    async def review(
        self,
        candidate: Candidate,
        context: list[KnowledgeItem],
        *,
        max_runtime_calls: int,
    ) -> CandidateReviewResult:
        if max_runtime_calls < 1:
            return CandidateReviewResult(
                weaknesses=["Runtime budget did not permit candidate review."],
                verdict="reject",
            )
        try:
            session = await self.runtime.start_session("candidate_review")
        except RuntimeErrorBase as error:
            return CandidateReviewResult(
                weaknesses=[f"Agent Runtime review failed: {type(error).__name__}"],
                verdict="reject",
                runtime_calls=1,
            )
        task = RuntimeTask(
            prompt=_review_prompt(candidate, context),
            output_schema=CandidateReviewOutput.model_json_schema(),
            sandbox=SandboxMode.READ_ONLY,
            timeout_seconds=self.timeout_seconds,
            metadata={"wander_session_id": str(candidate.session_id)},
        )
        try:
            result = await run_with_retry(
                self.runtime,
                session,
                task,
                max_retries=self.max_retries,
            )
            output = CandidateReviewOutput.model_validate(result.structured)
            output = _sanitize_review(output, context)
        except (RuntimeErrorBase, ValidationError) as error:
            return CandidateReviewResult(
                weaknesses=[f"Agent Runtime review failed: {type(error).__name__}"],
                verdict="reject",
                runtime_calls=1,
            )
        finally:
            await _close_session(self.runtime, session)
        return CandidateReviewResult(
            expanded_idea=output.expanded_idea,
            supporting_evidence=output.supporting_evidence,
            counter_evidence=output.counter_evidence,
            source_refs=output.source_refs,
            uncertainty=output.uncertainty,
            weaknesses=output.weaknesses,
            obviousness=output.obviousness,
            factual_risk=output.factual_risk,
            alternative_explanations=output.alternative_explanations,
            verdict=output.verdict,
            runtime_calls=1,
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


def _review_prompt(candidate: Candidate, context: list[KnowledgeItem]) -> str:
    sources = [
        {
            "citation_ref": item.source_ref or f"knowledge:{item.id}",
            "title": item.title,
            "content": item.content[:3_000],
            "topics": item.topics,
        }
        for item in context
    ]
    language = (
        "Write every human-readable value in Simplified Chinese."
        if any("\u4e00" <= character <= "\u9fff" for character in candidate.statement)
        else "Write every human-readable value in the candidate's language."
    )
    payload = {
        "candidate": {
            "statement": candidate.statement,
            "explanation": candidate.explanation,
            "operator": candidate.operator,
        },
        "source_items": sources,
    }
    return "\n".join(
        [
            "Act as WanderMind's independent evidence reviewer and critic. Return only JSON.",
            language,
            "Judge the candidate as a testable structural-transfer hypothesis, not as a proven fact.",
            "Use only the supplied source items and copy citation_ref values exactly into source_refs.",
            "PASS when the connection is grounded, coherent, useful, testable, and explicitly caveated.",
            "Use REVISE for a promising but fixable claim and REJECT only for unsupported or contradictory claims.",
            "The expanded idea must preserve uncertainty and state a concrete validation path.",
            f"Input: {json.dumps(payload, ensure_ascii=False)}",
        ]
    )


def _sanitize_review(
    output: CandidateReviewOutput,
    context: list[KnowledgeItem],
) -> CandidateReviewOutput:
    allowed_refs = {item.source_ref or f"knowledge:{item.id}" for item in context}
    returned_refs = set(output.source_refs)
    if returned_refs and not returned_refs.issubset(allowed_refs):
        output.supporting_evidence = []
        output.counter_evidence = []
        output.source_refs = []
        output.uncertainty = max(output.uncertainty, 0.8)
        if output.verdict == "pass":
            output.verdict = "revise"
        return output
    output.source_refs = list(dict.fromkeys(output.source_refs))
    return output


def _string_usage(usage: dict[str, object], key: str) -> str | None:
    value = usage.get(key)
    return value if isinstance(value, str) and value else None


def _session_model(session: RuntimeSession) -> str | None:
    value = session.metadata.get("model")
    return value if isinstance(value, str) and value else None


async def _close_session(runtime: AgentRuntimeAdapter, session: RuntimeSession) -> None:
    with suppress(RuntimeErrorBase):
        await runtime.close_session(session)
