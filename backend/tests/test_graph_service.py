from __future__ import annotations

from uuid import uuid4

import pytest

from wandermind.application.graph_service import IdeaGraphService
from wandermind.infrastructure.errors import NotFoundError
from wandermind.models import KnowledgeEdge, KnowledgeItem, KnowledgeType, RelationType
from wandermind.repositories import InMemoryRepositoryBundle


@pytest.mark.asyncio
async def test_graph_queries_cover_lineage_evidence_and_contradictions() -> None:
    repositories = InMemoryRepositoryBundle()
    service = IdeaGraphService(repositories)
    question = KnowledgeItem(
        type=KnowledgeType.QUESTION,
        title="Question",
        content="Can local feedback prevent overload?",
    )
    connection = KnowledgeItem(
        type=KnowledgeType.IDEA,
        title="Connection",
        content="Colonies and queues both allocate local capacity.",
    )
    hypothesis = KnowledgeItem(
        type=KnowledgeType.HYPOTHESIS,
        title="Hypothesis",
        content="Local feedback can stabilize demand.",
    )
    evidence = KnowledgeItem(
        type=KnowledgeType.EVIDENCE,
        title="Evidence",
        content="Backpressure measurements show bounded queues.",
    )
    counter = KnowledgeItem(
        type=KnowledgeType.EVIDENCE,
        title="Counter evidence",
        content="Delayed signals can still cause oscillation.",
    )
    for item in (question, connection, hypothesis, evidence, counter):
        await repositories.knowledge.create(item)

    lineage_edges = [
        KnowledgeEdge(
            source_id=connection.id,
            target_id=question.id,
            relation_type=RelationType.INSPIRED_BY,
        ),
        KnowledgeEdge(
            source_id=hypothesis.id,
            target_id=connection.id,
            relation_type=RelationType.DERIVED_FROM,
        ),
    ]
    evidence_edge = KnowledgeEdge(
        source_id=evidence.id,
        target_id=hypothesis.id,
        relation_type=RelationType.EVIDENCE_FOR,
    )
    contradiction_edge = KnowledgeEdge(
        source_id=counter.id,
        target_id=hypothesis.id,
        relation_type=RelationType.CONTRADICTS,
    )
    for edge in (*lineage_edges, evidence_edge, contradiction_edge):
        await service.create_edge(edge)

    lineage = await service.lineage(hypothesis.id)
    assert {item.id for item in lineage.items} == {
        question.id,
        connection.id,
        hypothesis.id,
    }
    assert {edge.id for edge in lineage.edges} == {edge.id for edge in lineage_edges}
    assert (await service.evidence(hypothesis.id)).edges == [evidence_edge]
    assert (await service.contradictions(hypothesis.id)).edges == [contradiction_edge]


@pytest.mark.asyncio
async def test_graph_rejects_edges_with_missing_nodes() -> None:
    repositories = InMemoryRepositoryBundle()
    source = KnowledgeItem(title="Known", content="Known node")
    await repositories.knowledge.create(source)

    with pytest.raises(NotFoundError):
        await IdeaGraphService(repositories).create_edge(
            KnowledgeEdge(
                source_id=source.id,
                target_id=uuid4(),
                relation_type=RelationType.SIMILAR_TO,
            )
        )
