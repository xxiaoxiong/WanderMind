from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from wandermind.models.base import DomainModel


class EvaluationStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class ExplorerOutput(DomainModel):
    expanded_idea: str
    implications: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    possible_support: list[str] = Field(default_factory=list)
    possible_failure_modes: list[str] = Field(default_factory=list)


class EvidenceOutput(DomainModel):
    supporting_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    uncertainty: float = Field(default=1.0, ge=0.0, le=1.0)
    status: EvaluationStatus = EvaluationStatus.COMPLETED
    error: str | None = None


class CriticVerdict(StrEnum):
    PASS = "pass"
    REVISE = "revise"
    REJECT = "reject"


class CriticOutput(DomainModel):
    weakness: list[str] = Field(default_factory=list)
    obviousness: float = Field(default=0.0, ge=0.0, le=1.0)
    over_analogy: bool = False
    factual_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    alternative_explanation: list[str] = Field(default_factory=list)
    verdict: CriticVerdict


class DeepEvaluationResult(DomainModel):
    explorer: ExplorerOutput | None = None
    evidence: EvidenceOutput
    critic: CriticOutput
