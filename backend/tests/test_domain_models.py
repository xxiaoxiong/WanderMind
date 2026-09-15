from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from wandermind.infrastructure.config import Settings
from wandermind.models import (
    KnowledgeEdge,
    KnowledgeItem,
    RelationType,
    Seed,
    SessionStatus,
    WanderSession,
    WonderScores,
)


@pytest.mark.parametrize("scheme", ["postgresql", "postgres"])
def test_settings_normalizes_hosted_postgres_urls(scheme: str) -> None:
    settings = Settings(database_url=f"{scheme}://user:password@database.example/wandermind")

    assert settings.database_url == (
        "postgresql+asyncpg://user:password@database.example/wandermind"
    )


def test_knowledge_item_serialization_and_label_normalization() -> None:
    item = KnowledgeItem(
        title="Semantic foraging",
        content="Local exploration alternates with patch switching.",
        topics=[" cognition ", "cognition", "creativity"],
        confidence=1.0,
    )

    payload = item.model_dump(mode="json")

    assert payload["type"] == "note"
    assert item.topics == ["cognition", "creativity"]
    assert payload["confidence"] == 1.0


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_knowledge_item_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        KnowledgeItem(title="Invalid", content="Invalid confidence", confidence=confidence)


def test_knowledge_edge_rejects_self_loop() -> None:
    item_id = uuid4()
    with pytest.raises(ValidationError, match="self-loop"):
        KnowledgeEdge(
            source_id=item_id,
            target_id=item_id,
            relation_type=RelationType.SIMILAR_TO,
        )


def test_seed_rejects_empty_content() -> None:
    with pytest.raises(ValidationError):
        Seed(content="")


def test_terminal_session_requires_end_time() -> None:
    with pytest.raises(ValidationError, match="ended_at"):
        WanderSession(seed_id=uuid4(), status=SessionStatus.COMPLETED)

    completed = WanderSession(
        seed_id=uuid4(),
        status=SessionStatus.COMPLETED,
        ended_at=datetime.now(UTC),
    )
    assert completed.status is SessionStatus.COMPLETED


def test_wonder_scores_enforce_normalized_range() -> None:
    with pytest.raises(ValidationError):
        WonderScores(novelty=1.2)
