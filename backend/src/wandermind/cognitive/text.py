from __future__ import annotations

import re
import unicodedata
from collections import Counter

TOKEN_PATTERN = re.compile(r"[\w\u3400-\u9fff]+", re.UNICODE)
SENTENCE_PATTERN = re.compile(r"(?<=[。！？.!?])\s+")  # noqa: RUF001
STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "for",
    "from",
    "have",
    "into",
    "that",
    "the",
    "this",
    "with",
    "一个",
    "以及",
    "可以",
    "如何",
    "如果",
    "我们",
    "这个",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return " ".join(normalized.split()).strip()


def tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_PATTERN.finditer(normalize_text(text))]


def significant_tokens(text: str) -> list[str]:
    return [token for token in tokens(text) if len(token) > 1 and token not in STOPWORDS]


def top_keywords(text: str, *, limit: int = 8) -> list[str]:
    counts = Counter(significant_tokens(text))
    return [token for token, _ in counts.most_common(limit)]


def summarize_text(text: str, *, max_chars: int = 280) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    sentences = SENTENCE_PATTERN.split(normalized)
    summary = ""
    for sentence in sentences:
        candidate = f"{summary} {sentence}".strip()
        if len(candidate) > max_chars:
            break
        summary = candidate
    return summary or normalized[: max_chars - 1].rstrip() + "…"


def jaccard_similarity(left: str, right: str) -> float:
    left_tokens = set(significant_tokens(left))
    right_tokens = set(significant_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
