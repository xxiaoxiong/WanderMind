from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from wandermind.infrastructure.database import (
    create_engine,
    create_schema,
    create_session_factory,
    drop_schema,
)
from wandermind.models import (
    Candidate,
    Feedback,
    FeedbackAction,
    KnowledgeEdge,
    KnowledgeItem,
    RelationType,
    Seed,
    SessionStatus,
    WanderSession,
    Wonder,
    WonderScores,
    WonderType,
)
from wandermind.repositories import SQLAlchemyRepositoryBundle
from wandermind.runtime import RuntimeSession


@pytest.fixture
async def sql_repositories() -> AsyncIterator[SQLAlchemyRepositoryBundle]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await create_schema(engine)
    repositories = SQLAlchemyRepositoryBundle(create_session_factory(engine))
    yield repositories
    await drop_schema(engine)
    await engine.dispose()


@pytest.mark.asyncio
async def test_sql_knowledge_and_graph_contract(
    sql_repositories: SQLAlchemyRepositoryBundle,
) -> None:
    first = KnowledgeItem(title="First", content="Agent scheduling", metadata={"kind": "demo"})
    second = KnowledgeItem(title="Second", content="Organization governance")
    await sql_repositories.knowledge.create(first)
    await sql_repositories.knowledge.create(second)
    edge = KnowledgeEdge(
        source_id=first.id,
        target_id=second.id,
        relation_type=RelationType.ANALOGY_OF,
    )
    await sql_repositories.graph.create(edge)

    fetched = await sql_repositories.knowledge.get(first.id)
    neighbors = await sql_repositories.graph.list_for_item(first.id)

    assert fetched == first
    assert fetched is not None and fetched.metadata == {"kind": "demo"}
    assert neighbors == [edge]
    assert await sql_repositories.knowledge.search("scheduling") == [first]


@pytest.mark.asyncio
async def test_sql_session_candidate_wonder_feedback_round_trip(
    sql_repositories: SQLAlchemyRepositoryBundle,
) -> None:
    seed = Seed(content="A seed")
    await sql_repositories.seeds.create(seed)
    session = WanderSession(seed_id=seed.id)
    await sql_repositories.sessions.create(session)
    source_ids = [uuid4(), uuid4()]
    candidate = Candidate(
        session_id=session.id,
        candidate_type=WonderType.CONNECTION,
        statement="A connection",
        explanation="An explainable connection",
        seed_id=seed.id,
        source_items=source_ids,
        operator="analogy",
    )
    await sql_repositories.candidates.create(candidate)
    scores = WonderScores(total=0.7, novelty=0.8, coherence=0.8)
    wonder = Wonder(
        session_id=session.id,
        seed_id=seed.id,
        candidate_id=candidate.id,
        type=WonderType.CONNECTION,
        statement=candidate.statement,
        explanation=candidate.explanation,
        why_interesting="It connects two systems.",
        source_items=source_ids,
        scores=scores,
    )
    await sql_repositories.wonders.create(wonder)
    feedback = Feedback(wonder_id=wonder.id, action=FeedbackAction.INTERESTING)
    await sql_repositories.feedback.create(feedback)
    session.ended_at = datetime.now(UTC)
    session.status = SessionStatus.COMPLETED
    await sql_repositories.sessions.update(session)

    assert await sql_repositories.candidates.list_for_session(session.id) == [candidate]
    assert await sql_repositories.wonders.get(wonder.id) == wonder
    assert await sql_repositories.feedback.list_for_wonder(wonder.id) == [feedback]
    stored_session = await sql_repositories.sessions.get(session.id)
    assert stored_session is not None and stored_session.status.value == "completed"

    runtime_session = RuntimeSession(
        provider="mock",
        purpose="critic",
        wander_session_id=session.id,
        cost={"runtime_calls": 1, "duration_seconds": 0.01},
    )
    await sql_repositories.runtime_sessions.create(runtime_session)
    stored_runtime = await sql_repositories.runtime_sessions.get(runtime_session.id)
    assert stored_runtime is not None
    assert stored_runtime.wander_session_id == session.id
    assert stored_runtime.cost["runtime_calls"] == 1

    assert await sql_repositories.sessions.delete(session.id) is True
    assert await sql_repositories.candidates.list_for_session(session.id) == []
    assert await sql_repositories.wonders.get(wonder.id) is None
    assert await sql_repositories.feedback.get(feedback.id) is None
    detached_runtime = await sql_repositories.runtime_sessions.get(runtime_session.id)
    assert detached_runtime is not None and detached_runtime.wander_session_id is None


@pytest.mark.asyncio
async def test_sqlite_database_survives_engine_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "restart.db"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    first_engine = create_engine(database_url)
    await create_schema(first_engine)
    item = KnowledgeItem(title="Persistent", content="Durable knowledge survives restart.")
    first_repositories = SQLAlchemyRepositoryBundle(create_session_factory(first_engine))
    await first_repositories.knowledge.create(item)
    await first_engine.dispose()

    second_engine = create_engine(database_url)
    second_repositories = SQLAlchemyRepositoryBundle(create_session_factory(second_engine))
    restored = await second_repositories.knowledge.get(item.id)
    await second_engine.dispose()

    assert restored == item
