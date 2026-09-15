from __future__ import annotations

from uuid import UUID

from wandermind.repositories.protocols import RepositoryBundle


class DataDeletionService:
    def __init__(self, repositories: RepositoryBundle) -> None:
        self.repositories = repositories

    async def delete_knowledge(self, item_id: UUID) -> bool:
        item = await self.repositories.knowledge.get(item_id)
        if item is None:
            return False
        for edge in await self.repositories.graph.list_for_item(item_id):
            await self.repositories.graph.delete(edge.id)
        for seed in await self.repositories.seeds.list(offset=0, limit=10_000):
            if seed.source_item_id == item_id:
                seed.source_item_id = None
                await self.repositories.seeds.update(seed)
        return await self.repositories.knowledge.delete(item_id)

    async def delete_wonder(self, wonder_id: UUID) -> bool:
        wonder = await self.repositories.wonders.get(wonder_id)
        if wonder is None:
            return False
        for feedback in await self.repositories.feedback.list_for_wonder(wonder_id):
            await self.repositories.feedback.delete(feedback.id)
        for child in await self.repositories.wonders.list(offset=0, limit=10_000):
            if child.parent_wonder_id == wonder_id:
                child.parent_wonder_id = None
                await self.repositories.wonders.update(child)
        return await self.repositories.wonders.delete(wonder_id)

    async def delete_feedback(self, wonder_id: UUID, feedback_id: UUID) -> bool:
        feedback = await self.repositories.feedback.get(feedback_id)
        if feedback is None or feedback.wonder_id != wonder_id:
            return False
        return await self.repositories.feedback.delete(feedback_id)

    async def delete_session(self, session_id: UUID) -> bool:
        session = await self.repositories.sessions.get(session_id)
        if session is None:
            return False
        wonders = await self.repositories.wonders.list(offset=0, limit=10_000)
        for wonder in wonders:
            if wonder.session_id == session_id:
                await self.delete_wonder(wonder.id)
        for candidate in await self.repositories.candidates.list(offset=0, limit=10_000):
            if candidate.session_id == session_id:
                await self.repositories.candidates.delete(candidate.id)
        for runtime_session in await self.repositories.runtime_sessions.list(
            offset=0,
            limit=10_000,
        ):
            if runtime_session.wander_session_id == session_id:
                runtime_session.wander_session_id = None
                await self.repositories.runtime_sessions.update(runtime_session)
        return await self.repositories.sessions.delete(session_id)
