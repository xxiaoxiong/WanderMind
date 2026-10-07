from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wandermind.models import Wonder

QUALITY_GATE_VERSION = 2


@dataclass(frozen=True, slots=True)
class QualityGateResult:
    accepted: bool
    reasons: tuple[str, ...]

    def as_metadata(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "version": QUALITY_GATE_VERSION,
        }


@dataclass(frozen=True, slots=True)
class AutopilotQualityPolicy:
    minimum_total: float = 0.63
    minimum_confidence: float = 0.57
    minimum_coherence: float = 0.70
    minimum_evidence_potential: float = 0.50
    maximum_redundancy: float = 0.45
    maximum_arbitrariness: float = 0.55
    maximum_hallucination_risk: float = 0.35
    maximum_uncertainty: float = 0.60
    maximum_factual_risk: float = 0.40
    maximum_revision_factual_risk: float = 0.35
    minimum_grounded_sources: int = 2

    def evaluate(
        self,
        wonder: Wonder,
        *,
        configured_threshold: float = 0.0,
    ) -> QualityGateResult:
        reasons: list[str] = []
        scores = wonder.scores
        minimum_total = max(self.minimum_total, configured_threshold)
        if scores.total < minimum_total:
            reasons.append("total_score_below_quality_floor")
        if wonder.confidence < self.minimum_confidence:
            reasons.append("confidence_too_low")
        if scores.coherence < self.minimum_coherence:
            reasons.append("coherence_too_low")
        if scores.evidence_potential < self.minimum_evidence_potential:
            reasons.append("evidence_potential_too_low")
        if scores.redundancy > self.maximum_redundancy:
            reasons.append("redundancy_too_high")
        if scores.arbitrariness > self.maximum_arbitrariness:
            reasons.append("arbitrariness_too_high")
        if scores.hallucination_risk > self.maximum_hallucination_risk:
            reasons.append("hallucination_risk_too_high")
        if not wonder.supporting_evidence:
            reasons.append("supporting_evidence_missing")
        if not wonder.counter_evidence:
            reasons.append("counter_evidence_missing")
        if not wonder.questions:
            reasons.append("validation_questions_missing")

        review = wonder.metadata.get("runtime_review")
        if not isinstance(review, dict):
            reasons.append("independent_review_missing")
            return QualityGateResult(accepted=False, reasons=tuple(reasons))

        verdict = review.get("verdict")
        uncertainty = _number(review.get("uncertainty"), default=1.0)
        factual_risk = _number(review.get("factual_risk"), default=1.0)
        grounded_refs = review.get("supporting_source_refs")
        grounded_source_count = (
            len({str(value) for value in grounded_refs if value})
            if isinstance(grounded_refs, list)
            else 0
        )
        if grounded_source_count < self.minimum_grounded_sources:
            reasons.append("insufficient_grounded_sources")
        if uncertainty > self.maximum_uncertainty:
            reasons.append("uncertainty_too_high")
        if verdict == "pass":
            if factual_risk > self.maximum_factual_risk:
                reasons.append("factual_risk_too_high")
        elif verdict == "revise" and wonder.metadata.get("promotion_basis") == "runtime_revision":
            if factual_risk > self.maximum_revision_factual_risk:
                reasons.append("revised_claim_factual_risk_too_high")
            if not review.get("revised_statement") or not review.get("expanded_idea"):
                reasons.append("runtime_revision_missing")
        else:
            reasons.append("independent_review_not_passed")

        return QualityGateResult(accepted=not reasons, reasons=tuple(reasons))


def _number(value: Any, *, default: float) -> float:
    return (
        float(value) if isinstance(value, int | float) and not isinstance(value, bool) else default
    )
