from __future__ import annotations

import builtins
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from wandermind.models import (
    Candidate,
    Feedback,
    KnowledgeEdge,
    KnowledgeItem,
    Seed,
    WanderSession,
    Wonder,
)
from wandermind.runtime.base import RuntimeSession


class IdentifiedEntity(Protocol):
    id: UUID


class InMemoryStore[ModelT: IdentifiedEntity]:
    def __init__(self) -> None:
        self._items: dict[UUID, ModelT] = {}

    async def create(self, item: ModelT) -> ModelT:
        item_id = item.id
        if item_id in self._items:
            raise ValueError(f"item {item_id} already exists")
        self._items[item_id] = item
        return item

    async def get(self, item_id: UUID) -> ModelT | None:
        return self._items.get(item_id)

    async def update(self, item: ModelT) -> ModelT:
        item_id = item.id
        if item_id not in self._items:
            raise KeyError(item_id)
        self._items[item_id] = item
        return item

    async def delete(self, item_id: UUID) -> bool:
        return self._items.pop(item_id, None) is not None

    async def list(self, *, offset: int = 0, limit: int = 50) -> builtins.list[ModelT]:
        return builtins.list(self._items.values())[offset : offset + limit]


class InMemoryKnowledgeRepository(InMemoryStore[KnowledgeItem]):
    async def search(self, query: str, *, limit: int = 20) -> builtins.list[KnowledgeItem]:
        needle = query.casefold().strip()
        if not needle:
            return []
        matches = [
            item
            for item in self._items.values()
            if needle in item.title.casefold()
            or needle in item.content.casefold()
            or any(needle in topic.casefold() for topic in item.topics)
        ]
        return matches[:limit]


class InMemoryGraphRepository(InMemoryStore[KnowledgeEdge]):
    async def list_for_item(self, item_id: UUID) -> builtins.list[KnowledgeEdge]:
        return [
            edge
            for edge in self._items.values()
            if edge.source_id == item_id or edge.target_id == item_id
        ]


class InMemorySeedRepository(InMemoryStore[Seed]):
    pass


class InMemoryCandidateRepository(InMemoryStore[Candidate]):
    async def list_for_session(self, session_id: UUID) -> builtins.list[Candidate]:
        return [item for item in self._items.values() if item.session_id == session_id]


class InMemoryWonderRepository(InMemoryStore[Wonder]):
    async def search_similar(self, text: str, *, limit: int = 20) -> builtins.list[Wonder]:
        terms = {term.casefold() for term in text.split() if len(term) > 2}
        scored: list[tuple[int, Wonder]] = []
        for wonder in self._items.values():
            haystack = f"{wonder.statement} {wonder.explanation}".casefold()
            score = sum(term in haystack for term in terms)
            if score:
                scored.append((score, wonder))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [wonder for _, wonder in scored[:limit]]


class InMemorySessionRepository(InMemoryStore[WanderSession]):
    pass


class InMemoryFeedbackRepository(InMemoryStore[Feedback]):
    async def list_for_wonder(self, wonder_id: UUID) -> builtins.list[Feedback]:
        return [item for item in self._items.values() if item.wonder_id == wonder_id]


class InMemoryRuntimeSessionRepository(InMemoryStore[RuntimeSession]):
    async def list_for_wander(self, wander_session_id: UUID) -> builtins.list[RuntimeSession]:
        return [
            item
            for item in self._items.values()
            if item.wander_session_id == wander_session_id
        ]


@dataclass(slots=True)
class InMemoryRepositoryBundle:
    knowledge: InMemoryKnowledgeRepository = field(default_factory=InMemoryKnowledgeRepository)
    graph: InMemoryGraphRepository = field(default_factory=InMemoryGraphRepository)
    seeds: InMemorySeedRepository = field(default_factory=InMemorySeedRepository)
    candidates: InMemoryCandidateRepository = field(default_factory=InMemoryCandidateRepository)
    wonders: InMemoryWonderRepository = field(default_factory=InMemoryWonderRepository)
    sessions: InMemorySessionRepository = field(default_factory=InMemorySessionRepository)
    feedback: InMemoryFeedbackRepository = field(default_factory=InMemoryFeedbackRepository)
    runtime_sessions: InMemoryRuntimeSessionRepository = field(
        default_factory=InMemoryRuntimeSessionRepository
    )
