from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection

from wandermind.cognitive.embedding import cosine_distance
from wandermind.models import KnowledgeItem, KnowledgePatch, PatchMembership, Seed


class PatchBuilder:
    def build(self, seed: Seed, items: list[KnowledgeItem]) -> list[KnowledgePatch]:
        grouped: dict[tuple[str, str], list[KnowledgeItem]] = defaultdict(list)
        for item in items:
            for patch_type, label in self._labels(item):
                grouped[(patch_type, label)].append(item)
        patches = []
        for (patch_type, label), members in grouped.items():
            coherence = self._coherence(members)
            patches.append(
                KnowledgePatch(
                    seed_id=seed.id,
                    label=f"{patch_type}:{label}",
                    center_item_id=self._center(members).id,
                    member_ids=[member.id for member in members],
                    coherence=coherence,
                    metadata={"patch_type": patch_type, "facet": label},
                )
            )
        return sorted(
            patches, key=lambda patch: (len(patch.member_ids), patch.coherence), reverse=True
        )

    def memberships(
        self,
        patches: list[KnowledgePatch],
        items: list[KnowledgeItem],
    ) -> list[PatchMembership]:
        items_by_id = {item.id: item for item in items}
        memberships: list[PatchMembership] = []
        for patch in patches:
            center = items_by_id.get(patch.center_item_id) if patch.center_item_id else None
            for item_id in patch.member_ids:
                item = items_by_id[item_id]
                distance = 0.0
                if center and center.embedding and item.embedding:
                    distance = cosine_distance(center.embedding, item.embedding)
                memberships.append(
                    PatchMembership(
                        patch_id=patch.id,
                        knowledge_item_id=item.id,
                        semantic_distance=distance,
                        relevance=max(0.0, min(1.0, 1.0 - distance / 2.0)),
                        novelty=max(0.0, min(1.0, distance)),
                        reason=f"matched {patch.metadata['patch_type']} facet {patch.metadata['facet']}",
                    )
                )
        return memberships

    def _labels(self, item: KnowledgeItem) -> list[tuple[str, str]]:
        labels: list[tuple[str, str]] = []
        for key in ("domain", "project"):
            value = item.metadata.get(key)
            if value:
                labels.append((key, str(value)))
        labels.extend(("topic", topic) for topic in item.topics[:2])
        if item.event_time is not None:
            labels.append(("temporal", item.event_time.strftime("%Y-%m")))
        embedding = item.embedding
        if embedding:
            dominant = max(range(len(embedding)), key=lambda index: abs(embedding[index]))
            labels.append(("cluster", str(dominant % 8)))
        if not labels:
            labels.append(("type", item.type.value))
        return list(dict.fromkeys(labels))

    def _center(self, items: list[KnowledgeItem]) -> KnowledgeItem:
        embedded = [item for item in items if item.embedding]
        if len(embedded) < 2:
            return items[0]
        dimensions = len(embedded[0].embedding or [])
        compatible: list[tuple[KnowledgeItem, list[float]]] = []
        for item in embedded:
            embedding = item.embedding
            if embedding is not None and len(embedding) == dimensions:
                compatible.append((item, embedding))
        if not compatible:
            return items[0]
        centroid = [
            sum(embedding[index] for _, embedding in compatible) / len(compatible)
            for index in range(dimensions)
        ]
        return min(
            compatible,
            key=lambda pair: cosine_distance(pair[1], centroid),
        )[0]

    def _coherence(self, items: list[KnowledgeItem]) -> float:
        embeddings = [item.embedding for item in items if item.embedding]
        if len(embeddings) < 2:
            return 1.0
        dimensions = len(embeddings[0])
        compatible = [embedding for embedding in embeddings if len(embedding) == dimensions]
        if len(compatible) < 2:
            return 1.0
        centroid = [
            sum(embedding[index] for embedding in compatible) / len(compatible)
            for index in range(dimensions)
        ]
        distances = [cosine_distance(embedding, centroid) for embedding in compatible]
        average_distance = sum(distances) / len(distances)
        return max(0.0, min(1.0, 1.0 - average_distance / 2.0))


def marginal_novelty_gain(
    visited_ids: Collection[object],
    candidate_items: list[KnowledgeItem],
    semantic_difference: float,
) -> float:
    if not candidate_items:
        return 0.0
    new_nodes = sum(item.id not in visited_ids for item in candidate_items)
    new_node_ratio = new_nodes / len(candidate_items)
    uniqueness = len({item.id for item in candidate_items}) / len(candidate_items)
    return max(
        0.0,
        min(1.0, 0.45 * new_node_ratio + 0.25 * uniqueness + 0.30 * semantic_difference),
    )
