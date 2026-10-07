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
from wandermind.models import Candidate, KnowledgeItem, KnowledgeStatus
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


class ReviewEvidenceClaim(DomainModel):
    claim: str = Field(min_length=4, max_length=2_000)
    source_ref: str = Field(min_length=1, max_length=2_048)


class CandidateReviewOutput(DomainModel):
    revised_statement: str | None = Field(min_length=8, max_length=2_000)
    expanded_idea: str = Field(min_length=20, max_length=6_000)
    supporting_evidence: list[ReviewEvidenceClaim] = Field(max_length=8)
    counter_evidence: list[ReviewEvidenceClaim] = Field(max_length=8)
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
            output, supporting_refs, counter_refs = _sanitize_review(output, context)
        except (RuntimeErrorBase, ValidationError) as error:
            return CandidateReviewResult(
                weaknesses=[f"Agent Runtime review failed: {type(error).__name__}"],
                verdict="reject",
                runtime_calls=1,
            )
        finally:
            await _close_session(self.runtime, session)
        return CandidateReviewResult(
            revised_statement=output.revised_statement,
            expanded_idea=output.expanded_idea,
            supporting_evidence=[claim.claim for claim in output.supporting_evidence],
            counter_evidence=[claim.claim for claim in output.counter_evidence],
            supporting_source_refs=supporting_refs,
            counter_source_refs=counter_refs,
            source_refs=list(dict.fromkeys([*supporting_refs, *counter_refs])),
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
                "source": item.source,
                "epistemic_status": item.metadata.get("epistemic_status", "source_knowledge"),
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
            "Treat any source produced by autopilot as an unverified hypothesis, never as evidence.",
            "Never invent measurements, thresholds, percentages, units, or empirical outcomes.",
            "A number absent from the sources may only be proposed as an experiment parameter.",
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
            "source": item.source,
            "epistemic_status": item.metadata.get("epistemic_status", "source_knowledge"),
            "evidence_eligible": _evidence_eligible(item),
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
            "Each evidence item must be an object with claim and source_ref; copy citation_ref exactly.",
            "Cite both evidence-eligible source items in supporting_evidence or reject the candidate.",
            "Treat autopilot-generated source content as an unverified hypothesis, never as evidence.",
            "Never cite a source whose evidence_eligible value is false.",
            "Reject unsupported measurements, thresholds, percentages, units, or empirical outcomes.",
            "PASS when the connection is grounded, coherent, useful, testable, and explicitly caveated.",
            "Use REVISE for a promising but fixable claim and REJECT only for unsupported or contradictory claims.",
            "For REVISE, provide a concise revised_statement; otherwise set revised_statement to null.",
            "The expanded idea must preserve uncertainty and state a concrete validation path.",
            f"Input: {json.dumps(payload, ensure_ascii=False)}",
        ]
    )


def _sanitize_review(
    output: CandidateReviewOutput,
    context: list[KnowledgeItem],
) -> tuple[CandidateReviewOutput, list[str], list[str]]:
    trusted_refs = {
        item.source_ref or f"knowledge:{item.id}"
        for item in context
        if _evidence_eligible(item)
    }
    output.supporting_evidence = [
        claim for claim in output.supporting_evidence if claim.source_ref in trusted_refs
    ]
    output.counter_evidence = [
        claim for claim in output.counter_evidence if claim.source_ref in trusted_refs
    ]
    supporting_refs = list(
        dict.fromkeys(claim.source_ref for claim in output.supporting_evidence)
    )
    counter_refs = list(dict.fromkeys(claim.source_ref for claim in output.counter_evidence))
    if len(supporting_refs) < min(2, len(context)):
        output.uncertainty = max(output.uncertainty, 0.8)
        output.factual_risk = max(output.factual_risk, 0.65)
        output.verdict = "reject"
        output.weaknesses = list(
            dict.fromkeys(
                [
                    *output.weaknesses,
                    "The claim lacks grounded support from both independent source items.",
                ]
            )
        )
    if output.verdict == "revise" and not output.revised_statement:
        output.verdict = "reject"
        output.weaknesses = list(
            dict.fromkeys(
                [*output.weaknesses, "The requested revision did not provide a revised claim."]
            )
        )
    return output, supporting_refs, counter_refs


def _evidence_eligible(item: KnowledgeItem) -> bool:
    epistemic_status = str(item.metadata.get("epistemic_status", "source_knowledge"))
    return (
        item.status is KnowledgeStatus.ACTIVE
        and item.source != "autopilot"
        and epistemic_status
        not in {"reviewed_hypothesis", "quality_rejected", "encoding_corrupted"}
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
