from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse

from wandermind.api.dependencies import get_container
from wandermind.api.schemas import WanderCreate, WanderRunResponse
from wandermind.application.container import ApplicationContainer
from wandermind.application.runtime_summary import summarize_runtime
from wandermind.cognitive.seed_selector import SeedSelector
from wandermind.infrastructure.errors import InsufficientKnowledgeError, NotFoundError
from wandermind.infrastructure.observability import record_wander_run
from wandermind.infrastructure.security import validate_safe_text
from wandermind.models import Seed, SeedSource, SessionStatus, WanderSession

router = APIRouter(prefix="/wander", tags=["wander"])
Container = Annotated[ApplicationContainer, Depends(get_container)]
MINIMUM_KNOWLEDGE_ITEMS = 2


@router.post("", response_model=WanderRunResponse)
async def run_wander(payload: WanderCreate, container: Container) -> WanderRunResponse:
    await _require_sufficient_knowledge(container)
    seed = await _resolve_seed(payload, container)
    result = await container.wander_engine.run(seed, payload.budget)
    record_wander_run(result.session, result.candidates, result.wonders)
    return await _run_response(result.session.id, container)


@router.post("/start", response_model=WanderSession, status_code=status.HTTP_202_ACCEPTED)
async def start_wander(payload: WanderCreate, container: Container) -> WanderSession:
    await _require_sufficient_knowledge(container)
    seed = await _resolve_seed(payload, container)
    return await container.wander_coordinator.create(seed, payload.budget)


@router.get("/{session_id}", response_model=WanderSession)
async def get_wander_session(session_id: UUID, container: Container) -> WanderSession:
    session = await container.repositories.sessions.get(session_id)
    if session is None:
        raise NotFoundError("wander session not found", details={"id": str(session_id)})
    return session


@router.get("/{session_id}/result", response_model=WanderRunResponse)
async def get_wander_result(session_id: UUID, container: Container) -> WanderRunResponse:
    return await _run_response(session_id, container)


@router.get("/{session_id}/stream")
async def stream_wander_session(
    session_id: UUID,
    request: Request,
    container: Container,
    after: int = -1,
) -> StreamingResponse:
    session = await container.repositories.sessions.get(session_id)
    if session is None:
        raise NotFoundError("wander session not found", details={"id": str(session_id)})

    async def events() -> AsyncIterator[dict[str, str]]:
        next_index = max(after + 1, 0)
        last_progress: tuple[str, str, int, int, int] | None = None
        heartbeat_ticks = 0
        terminal = {SessionStatus.COMPLETED, SessionStatus.STOPPED, SessionStatus.FAILED}
        while True:
            current = await container.repositories.sessions.get(session_id)
            if current is None:
                return
            for step in current.trace.steps[next_index:]:
                current_patch = None
                if current.trace.patches:
                    patch_index = min(step.index, len(current.trace.patches) - 1)
                    current_patch = str(current.trace.patches[patch_index])
                payload = step.model_dump(mode="json")
                payload.update(
                    {
                        "current_patch": current_patch,
                        "patch_count": len(current.trace.patches),
                        "candidate_count": len(current.trace.candidate_ids),
                        "wonder_count": len(current.trace.final_wonder_ids),
                        "status": current.status.value,
                    }
                )
                yield {
                    "event": "wander_step",
                    "id": str(step.index),
                    "data": json.dumps(payload, ensure_ascii=False),
                }
                next_index = step.index + 1
            progress = (
                current.status.value,
                current.state.value,
                len(current.trace.candidate_ids),
                len(current.trace.final_wonder_ids),
                int(current.metadata.get("runtime_calls_used", 0)),
            )
            if progress != last_progress:
                yield {
                    "event": "progress",
                    "data": json.dumps(
                        {
                            "status": current.status.value,
                            "state": current.state.value,
                            "candidate_count": progress[2],
                            "wonder_count": progress[3],
                            "runtime_calls_used": progress[4],
                        },
                        ensure_ascii=False,
                    ),
                }
                last_progress = progress
                heartbeat_ticks = 0
            if current.status in terminal:
                yield {
                    "event": "completed",
                    "data": json.dumps(
                        {
                            "status": current.status.value,
                            "stop_reason": current.trace.stop_reason,
                            "wonder_ids": [str(value) for value in current.trace.final_wonder_ids],
                            "patch_ids": [str(value) for value in current.trace.patches],
                            "candidate_count": len(current.trace.candidate_ids),
                        },
                        ensure_ascii=False,
                    ),
                }
                return
            if await request.is_disconnected():
                return
            heartbeat_ticks += 1
            if heartbeat_ticks >= 20:
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"status": current.status.value}),
                }
                heartbeat_ticks = 0
            await asyncio.sleep(0.25)

    async def encoded_events() -> AsyncIterator[str]:
        async for event in events():
            lines = [f"event: {event['event']}"]
            if event_id := event.get("id"):
                lines.append(f"id: {event_id}")
            lines.append(f"data: {event['data']}")
            yield "\n".join(lines) + "\n\n"

    return StreamingResponse(
        encoded_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/stop", response_model=WanderSession)
async def stop_wander_session(session_id: UUID, container: Container) -> WanderSession:
    session = await container.wander_coordinator.stop(session_id)
    if session is None:
        raise NotFoundError("wander session not found", details={"id": str(session_id)})
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wander_session(session_id: UUID, container: Container) -> Response:
    await container.wander_coordinator.stop(session_id)
    if not await container.deletion.delete_session(session_id):
        raise NotFoundError("wander session not found", details={"id": str(session_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _run_response(
    session_id: UUID,
    container: ApplicationContainer,
) -> WanderRunResponse:
    session = await container.repositories.sessions.get(session_id)
    if session is None:
        raise NotFoundError("wander session not found", details={"id": str(session_id)})
    candidates = await container.repositories.candidates.list_for_session(session_id)
    wonders = [
        wonder
        for wonder in await container.repositories.wonders.list(offset=0, limit=10_000)
        if wonder.session_id == session_id
    ]
    wonders.sort(key=lambda wonder: (wonder.scores.total, wonder.confidence), reverse=True)
    runtime_sessions = await container.repositories.runtime_sessions.list_for_wander(session_id)
    return WanderRunResponse(
        session=session,
        candidates=candidates,
        wonders=wonders,
        runtime=summarize_runtime(container.settings.runtime_adapter, runtime_sessions),
    )


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
