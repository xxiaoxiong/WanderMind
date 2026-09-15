from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import JSON, event
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator, TypeEngine


class Base(DeclarativeBase):
    pass


class EmbeddingType(TypeDecorator[list[float]]):
    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[object]:
        if getattr(dialect, "name", None) == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(JSON())


def create_engine(database_url: str) -> AsyncEngine:
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if database_url in {"sqlite+aiosqlite://", "sqlite+aiosqlite:///:memory:"}:
        kwargs.update({"poolclass": StaticPool, "connect_args": {"check_same_thread": False}})
    engine = create_async_engine(database_url, **kwargs)
    if database_url.startswith("sqlite+"):
        event.listen(engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(dbapi_connection: Any, connection_record: object) -> None:
    del connection_record
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def create_schema(engine: AsyncEngine) -> None:
    from wandermind.infrastructure import orm

    del orm
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def drop_schema(engine: AsyncEngine) -> None:
    from wandermind.infrastructure import orm

    del orm
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
