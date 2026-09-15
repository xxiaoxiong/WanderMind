from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Protocol

from wandermind.cognitive.embedding import EmbeddingAdapter, cosine_similarity
from wandermind.cognitive.errors import EmbeddingError
from wandermind.cognitive.text import (
    jaccard_similarity,
    normalize_text,
    summarize_text,
    top_keywords,
)
from wandermind.models import KnowledgeItem, KnowledgeType
from wandermind.repositories.protocols import KnowledgeRepository

ENTITY_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9_-]{2,}\b|[\u4e00-\u9fff]{2,8}")


class DuplicateKnowledgeError(ValueError):
    def __init__(self, existing_id: str, reason: str) -> None:
        super().__init__(f"duplicate knowledge: {reason} ({existing_id})")
        self.existing_id = existing_id
        self.reason = reason


class DocumentLoader(Protocol):
    async def load(self, source: str) -> str: ...


@dataclass(slots=True)
class TextDocumentLoader:
    content: str

    async def load(self, source: str) -> str:
        del source
        return self.content


class IngestionService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        embedding: EmbeddingAdapter,
        *,
        semantic_duplicate_threshold: float = 0.94,
    ) -> None:
        self.repository = repository
        self.embedding = embedding
        self.semantic_duplicate_threshold = semantic_duplicate_threshold

    async def ingest_text(
        self,
        content: str,
        *,
        title: str | None = None,
        item_type: KnowledgeType = KnowledgeType.NOTE,
        source: str = "manual",
        source_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeItem:
        normalized = normalize_text(content)
        if not normalized:
            raise ValueError("knowledge content cannot be empty")
        resolved_title = normalize_text(title or "") or summarize_text(normalized, max_chars=80)
        normalized_hash = hashlib.sha256(normalized.casefold().encode("utf-8")).hexdigest()
        try:
            embedding = await self.embedding.embed_text(f"{resolved_title}. {normalized}")
        except Exception as error:
            raise EmbeddingError("knowledge embedding failed") from error
        existing_items = await self.repository.list(offset=0, limit=10_000)
        for existing in existing_items:
            if existing.metadata.get("normalized_hash") == normalized_hash:
                raise DuplicateKnowledgeError(str(existing.id), "normalized_hash")
            semantic_similarity = (
                cosine_similarity(existing.embedding, embedding) if existing.embedding else 0.0
            )
            lexical_similarity = jaccard_similarity(existing.content, normalized)
            if (
                semantic_similarity >= self.semantic_duplicate_threshold
                and lexical_similarity >= 0.72
            ):
                raise DuplicateKnowledgeError(str(existing.id), "semantic_similarity")
        topics = top_keywords(normalized, limit=8)
        entities = list(dict.fromkeys(ENTITY_PATTERN.findall(normalized)))[:20]
        item = KnowledgeItem(
            type=item_type,
            title=resolved_title,
            content=normalized,
            summary=summarize_text(normalized),
            source=source,
            source_ref=source_ref,
            topics=topics,
            entities=entities,
            embedding=embedding,
            metadata={**(metadata or {}), "normalized_hash": normalized_hash},
        )
        return await self.repository.create(item)

    async def ingest_document(
        self,
        loader: DocumentLoader,
        source: str,
        *,
        title: str | None = None,
    ) -> KnowledgeItem:
        content = await loader.load(source)
        return await self.ingest_text(
            content,
            title=title,
            item_type=KnowledgeType.DOCUMENT,
            source="document",
            source_ref=source,
        )
