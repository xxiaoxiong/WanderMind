from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from wandermind.cognitive.embedding import cosine_distance
from wandermind.cognitive.text import significant_tokens
from wandermind.models import KnowledgeItem
from wandermind.models.base import DomainModel


class AssociationType(StrEnum):
    SEMANTIC = "semantic"
    CONTRADICTION = "contradiction"
    ANALOGY_CANDIDATE = "analogy_candidate"
    CAUSAL_CANDIDATE = "causal_candidate"
    TEMPORAL = "temporal"
    SHARED_PATTERN = "shared_pattern"


class Association(DomainModel):
    type: AssociationType
    strength: float = Field(ge=0.0, le=1.0)
    distance: float = Field(ge=0.0, le=2.0)
    shared_terms: list[str] = Field(default_factory=list)
    explanation: str


class AssociationEngine:
    def analyze(self, left: KnowledgeItem, right: KnowledgeItem) -> Association:
        distance = 1.0
        if left.embedding and right.embedding:
            distance = cosine_distance(left.embedding, right.embedding)
        left_terms = set(significant_tokens(f"{left.title} {left.content}"))
        right_terms = set(significant_tokens(f"{right.title} {right.content}"))
        raw_shared = sorted(left_terms & right_terms)
        generic_terms = {
            "between",
            "exposing",
            "in",
            "observers",
            "pattern",
            "preserving",
            "see",
            "specific",
            "systems",
            "using",
            "when",
            "while",
        }
        shared = [term for term in raw_shared if term not in generic_terms][:8]
        contradiction_markers = {"not", "never", "against", "反对", "并非", "不是"}
        causal_markers = {"because", "therefore", "cause", "因为", "导致", "因此"}
        all_terms = left_terms | right_terms
        if contradiction_markers & all_terms:
            association_type = AssociationType.CONTRADICTION
        elif causal_markers & all_terms:
            association_type = AssociationType.CAUSAL_CANDIDATE
        elif shared and distance > 0.45:
            association_type = AssociationType.SHARED_PATTERN
        elif distance > 0.55:
            association_type = AssociationType.ANALOGY_CANDIDATE
        else:
            association_type = AssociationType.SEMANTIC
        distance_quality = 1.0 - min(1.0, abs(distance - 0.65) / 0.65)
        shared_bonus = min(0.25, len(raw_shared) * 0.05)
        strength = max(0.0, min(1.0, 0.7 * distance_quality + shared_bonus))
        bridge = ", ".join(shared) if shared else "a structural rather than lexical bridge"
        return Association(
            type=association_type,
            strength=strength,
            distance=distance,
            shared_terms=shared,
            explanation=(
                f"{left.title} and {right.title} are connected through {bridge}; "
                f"their semantic distance is {distance:.2f}."
            ),
        )
