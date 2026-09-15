from __future__ import annotations

from enum import StrEnum
from statistics import quantiles
from uuid import UUID

from pydantic import Field

from wandermind.cognitive.embedding import cosine_distance
from wandermind.cognitive.text import normalize_text, significant_tokens
from wandermind.models import KnowledgeItem
from wandermind.models.base import DomainModel


class DistanceBand(StrEnum):
    NEAR = "near"
    MODERATE = "moderate"
    REMOTE = "remote"
    VERY_REMOTE = "very_remote"


class RetrievedItem(DomainModel):
    item: KnowledgeItem
    distance: float = Field(ge=0.0, le=2.0)
    relevance: float = Field(ge=0.0, le=1.0)
    band: DistanceBand


def _boundaries(distances: list[float]) -> tuple[float, float, float]:
    if len(distances) < 4:
        ordered = sorted(distances)
        if not ordered:
            return (0.25, 0.55, 0.85)
        return (
            ordered[max(0, len(ordered) // 4)],
            ordered[max(0, len(ordered) // 2)],
            ordered[max(0, (len(ordered) * 3) // 4)],
        )
    quartiles = quantiles(distances, n=4, method="inclusive")
    return quartiles[0], quartiles[1], quartiles[2]


def classify_band(distance: float, boundaries: tuple[float, float, float]) -> DistanceBand:
    first, second, third = boundaries
    if distance <= first:
        return DistanceBand.NEAR
    if distance <= second:
        return DistanceBand.MODERATE
    if distance <= third:
        return DistanceBand.REMOTE
    return DistanceBand.VERY_REMOTE


class SemanticRetriever:
    def rank(
        self,
        query_embedding: list[float],
        items: list[KnowledgeItem],
        *,
        query_text: str | None = None,
        exclude_ids: set[UUID] | None = None,
    ) -> list[RetrievedItem]:
        excluded = exclude_ids or set()
        raw = [
            (
                item,
                _retrieval_distance(query_embedding, item, query_text=query_text),
            )
            for item in items
            if item.id not in excluded and item.embedding is not None
        ]
        raw.sort(key=lambda pair: pair[1])
        boundaries = _boundaries([distance for _, distance in raw])
        return [
            RetrievedItem(
                item=item,
                distance=distance,
                relevance=max(0.0, min(1.0, 1.0 - distance / 2.0)),
                band=classify_band(distance, boundaries),
            )
            for item, distance in raw
        ]

    def nearest(
        self,
        query_embedding: list[float],
        items: list[KnowledgeItem],
        *,
        limit: int = 10,
        exclude_ids: set[UUID] | None = None,
    ) -> list[RetrievedItem]:
        return self.rank(query_embedding, items, exclude_ids=exclude_ids)[:limit]

    def by_band(
        self,
        query_embedding: list[float],
        items: list[KnowledgeItem],
        band: DistanceBand,
        *,
        limit: int = 10,
        exclude_ids: set[UUID] | None = None,
    ) -> list[RetrievedItem]:
        ranked = self.rank(query_embedding, items, exclude_ids=exclude_ids)
        return [result for result in ranked if result.band is band][:limit]

    def controlled_remote(
        self,
        query_embedding: list[float],
        items: list[KnowledgeItem],
        *,
        relevance_floor: float = 0.25,
        distance_floor: float = 0.35,
        distance_ceiling: float = 1.35,
        limit: int = 10,
        exclude_ids: set[UUID] | None = None,
    ) -> list[RetrievedItem]:
        ranked = self.rank(query_embedding, items, exclude_ids=exclude_ids)
        return [
            result
            for result in ranked
            if result.relevance >= relevance_floor
            and distance_floor <= result.distance <= distance_ceiling
            and result.band in {DistanceBand.MODERATE, DistanceBand.REMOTE}
        ][:limit]


class HistoricalNoveltyChecker:
    def __init__(self, retriever: SemanticRetriever) -> None:
        self.retriever = retriever

    def novelty(
        self,
        candidate_embedding: list[float],
        historical_items: list[KnowledgeItem],
    ) -> float:
        nearest = self.retriever.nearest(candidate_embedding, historical_items, limit=1)
        if not nearest:
            return 1.0
        return max(0.0, min(1.0, nearest[0].distance))


def _retrieval_distance(
    query_embedding: list[float],
    item: KnowledgeItem,
    *,
    query_text: str | None,
) -> float:
    if item.embedding is None:
        return 2.0
    semantic_distance = cosine_distance(query_embedding, item.embedding)
    if not query_text:
        return semantic_distance
    query_terms = set(significant_tokens(query_text))
    if not query_terms:
        return semantic_distance
    item_terms = set(significant_tokens(f"{item.title} {item.summary or item.content}"))
    token_coverage = len(query_terms & item_terms) / len(query_terms)
    concept_title = normalize_text(item.title.rsplit(":", maxsplit=1)[-1]).casefold()
    title_match = (
        0.85 if len(concept_title) >= 4 and concept_title in query_text.casefold() else 0.0
    )
    lexical_signal = max(token_coverage, title_match)
    return max(0.0, min(2.0, semantic_distance - 0.45 * lexical_signal))
