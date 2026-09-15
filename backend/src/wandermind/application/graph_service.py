from __future__ import annotations

from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from wandermind.infrastructure.errors import NotFoundError
from wandermind.models import KnowledgeEdge, KnowledgeItem, RelationType
from wandermind.repositories.protocols import RepositoryBundle


@dataclass(slots=True)
class GraphView:
    items: list[KnowledgeItem]
    edges: list[KnowledgeEdge]


class IdeaGraphService:
    LINEAGE_RELATIONS: ClassVar[frozenset[RelationType]] = frozenset(
        {
            RelationType.DERIVED_FROM,
            RelationType.EVOLVES_FROM,
            RelationType.INSPIRED_BY,
        }
    )
    EVIDENCE_RELATIONS: ClassVar[frozenset[RelationType]] = frozenset(
        {
            RelationType.EVIDENCE_FOR,
            RelationType.EVIDENCE_AGAINST,
        }
    )

    def __init__(self, repositories: RepositoryBundle) -> None:
        self.repositories = repositories

    async def create_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        await self._require_item(edge.source_id)
        await self._require_item(edge.target_id)
        return await self.repositories.graph.create(edge)

    async def neighbors(
        self,
        item_id: UUID,
        relation_types: AbstractSet[RelationType] | None = None,
    ) -> GraphView:
        root = await self._require_item(item_id)
        edges = await self.repositories.graph.list_for_item(item_id)
        if relation_types:
            edges = [edge for edge in edges if edge.relation_type in relation_types]
        return await self._view(root, edges)

    async def lineage(self, item_id: UUID, *, max_depth: int = 10) -> GraphView:
        root = await self._require_item(item_id)
        visited = {item_id}
        frontier = {item_id}
        edges_by_id: dict[UUID, KnowledgeEdge] = {}
        for _ in range(max_depth):
            next_frontier: set[UUID] = set()
            for current_id in sorted(frontier, key=str):
                for edge in await self.repositories.graph.list_for_item(current_id):
                    if edge.relation_type not in self.LINEAGE_RELATIONS:
                        continue
                    edges_by_id.setdefault(edge.id, edge)
                    adjacent_id = edge.target_id if edge.source_id == current_id else edge.source_id
                    if adjacent_id not in visited:
                        visited.add(adjacent_id)
                        next_frontier.add(adjacent_id)
            if not next_frontier:
                break
            frontier = next_frontier
        return await self._view(root, list(edges_by_id.values()))

    async def evidence(self, item_id: UUID) -> GraphView:
        return await self.neighbors(item_id, self.EVIDENCE_RELATIONS)

    async def contradictions(self, item_id: UUID) -> GraphView:
        return await self.neighbors(item_id, {RelationType.CONTRADICTS})

    async def _view(
        self,
        root: KnowledgeItem,
        edges: list[KnowledgeEdge],
    ) -> GraphView:
        item_ids = {root.id}
        for edge in edges:
            item_ids.update((edge.source_id, edge.target_id))
        items = [root]
        for item_id in sorted(item_ids - {root.id}, key=str):
            item = await self.repositories.knowledge.get(item_id)
            if item is not None:
                items.append(item)
        return GraphView(items=items, edges=sorted(edges, key=lambda edge: str(edge.id)))

    async def _require_item(self, item_id: UUID) -> KnowledgeItem:
        item = await self.repositories.knowledge.get(item_id)
        if item is None:
            raise NotFoundError("knowledge item not found", details={"id": str(item_id)})
        return item
