from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from wandermind.cognitive.engine import WanderEngine
from wandermind.infrastructure.observability import record_wander_run
from wandermind.models import CognitiveState, Seed, SessionStatus, WanderBudget, WanderSession
from wandermind.repositories.protocols import RepositoryBundle

logger = logging.getLogger(__name__)


class WanderCoordinator:
    def __init__(
        self,
        repositories: RepositoryBundle,
        engine: WanderEngine,
        *,
        max_concurrent_runs: int = 2,
    ) -> None:
        self.repositories = repositories
        self.engine = engine
        self._tasks: dict[UUID, asyncio.Task[None]] = {}
        self._slots = asyncio.Semaphore(max_concurrent_runs)
        self._shutting_down = False

    async def recover(self) -> None:
        sessions = await self.repositories.sessions.list(offset=0, limit=10_000)
        for session in sessions:
            if session.status in {SessionStatus.PENDING, SessionStatus.RUNNING}:
                session.metadata["recovered_after_restart"] = True
                await self.repositories.sessions.update(session)
                self.submit(session.id)

    async def create(
        self,
        seed: Seed,
        budget: WanderBudget,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> WanderSession:
        session = await self.engine.create_session(seed, budget, metadata=metadata)
        self.submit(session.id)
        return session

    def submit(self, session_id: UUID) -> None:
        existing = self._tasks.get(session_id)
        if existing is not None and not existing.done():
            return
        task = asyncio.create_task(
            self._execute(session_id),
            name=f"wander-{session_id}",
        )
        self._tasks[session_id] = task
        task.add_done_callback(lambda completed: self._discard(session_id, completed))

    async def stop(self, session_id: UUID) -> WanderSession | None:
        session = await self.repositories.sessions.get(session_id)
        if session is None:
            return None
        if session.status not in {SessionStatus.PENDING, SessionStatus.RUNNING}:
            return session
        session.metadata["cancel_requested"] = True
        await self.repositories.sessions.update(session)
        task = self._tasks.get(session_id)
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        return await self._mark_stopped(session_id)

    async def shutdown(self) -> None:
        self._shutting_down = True
        active = [task for task in self._tasks.values() if not task.done()]
        for task in active:
            task.cancel()
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        self._tasks.clear()

    def is_active(self, session_id: UUID) -> bool:
        task = self._tasks.get(session_id)
        return task is not None and not task.done()

    async def _execute(self, session_id: UUID) -> None:
        try:
            async with self._slots:
                session = await self.repositories.sessions.get(session_id)
                if session is None or session.status in {
                    SessionStatus.COMPLETED,
                    SessionStatus.STOPPED,
                    SessionStatus.FAILED,
                }:
                    return
                seed = await self.repositories.seeds.get(session.seed_id)
                if seed is None:
                    await self._mark_failed(session, "seed_not_found")
                    return
                result = await self.engine.run(seed, session=session)
                record_wander_run(result.session, result.candidates, result.wonders)
        except asyncio.CancelledError:
            if not self._shutting_down:
                await self._mark_stopped(session_id)
            raise
        except Exception as error:
            logger.exception("background wander failed", extra={"session_id": str(session_id)})
            try:
                session = await self.repositories.sessions.get(session_id)
                if session is not None and session.status in {
                    SessionStatus.PENDING,
                    SessionStatus.RUNNING,
                }:
                    await self._mark_failed(session, type(error).__name__)
            except Exception:
                logger.exception(
                    "could not persist background wander failure",
                    extra={"session_id": str(session_id)},
                )

    async def _mark_stopped(self, session_id: UUID) -> WanderSession | None:
        session = await self.repositories.sessions.get(session_id)
        if session is None:
            return None
        if session.status in {SessionStatus.COMPLETED, SessionStatus.FAILED}:
            return session
        session.ended_at = datetime.now(UTC)
        session.state = CognitiveState.STOPPED
        session.status = SessionStatus.STOPPED
        session.trace.stop_reason = "manual_stop"
        session.metadata["cancel_requested"] = True
        return await self.repositories.sessions.update(session)

    async def _mark_failed(self, session: WanderSession, reason: str) -> None:
        session.ended_at = datetime.now(UTC)
        session.state = CognitiveState.FAILED
        session.status = SessionStatus.FAILED
        session.trace.stop_reason = f"failure:{reason}"
        await self.repositories.sessions.update(session)

    def _discard(self, session_id: UUID, task: asyncio.Task[None]) -> None:
        if self._tasks.get(session_id) is task:
            self._tasks.pop(session_id, None)
