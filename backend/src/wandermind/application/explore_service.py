from __future__ import annotations

import json
from contextlib import suppress

from pydantic import ValidationError

from wandermind.application.evaluation import (
    CriticOutput,
    CriticVerdict,
    DeepEvaluationResult,
    EvaluationStatus,
    EvidenceOutput,
    ExplorerOutput,
)
from wandermind.models import Candidate, KnowledgeItem
from wandermind.runtime import (
    AgentRuntimeAdapter,
    RuntimeErrorBase,
    RuntimeMalformedOutputError,
    RuntimeSession,
    RuntimeTask,
    SandboxMode,
    run_with_retry,
)


class ExplorerService:
    def __init__(self, runtime: AgentRuntimeAdapter, *, max_retries: int = 1) -> None:
        self.runtime = runtime
        self.max_retries = max_retries

    async def explore(self, candidate: Candidate, context: list[KnowledgeItem]) -> ExplorerOutput:
        session = await self.runtime.start_session("explorer")
        prompt = chr(10).join(
            [
                "Expand the candidate without asserting unsupported facts. Return only JSON.",
                f"Candidate: {candidate.statement}",
                f"Explanation: {candidate.explanation}",
                f"Context: {_context_payload(context)}",
            ]
        )
        task = RuntimeTask(
            prompt=prompt,
            output_schema=ExplorerOutput.model_json_schema(),
            sandbox=SandboxMode.READ_ONLY,
            metadata={"wander_session_id": str(candidate.session_id)},
        )
        try:
            result = await run_with_retry(
                self.runtime,
                session,
                task,
                max_retries=self.max_retries,
            )
            try:
                return ExplorerOutput.model_validate(result.structured)
            except ValidationError as error:
                raise RuntimeMalformedOutputError("explorer output failed validation") from error
        finally:
            await _close_session(self.runtime, session)


class EvidenceService:
    def __init__(self, runtime: AgentRuntimeAdapter, *, max_retries: int = 1) -> None:
        self.runtime = runtime
        self.max_retries = max_retries

    async def collect(self, candidate: Candidate, context: list[KnowledgeItem]) -> EvidenceOutput:
        session = await self.runtime.start_session("evidence")
        prompt = chr(10).join(
            [
                "Find support and counter-evidence. Never invent a source reference. Return only JSON.",
                f"Candidate: {candidate.statement}",
                f"Context: {_context_payload(context)}",
            ]
        )
        task = RuntimeTask(
            prompt=prompt,
            output_schema=EvidenceOutput.model_json_schema(),
            sandbox=SandboxMode.READ_ONLY,
            metadata={"wander_session_id": str(candidate.session_id)},
        )
        try:
            result = await run_with_retry(
                self.runtime,
                session,
                task,
                max_retries=self.max_retries,
            )
            evidence = EvidenceOutput.model_validate(result.structured)
        except (RuntimeErrorBase, ValidationError) as error:
            return EvidenceOutput(
                uncertainty=1.0,
                status=EvaluationStatus.FAILED,
                error=type(error).__name__,
            )
        finally:
            await _close_session(self.runtime, session)
        if not evidence.source_refs:
            evidence.supporting_evidence = []
            evidence.counter_evidence = []
            evidence.uncertainty = max(evidence.uncertainty, 0.8)
        return evidence


class CriticService:
    def __init__(self, runtime: AgentRuntimeAdapter, *, max_retries: int = 1) -> None:
        self.runtime = runtime
        self.max_retries = max_retries

    async def critique(self, candidate: Candidate, evidence: EvidenceOutput) -> CriticOutput:
        session = await self.runtime.start_session("critic")
        prompt = chr(10).join(
            [
                "Independently critique the candidate. Do not assume it is correct. Return only JSON.",
                f"Candidate: {candidate.statement}",
                f"Evidence: {evidence.model_dump_json()}",
            ]
        )
        task = RuntimeTask(
            prompt=prompt,
            output_schema=CriticOutput.model_json_schema(),
            sandbox=SandboxMode.READ_ONLY,
            metadata={"wander_session_id": str(candidate.session_id)},
        )
        try:
            result = await run_with_retry(
                self.runtime,
                session,
                task,
                max_retries=self.max_retries,
            )
            return CriticOutput.model_validate(result.structured)
        except (RuntimeErrorBase, ValidationError):
            return CriticOutput(
                weakness=["Independent critic was unavailable."],
                factual_risk=1.0,
                verdict=CriticVerdict.REJECT,
            )
        finally:
            await _close_session(self.runtime, session)


class DeepEvaluationService:
    def __init__(
        self,
        explorer: ExplorerService,
        evidence: EvidenceService,
        critic: CriticService,
    ) -> None:
        self.explorer = explorer
        self.evidence = evidence
        self.critic = critic

    async def evaluate(
        self,
        candidate: Candidate,
        context: list[KnowledgeItem],
        *,
        max_runtime_calls: int = 3,
    ) -> DeepEvaluationResult:
        explorer_output: ExplorerOutput | None = None
        if max_runtime_calls >= 1:
            with suppress(RuntimeErrorBase):
                explorer_output = await self.explorer.explore(candidate, context)
        if max_runtime_calls >= 2:
            evidence_output = await self.evidence.collect(candidate, context)
        else:
            evidence_output = EvidenceOutput(
                uncertainty=1.0,
                status=EvaluationStatus.FAILED,
                error="runtime_budget_exhausted",
            )
        if max_runtime_calls >= 3:
            critic_output = await self.critic.critique(candidate, evidence_output)
        else:
            critic_output = CriticOutput(
                weakness=["Runtime budget did not permit an independent critic."],
                factual_risk=1.0,
                verdict=CriticVerdict.REJECT,
            )
        return DeepEvaluationResult(
            explorer=explorer_output,
            evidence=evidence_output,
            critic=critic_output,
        )


def _context_payload(context: list[KnowledgeItem]) -> str:
    return json.dumps(
        [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary or item.content[:500],
                "source_ref": item.source_ref,
            }
            for item in context
        ],
        ensure_ascii=False,
    )


async def _close_session(runtime: AgentRuntimeAdapter, session: RuntimeSession) -> None:
    with suppress(RuntimeErrorBase):
        await runtime.close_session(session)
