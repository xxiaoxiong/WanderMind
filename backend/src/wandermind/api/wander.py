from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sse_starlette.sse import EventSourceResponse

from wandermind.api.dependencies import get_container
from wandermind.api.schemas import WanderCreate, WanderRunResponse
from wandermind.application.container import ApplicationContainer
from wandermind.application.runtime_summary import summarize_runtime
from wandermind.cognitive.seed_selector import SeedSelector
from wandermind.infrastructure.errors import InsufficientKnowledgeError, NotFoundError
from wandermind.infrastructure.observability import record_wander_run
from wandermind.infrastructure.security import validate_safe_text
from wandermind.models import CognitiveState, Seed, SeedSource, SessionStatus, WanderSession

router = APIRouter(prefix="/wander", tags=["wander"])
Container = Annotated[ApplicationContainer, Depends(get_container)]
MINIMUM_KNOWLEDGE_ITEMS = 2


@router.post("", response_model=WanderRunResponse)
async def run_wander(payload: WanderCreate, container: Container) -> WanderRunResponse:
    await _require_sufficient_knowledge(container)
    seed = await _resolve_seed(payload, container)
    result = await container.wander_engine.run(seed, payload.budget)
    record_wander_run(result.session, result.candidates, result.wonders)
    runtime_sessions = await container.repositories.runtime_sessions.list_for_wander(
        result.session.id
    )
    return WanderRunResponse(
        session=result.session,
        candidates=result.candidates,
        wonders=result.wonders,
        runtime=summarize_runtime(container.settings.runtime_adapter, runtime_sessions),
    )


@router.get("/{session_id}", response_model=WanderSession)
async def get_wander_session(session_id: UUID, container: Container) -> WanderSession:
    session = await container.repositories.sessions.get(session_id)
    if session is None:
        raise NotFoundError("wander session not found", details={"id": str(session_id)})
    return session


@router.get("/{session_id}/stream")
async def stream_wander_session(session_id: UUID, container: Container) -> EventSourceResponse:
    session = await container.repositories.sessions.get(session_id)
    if session is None:
        raise NotFoundError("wander session not found", details={"id": str(session_id)})

    async def events() -> AsyncIterator[dict[str, str]]:
        for step in session.trace.steps:
            current_patch = None
            if session.trace.patches:
                patch_index = min(step.index, len(session.trace.patches) - 1)
                current_patch = str(session.trace.patches[patch_index])
            payload = step.model_dump(mode="json")
            payload.update(
                {
                    "current_patch": current_patch,
                    "patch_count": len(session.trace.patches),
                    "candidate_count": len(session.trace.candidate_ids),
                    "status": session.status.value,
                }
            )
            yield {
                "event": "wander_step",
                "id": str(step.index),
                "data": json.dumps(payload, ensure_ascii=False),
            }
        yield {
            "event": "completed",
            "data": json.dumps(
                {
                    "status": session.status.value,
                    "stop_reason": session.trace.stop_reason,
                    "wonder_ids": [str(value) for value in session.trace.final_wonder_ids],
                    "patch_ids": [str(value) for value in session.trace.patches],
                    "candidate_count": len(session.trace.candidate_ids),
                },
                ensure_ascii=False,
            ),
        }

    return EventSourceResponse(events())


@router.post("/{session_id}/stop", response_model=WanderSession)
async def stop_wander_session(session_id: UUID, container: Container) -> WanderSession:
    session = await container.repositories.sessions.get(session_id)
    if session is None:
        raise NotFoundError("wander session not found", details={"id": str(session_id)})
    if session.status is SessionStatus.RUNNING:
        session.state = CognitiveState.STOPPED
        session.trace.stop_reason = "manual_stop"
        session.ended_at = datetime.now(UTC)
        session.status = SessionStatus.STOPPED
        await container.repositories.sessions.update(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wander_session(session_id: UUID, container: Container) -> Response:
    if not await container.deletion.delete_session(session_id):
        raise NotFoundError("wander session not found", details={"id": str(session_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _require_sufficient_knowledge(container: ApplicationContainer) -> None:
    items = await container.repositories.knowledge.list(
        offset=0,
        limit=MINIMUM_KNOWLEDGE_ITEMS,
    )
    if len(items) < MINIMUM_KNOWLEDGE_ITEMS:
        raise InsufficientKnowledgeError(
            "at least two knowledge items are required to run a wander",
            details={
                "available_count": len(items),
                "required_count": MINIMUM_KNOWLEDGE_ITEMS,
            },
        )


async def _resolve_seed(payload: WanderCreate, container: ApplicationContainer) -> Seed:
    if payload.seed_id is not None:
        seed = await container.repositories.seeds.get(payload.seed_id)
        if seed is None:
            raise NotFoundError("seed not found", details={"id": str(payload.seed_id)})
        return seed
    if payload.content is not None:
        validate_safe_text(payload.content, max_length=20_000)
        seed = Seed(content=payload.content, priority=1.0)
        return await container.repositories.seeds.create(seed)
    seeds = await container.repositories.seeds.list(offset=0, limit=1_000)
    selected = SeedSelector().select(seeds)
    if selected is not None:
        return selected
    recent = await container.repositories.knowledge.list(offset=0, limit=1)
    if not recent:
        raise NotFoundError("no eligible seed or recent knowledge exists")
    item = recent[0]
    generated = Seed(
        content=(
            f"Explore unresolved connections around recent knowledge: {item.title}. "
            f"{item.summary or item.content[:500]}"
        ),
        source=SeedSource.RECENT,
        priority=0.55,
        source_item_id=item.id,
        metadata={"generated_by": "recent_knowledge_fallback"},
    )
    return await container.repositories.seeds.create(generated)
