from __future__ import annotations

import hashlib
import math
from typing import Protocol

from wandermind.cognitive.text import significant_tokens


class EmbeddingAdapter(Protocol):
    dimensions: int

    async def embed_text(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbeddingAdapter:
    def __init__(self, dimensions: int = 96) -> None:
        if dimensions < 8:
            raise ValueError("embedding dimensions must be at least 8")
        self.dimensions = dimensions

    async def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("cannot embed empty text")
        vector = [0.0] * self.dimensions
        for token in significant_tokens(text) or [text.casefold()]:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = -1.0 if digest[8] & 1 else 1.0
            weight = 1.0 + (digest[9] / 255.0)
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(text) for text in texts]


MockEmbeddingAdapter = HashEmbeddingAdapter


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions do not match")
    if not left:
        raise ValueError("embeddings cannot be empty")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def cosine_distance(left: list[float], right: list[float]) -> float:
    return 1.0 - cosine_similarity(left, right)
