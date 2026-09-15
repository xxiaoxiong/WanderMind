from uuid import uuid4

import pytest

from wandermind.models import Candidate, KnowledgeEdge, KnowledgeItem, RelationType, WonderType
from wandermind.repositories import InMemoryRepositoryBundle


@pytest.mark.asyncio
async def test_knowledge_repository_contract() -> None:
    repositories = InMemoryRepositoryBundle()
    item = KnowledgeItem(title="Mind wandering", content="Spontaneous thought can be productive.")

    await repositories.knowledge.create(item)

    assert await repositories.knowledge.get(item.id) == item
    assert await repositories.knowledge.search("productive") == [item]
    assert await repositories.knowledge.list(limit=1) == [item]
    assert await repositories.knowledge.delete(item.id)
    assert await repositories.knowledge.get(item.id) is None


@pytest.mark.asyncio
async def test_graph_repository_lists_both_directions() -> None:
    repositories = InMemoryRepositoryBundle()
    first_id = uuid4()
    second_id = uuid4()
    edge = KnowledgeEdge(
        source_id=first_id,
        target_id=second_id,
        relation_type=RelationType.INSPIRED_BY,
    )

    await repositories.graph.create(edge)

    assert await repositories.graph.list_for_item(first_id) == [edge]
    assert await repositories.graph.list_for_item(second_id) == [edge]


@pytest.mark.asyncio
async def test_candidate_repository_filters_by_session() -> None:
    repositories = InMemoryRepositoryBundle()
    session_id = uuid4()
    candidate = Candidate(
        session_id=session_id,
        candidate_type=WonderType.CONNECTION,
        statement="A scheduling analogy",
        explanation="Both systems allocate scarce attention.",
        seed_id=uuid4(),
        source_items=[uuid4(), uuid4()],
        operator="analogy",
    )

    await repositories.candidates.create(candidate)

    assert await repositories.candidates.list_for_session(session_id) == [candidate]
    assert await repositories.candidates.list_for_session(uuid4()) == []
