from __future__ import annotations

import builtins
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wandermind.infrastructure.orm import (
    CandidateRow,
    FeedbackRow,
    KnowledgeEdgeRow,
    KnowledgeItemRow,
    RuntimeSessionRow,
    SeedRow,
    WanderSessionRow,
    WanderStepRow,
    WonderRow,
)
from wandermind.models import (
    Candidate,
    Feedback,
    KnowledgeEdge,
    KnowledgeItem,
    Seed,
    WanderSession,
    Wonder,
)
from wandermind.runtime.base import RuntimeSession


class TimestampedEntity(Protocol):
    id: UUID
    created_at: datetime
    updated_at: datetime


class SQLRepository[RowT]:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def _commit(self, session: AsyncSession) -> None:
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class SQLKnowledgeRepository(SQLRepository[KnowledgeItemRow]):
    async def create(self, item: KnowledgeItem) -> KnowledgeItem:
        row = KnowledgeItemRow(**_knowledge_values(item))
        async with self.factory() as session:
            session.add(row)
            await self._commit(session)
        return _knowledge_model(row)

    async def get(self, item_id: UUID) -> KnowledgeItem | None:
        async with self.factory() as session:
            row = await session.get(KnowledgeItemRow, item_id)
            return _knowledge_model(row) if row else None

    async def update(self, item: KnowledgeItem) -> KnowledgeItem:
        async with self.factory() as session:
            row = await session.get(KnowledgeItemRow, item.id)
            if row is None:
                raise KeyError(item.id)
            _assign(row, _knowledge_values(item))
            await self._commit(session)
            return _knowledge_model(row)

    async def delete(self, item_id: UUID) -> bool:
        async with self.factory() as session:
            row = await session.get(KnowledgeItemRow, item_id)
            if row is None:
                return False
            await session.delete(row)
            await self._commit(session)
            return True

    async def list(self, *, offset: int = 0, limit: int = 50) -> builtins.list[KnowledgeItem]:
        statement = (
            select(KnowledgeItemRow)
            .order_by(KnowledgeItemRow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_knowledge_model(row) for row in rows]

    async def search(self, query: str, *, limit: int = 20) -> builtins.list[KnowledgeItem]:
        pattern = f"%{query.strip()}%"
        statement = (
            select(KnowledgeItemRow)
            .where(
                or_(KnowledgeItemRow.title.ilike(pattern), KnowledgeItemRow.content.ilike(pattern))
            )
            .order_by(KnowledgeItemRow.created_at.desc())
            .limit(limit)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_knowledge_model(row) for row in rows]


class SQLGraphRepository(SQLRepository[KnowledgeEdgeRow]):
    async def create(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        row = KnowledgeEdgeRow(**_edge_values(edge))
        async with self.factory() as session:
            session.add(row)
            await self._commit(session)
        return _edge_model(row)

    async def list_for_item(self, item_id: UUID) -> builtins.list[KnowledgeEdge]:
        statement = select(KnowledgeEdgeRow).where(
            or_(KnowledgeEdgeRow.source_id == item_id, KnowledgeEdgeRow.target_id == item_id)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_edge_model(row) for row in rows]

    async def delete(self, edge_id: UUID) -> bool:
        async with self.factory() as session:
            row = await session.get(KnowledgeEdgeRow, edge_id)
            if row is None:
                return False
            await session.delete(row)
            await self._commit(session)
            return True


class SQLSeedRepository(SQLRepository[SeedRow]):
    async def create(self, seed: Seed) -> Seed:
        row = SeedRow(**_seed_values(seed))
        async with self.factory() as session:
            session.add(row)
            await self._commit(session)
        return _seed_model(row)

    async def get(self, seed_id: UUID) -> Seed | None:
        async with self.factory() as session:
            row = await session.get(SeedRow, seed_id)
            return _seed_model(row) if row else None

    async def update(self, seed: Seed) -> Seed:
        async with self.factory() as session:
            row = await session.get(SeedRow, seed.id)
            if row is None:
                raise KeyError(seed.id)
            _assign(row, _seed_values(seed))
            await self._commit(session)
            return _seed_model(row)

    async def list(self, *, offset: int = 0, limit: int = 50) -> builtins.list[Seed]:
        statement = select(SeedRow).order_by(SeedRow.created_at.desc()).offset(offset).limit(limit)
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_seed_model(row) for row in rows]


class SQLCandidateRepository(SQLRepository[CandidateRow]):
    async def create(self, candidate: Candidate) -> Candidate:
        row = CandidateRow(**_candidate_values(candidate))
        async with self.factory() as session:
            session.add(row)
            await self._commit(session)
        return _candidate_model(row)

    async def get(self, candidate_id: UUID) -> Candidate | None:
        async with self.factory() as session:
            row = await session.get(CandidateRow, candidate_id)
            return _candidate_model(row) if row else None

    async def update(self, candidate: Candidate) -> Candidate:
        async with self.factory() as session:
            row = await session.get(CandidateRow, candidate.id)
            if row is None:
                raise KeyError(candidate.id)
            _assign(row, _candidate_values(candidate))
            await self._commit(session)
            return _candidate_model(row)

    async def delete(self, candidate_id: UUID) -> bool:
        async with self.factory() as session:
            row = await session.get(CandidateRow, candidate_id)
            if row is None:
                return False
            await session.delete(row)
            await self._commit(session)
            return True

    async def list(self, *, offset: int = 0, limit: int = 50) -> builtins.list[Candidate]:
        statement = (
            select(CandidateRow)
            .order_by(CandidateRow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_candidate_model(row) for row in rows]

    async def list_for_session(self, session_id: UUID) -> builtins.list[Candidate]:
        statement = (
            select(CandidateRow)
            .where(CandidateRow.session_id == session_id)
            .order_by(CandidateRow.created_at)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_candidate_model(row) for row in rows]


class SQLWonderRepository(SQLRepository[WonderRow]):
    async def create(self, wonder: Wonder) -> Wonder:
        row = WonderRow(**_wonder_values(wonder))
        async with self.factory() as session:
            session.add(row)
            await self._commit(session)
        return _wonder_model(row)

    async def get(self, wonder_id: UUID) -> Wonder | None:
        async with self.factory() as session:
            row = await session.get(WonderRow, wonder_id)
            return _wonder_model(row) if row else None

    async def update(self, wonder: Wonder) -> Wonder:
        async with self.factory() as session:
            row = await session.get(WonderRow, wonder.id)
            if row is None:
                raise KeyError(wonder.id)
            _assign(row, _wonder_values(wonder))
            await self._commit(session)
            return _wonder_model(row)

    async def delete(self, wonder_id: UUID) -> bool:
        async with self.factory() as session:
            row = await session.get(WonderRow, wonder_id)
            if row is None:
                return False
            await session.delete(row)
            await self._commit(session)
            return True

    async def list(self, *, offset: int = 0, limit: int = 50) -> builtins.list[Wonder]:
        statement = (
            select(WonderRow).order_by(WonderRow.created_at.desc()).offset(offset).limit(limit)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_wonder_model(row) for row in rows]

    async def search_similar(self, text: str, *, limit: int = 20) -> builtins.list[Wonder]:
        pattern = f"%{text.strip()}%"
        statement = (
            select(WonderRow)
            .where(or_(WonderRow.statement.ilike(pattern), WonderRow.explanation.ilike(pattern)))
            .order_by(WonderRow.created_at.desc())
            .limit(limit)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_wonder_model(row) for row in rows]


class SQLSessionRepository(SQLRepository[WanderSessionRow]):
    async def create(self, wander_session: WanderSession) -> WanderSession:
        row = WanderSessionRow(**_session_values(wander_session))
        async with self.factory() as session:
            session.add(row)
            await session.flush()
            await _sync_steps(session, wander_session)
            await self._commit(session)
        return _session_model(row)

    async def get(self, session_id: UUID) -> WanderSession | None:
        async with self.factory() as session:
            row = await session.get(WanderSessionRow, session_id)
            return _session_model(row) if row else None

    async def update(self, wander_session: WanderSession) -> WanderSession:
        async with self.factory() as session:
            row = await session.get(WanderSessionRow, wander_session.id)
            if row is None:
                raise KeyError(wander_session.id)
            _assign(row, _session_values(wander_session))
            await _sync_steps(session, wander_session)
            await self._commit(session)
            return _session_model(row)

    async def delete(self, session_id: UUID) -> bool:
        async with self.factory() as session:
            row = await session.get(WanderSessionRow, session_id)
            if row is None:
                return False
            await session.delete(row)
            await self._commit(session)
            return True

    async def list(self, *, offset: int = 0, limit: int = 50) -> builtins.list[WanderSession]:
        statement = (
            select(WanderSessionRow)
            .order_by(WanderSessionRow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_session_model(row) for row in rows]


class SQLFeedbackRepository(SQLRepository[FeedbackRow]):
    async def create(self, feedback: Feedback) -> Feedback:
        row = FeedbackRow(**_feedback_values(feedback))
        async with self.factory() as session:
            session.add(row)
            await self._commit(session)
        return _feedback_model(row)

    async def get(self, feedback_id: UUID) -> Feedback | None:
        async with self.factory() as session:
            row = await session.get(FeedbackRow, feedback_id)
            return _feedback_model(row) if row else None

    async def delete(self, feedback_id: UUID) -> bool:
        async with self.factory() as session:
            row = await session.get(FeedbackRow, feedback_id)
            if row is None:
                return False
            await session.delete(row)
            await self._commit(session)
            return True

    async def list_for_wonder(self, wonder_id: UUID) -> builtins.list[Feedback]:
        statement = (
            select(FeedbackRow)
            .where(FeedbackRow.wonder_id == wonder_id)
            .order_by(FeedbackRow.created_at)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_feedback_model(row) for row in rows]


class SQLRuntimeSessionRepository(SQLRepository[RuntimeSessionRow]):
    async def create(self, runtime_session: RuntimeSession) -> RuntimeSession:
        row = RuntimeSessionRow(**_runtime_session_values(runtime_session))
        async with self.factory() as session:
            session.add(row)
            await self._commit(session)
        return _runtime_session_model(row)

    async def get(self, session_id: UUID) -> RuntimeSession | None:
        async with self.factory() as session:
            row = await session.get(RuntimeSessionRow, session_id)
            return _runtime_session_model(row) if row else None

    async def update(self, runtime_session: RuntimeSession) -> RuntimeSession:
        async with self.factory() as session:
            row = await session.get(RuntimeSessionRow, runtime_session.id)
            if row is None:
                raise KeyError(runtime_session.id)
            _assign(row, _runtime_session_values(runtime_session))
            await self._commit(session)
            return _runtime_session_model(row)

    async def list(self, *, offset: int = 0, limit: int = 50) -> builtins.list[RuntimeSession]:
        statement = (
            select(RuntimeSessionRow)
            .order_by(RuntimeSessionRow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        async with self.factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_runtime_session_model(row) for row in rows]


@dataclass(slots=True)
class SQLAlchemyRepositoryBundle:
    factory: async_sessionmaker[AsyncSession]
    knowledge: SQLKnowledgeRepository = field(init=False)
    graph: SQLGraphRepository = field(init=False)
    seeds: SQLSeedRepository = field(init=False)
    candidates: SQLCandidateRepository = field(init=False)
    wonders: SQLWonderRepository = field(init=False)
    sessions: SQLSessionRepository = field(init=False)
    feedback: SQLFeedbackRepository = field(init=False)
    runtime_sessions: SQLRuntimeSessionRepository = field(init=False)

    def __post_init__(self) -> None:
        self.knowledge = SQLKnowledgeRepository(self.factory)
        self.graph = SQLGraphRepository(self.factory)
        self.seeds = SQLSeedRepository(self.factory)
        self.candidates = SQLCandidateRepository(self.factory)
        self.wonders = SQLWonderRepository(self.factory)
        self.sessions = SQLSessionRepository(self.factory)
        self.feedback = SQLFeedbackRepository(self.factory)
        self.runtime_sessions = SQLRuntimeSessionRepository(self.factory)


async def _sync_steps(session: AsyncSession, wander_session: WanderSession) -> None:
    await session.execute(
        delete(WanderStepRow).where(WanderStepRow.session_id == wander_session.id)
    )
    session.add_all(
        [
            WanderStepRow(
                id=step.id,
                session_id=wander_session.id,
                step_index=step.index,
                state=step.state.value,
                action=step.action,
                payload=step.model_dump(mode="json"),
                created_at=step.created_at,
                updated_at=step.created_at,
            )
            for step in wander_session.trace.steps
        ]
    )


def _assign(row: object, values: dict[str, Any]) -> None:
    for name, value in values.items():
        setattr(row, name, value)


def _base_values(model: TimestampedEntity) -> dict[str, Any]:
    return {
        "id": model.id,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _knowledge_values(item: KnowledgeItem) -> dict[str, Any]:
    return {
        **_base_values(item),
        "type": item.type.value,
        "title": item.title,
        "content": item.content,
        "summary": item.summary,
        "source": item.source,
        "source_ref": item.source_ref,
        "topics": item.topics,
        "entities": item.entities,
        "embedding": item.embedding,
        "importance": item.importance,
        "confidence": item.confidence,
        "status": item.status.value,
        "event_time": item.event_time,
        "item_metadata": item.metadata,
    }


def _knowledge_model(row: KnowledgeItemRow) -> KnowledgeItem:
    return KnowledgeItem(
        id=row.id,
        type=row.type,
        title=row.title,
        content=row.content,
        summary=row.summary,
        source=row.source,
        source_ref=row.source_ref,
        topics=row.topics,
        entities=row.entities,
        embedding=row.embedding,
        importance=row.importance,
        confidence=row.confidence,
        status=row.status,
        event_time=_as_utc(row.event_time),
        metadata=row.item_metadata,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


def _edge_values(edge: KnowledgeEdge) -> dict[str, Any]:
    return {
        **_base_values(edge),
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "relation_type": edge.relation_type.value,
        "weight": edge.weight,
        "confidence": edge.confidence,
        "created_by": edge.created_by,
        "edge_metadata": edge.metadata,
    }


def _edge_model(row: KnowledgeEdgeRow) -> KnowledgeEdge:
    return KnowledgeEdge(
        id=row.id,
        source_id=row.source_id,
        target_id=row.target_id,
        relation_type=row.relation_type,
        weight=row.weight,
        confidence=row.confidence,
        created_by=row.created_by,
        metadata=row.edge_metadata,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


def _seed_values(seed: Seed) -> dict[str, Any]:
    return {
        **_base_values(seed),
        "content": seed.content,
        "source": seed.source.value,
        "priority": seed.priority,
        "status": seed.status.value,
        "source_item_id": seed.source_item_id,
        "last_used_at": seed.last_used_at,
        "seed_metadata": seed.metadata,
    }


def _seed_model(row: SeedRow) -> Seed:
    return Seed(
        id=row.id,
        content=row.content,
        source=row.source,
        priority=row.priority,
        status=row.status,
        source_item_id=row.source_item_id,
        last_used_at=_as_utc(row.last_used_at),
        metadata=row.seed_metadata,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


def _candidate_values(candidate: Candidate) -> dict[str, Any]:
    return {
        **_base_values(candidate),
        "session_id": candidate.session_id,
        "seed_id": candidate.seed_id,
        "candidate_type": candidate.candidate_type.value,
        "statement": candidate.statement,
        "explanation": candidate.explanation,
        "source_items": [str(value) for value in candidate.source_items],
        "operator": candidate.operator,
        "wander_path": [str(value) for value in candidate.wander_path],
        "scores": candidate.scores.model_dump(mode="json") if candidate.scores else None,
        "status": candidate.status.value,
        "candidate_metadata": candidate.metadata,
    }


def _candidate_model(row: CandidateRow) -> Candidate:
    return Candidate(
        id=row.id,
        session_id=row.session_id,
        seed_id=row.seed_id,
        candidate_type=row.candidate_type,
        statement=row.statement,
        explanation=row.explanation,
        source_items=row.source_items,
        operator=row.operator,
        wander_path=row.wander_path,
        scores=row.scores,
        status=row.status,
        metadata=row.candidate_metadata,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


def _wonder_values(wonder: Wonder) -> dict[str, Any]:
    return {
        **_base_values(wonder),
        "session_id": wonder.session_id,
        "seed_id": wonder.seed_id,
        "candidate_id": wonder.candidate_id,
        "type": wonder.type.value,
        "statement": wonder.statement,
        "explanation": wonder.explanation,
        "why_interesting": wonder.why_interesting,
        "source_items": [str(value) for value in wonder.source_items],
        "connection_path": [str(value) for value in wonder.connection_path],
        "supporting_evidence": wonder.supporting_evidence,
        "counter_evidence": wonder.counter_evidence,
        "assumptions": wonder.assumptions,
        "questions": wonder.questions,
        "scores": wonder.scores.model_dump(mode="json"),
        "confidence": wonder.confidence,
        "status": wonder.status.value,
        "parent_wonder_id": wonder.parent_wonder_id,
        "wonder_metadata": wonder.metadata,
    }


def _wonder_model(row: WonderRow) -> Wonder:
    return Wonder(
        id=row.id,
        session_id=row.session_id,
        seed_id=row.seed_id,
        candidate_id=row.candidate_id,
        type=row.type,
        statement=row.statement,
        explanation=row.explanation,
        why_interesting=row.why_interesting,
        source_items=row.source_items,
        connection_path=row.connection_path,
        supporting_evidence=row.supporting_evidence,
        counter_evidence=row.counter_evidence,
        assumptions=row.assumptions,
        questions=row.questions,
        scores=row.scores,
        confidence=row.confidence,
        status=row.status,
        parent_wonder_id=row.parent_wonder_id,
        metadata=row.wonder_metadata,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


def _session_values(wander_session: WanderSession) -> dict[str, Any]:
    return {
        **_base_values(wander_session),
        "seed_id": wander_session.seed_id,
        "state": wander_session.state.value,
        "budget": wander_session.budget.model_dump(mode="json"),
        "status": wander_session.status.value,
        "trace": wander_session.trace.model_dump(mode="json"),
        "started_at": wander_session.started_at,
        "ended_at": wander_session.ended_at,
        "session_metadata": wander_session.metadata,
    }


def _session_model(row: WanderSessionRow) -> WanderSession:
    return WanderSession(
        id=row.id,
        seed_id=row.seed_id,
        state=row.state,
        budget=row.budget,
        status=row.status,
        trace=row.trace,
        started_at=_as_utc(row.started_at),
        ended_at=_as_utc(row.ended_at),
        metadata=row.session_metadata,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


def _feedback_values(feedback: Feedback) -> dict[str, Any]:
    return {
        **_base_values(feedback),
        "wonder_id": feedback.wonder_id,
        "action": feedback.action.value,
        "value": feedback.value,
        "note": feedback.note,
        "feedback_metadata": feedback.metadata,
    }


def _feedback_model(row: FeedbackRow) -> Feedback:
    return Feedback(
        id=row.id,
        wonder_id=row.wonder_id,
        action=row.action,
        value=row.value,
        note=row.note,
        metadata=row.feedback_metadata,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


def _runtime_session_values(runtime_session: RuntimeSession) -> dict[str, Any]:
    return {
        **_base_values(runtime_session),
        "wander_session_id": runtime_session.wander_session_id,
        "runtime": runtime_session.provider,
        "purpose": runtime_session.purpose,
        "external_session_id": runtime_session.external_session_id,
        "status": runtime_session.status.value,
        "last_used_at": runtime_session.last_used_at,
        "cost": runtime_session.cost,
        "runtime_metadata": runtime_session.metadata,
    }


def _runtime_session_model(row: RuntimeSessionRow) -> RuntimeSession:
    return RuntimeSession(
        id=row.id,
        provider=row.runtime,
        purpose=row.purpose,
        external_session_id=row.external_session_id,
        status=row.status,
        wander_session_id=row.wander_session_id,
        last_used_at=_as_utc(row.last_used_at),
        cost=row.cost,
        metadata=row.runtime_metadata,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
