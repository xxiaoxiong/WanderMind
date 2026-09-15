from uuid import uuid4

import pytest

from wandermind.cognitive.embedding import HashEmbeddingAdapter, cosine_similarity
from wandermind.cognitive.ingestion import DuplicateKnowledgeError, IngestionService
from wandermind.cognitive.patches import PatchBuilder
from wandermind.cognitive.retrieval import DistanceBand, SemanticRetriever, classify_band
from wandermind.models import KnowledgeItem, Seed
from wandermind.repositories import InMemoryRepositoryBundle


@pytest.mark.asyncio
async def test_hash_embedding_is_deterministic_and_normalized() -> None:
    adapter = HashEmbeddingAdapter(dimensions=32)
    first = await adapter.embed_text("semantic foraging and creative cognition")
    second = await adapter.embed_text("semantic foraging and creative cognition")
    batch = await adapter.embed_batch(["alpha", "beta"])

    assert first == second
    assert len(first) == 32
    assert cosine_similarity(first, second) == pytest.approx(1.0)
    assert len(batch) == 2
    with pytest.raises(ValueError, match="empty"):
        await adapter.embed_text(" ")


@pytest.mark.asyncio
async def test_ingestion_normalizes_unicode_and_rejects_duplicates() -> None:
    repositories = InMemoryRepositoryBundle()
    service = IngestionService(repositories.knowledge, HashEmbeddingAdapter(32))

    item = await service.ingest_text(
        "  认知漫游   可以连接不同领域。  ",
        title="认知漫游",
        metadata={"domain": "cognition"},
    )

    assert item.content == "认知漫游 可以连接不同领域。"
    assert item.embedding is not None
    assert item.metadata["normalized_hash"]
    assert item.metadata["domain"] == "cognition"
    with pytest.raises(DuplicateKnowledgeError):
        await service.ingest_text("认知漫游 可以连接不同领域。", title="重复")


def test_distance_bands_and_controlled_remote_retrieval() -> None:
    query = [1.0, 0.0]
    vectors = [[1.0, 0.0], [0.9, 0.1], [0.7, 0.7], [0.0, 1.0], [-1.0, 0.0]]
    items = [
        KnowledgeItem(title=f"item-{index}", content="content", embedding=vector)
        for index, vector in enumerate(vectors)
    ]
    retriever = SemanticRetriever()

    ranked = retriever.rank(query, items)
    remote = retriever.controlled_remote(
        query,
        items,
        relevance_floor=0.25,
        distance_floor=0.2,
        distance_ceiling=1.2,
    )

    assert [result.item.title for result in ranked[:2]] == ["item-0", "item-1"]
    assert all(result.band in {DistanceBand.MODERATE, DistanceBand.REMOTE} for result in remote)
    assert classify_band(0.1, (0.2, 0.5, 0.8)) is DistanceBand.NEAR
    assert classify_band(0.9, (0.2, 0.5, 0.8)) is DistanceBand.VERY_REMOTE


def test_retrieval_excludes_requested_ids() -> None:
    excluded_id = uuid4()
    excluded = KnowledgeItem(id=excluded_id, title="excluded", content="x", embedding=[1.0, 0.0])
    included = KnowledgeItem(title="included", content="y", embedding=[0.0, 1.0])

    results = SemanticRetriever().nearest(
        [1.0, 0.0],
        [excluded, included],
        exclude_ids={excluded_id},
    )

    assert [result.item.id for result in results] == [included.id]


@pytest.mark.asyncio
async def test_retrieval_uses_exact_concept_title_as_a_lexical_anchor() -> None:
    adapter = HashEmbeddingAdapter(32)
    query_text = "How does backpressure control overloaded software queues?"
    query = await adapter.embed_text(query_text)
    distractor = KnowledgeItem(
        title="Urban density",
        content="A generic pattern about shared capacity and coordination.",
        embedding=await adapter.embed_text("nearby query context"),
    )
    target = KnowledgeItem(
        title="Distributed Systems: backpressure",
        content="Backpressure regulates demand in overloaded queues.",
        embedding=await adapter.embed_text("unrelated vector text"),
    )

    ranked = SemanticRetriever().rank(query, [distractor, target], query_text=query_text)

    assert ranked[0].item.id == target.id


def test_patch_builder_groups_domains_and_uses_centroid_coherence() -> None:
    items = [
        KnowledgeItem(
            title=f"item-{index}",
            content="feedback system",
            embedding=[1.0, float(index) / 10],
            metadata={"domain": "systems"},
        )
        for index in range(20)
    ]
    builder = PatchBuilder()
    patches = builder.build(Seed(content="feedback"), items)
    domain_patch = next(patch for patch in patches if patch.label == "domain:systems")
    memberships = builder.memberships(patches, items)

    assert len(patches) > 1
    assert len(domain_patch.member_ids) == 20
    assert 0 <= domain_patch.coherence <= 1
    assert len(memberships) > len(items)
    assert all(membership.reason.startswith("matched ") for membership in memberships)
