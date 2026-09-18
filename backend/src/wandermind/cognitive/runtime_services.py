from __future__ import annotations

from typing import Protocol

from pydantic import Field

from wandermind.cognitive.operators import OperatorContext, OperatorResult
from wandermind.models import Candidate, KnowledgeItem
from wandermind.models.base import DomainModel


class CandidateSynthesisResult(DomainModel):
    operator_result: OperatorResult
    runtime_calls: int = Field(default=0, ge=0)
    verified: bool = False
    provider: str | None = None
    model: str | None = None
    error: str | None = None


class CandidateReviewResult(DomainModel):
    expanded_idea: str | None = None
    supporting_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    uncertainty: float = Field(default=1.0, ge=0.0, le=1.0)
    weaknesses: list[str] = Field(default_factory=list)
    obviousness: float = Field(default=0.0, ge=0.0, le=1.0)
    factual_risk: float = Field(default=1.0, ge=0.0, le=1.0)
    alternative_explanations: list[str] = Field(default_factory=list)
    verdict: str
    runtime_calls: int = Field(default=0, ge=0)


class CandidateSynthesizer(Protocol):
    async def synthesize(
        self,
        context: OperatorContext,
        draft: OperatorResult,
        *,
        wander_session_id: str,
    ) -> CandidateSynthesisResult: ...


class CandidateReviewer(Protocol):
    async def review(
        self,
        candidate: Candidate,
        context: list[KnowledgeItem],
        *,
        max_runtime_calls: int,
    ) -> CandidateReviewResult: ...
