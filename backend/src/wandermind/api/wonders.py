from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from wandermind.api.dependencies import get_container
from wandermind.api.schemas import DeepExploreResponse, FeedbackCreate
from wandermind.application.container import ApplicationContainer
from wandermind.application.evaluation import CriticVerdict
from wandermind.infrastructure.errors import ConflictError, NotFoundError
from wandermind.infrastructure.security import validate_safe_metadata, validate_safe_text
from wandermind.models import Feedback, Wonder

router = APIRouter(prefix="/wonders", tags=["wonders"])
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.get("", response_model=list[Wonder])
async def list_wonders(
    container: Container,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Wonder]:
    return await container.repositories.wonders.list(offset=offset, limit=limit)


@router.get("/{wonder_id}", response_model=Wonder)
async def get_wonder(wonder_id: UUID, container: Container) -> Wonder:
    return await _require_wonder(wonder_id, container)


@router.post("/{wonder_id}/feedback", response_model=Feedback, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    wonder_id: UUID,
    payload: FeedbackCreate,
    container: Container,
) -> Feedback:
    await _require_wonder(wonder_id, container)
    validate_safe_metadata(payload.metadata)
    if payload.note is not None:
        validate_safe_text(payload.note, max_length=5_000)
    return await container.feedback.submit(payload.to_domain(wonder_id))


@router.delete("/{wonder_id}/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    wonder_id: UUID,
    feedback_id: UUID,
    container: Container,
) -> Response:
    if not await container.deletion.delete_feedback(wonder_id, feedback_id):
        raise NotFoundError(
            "feedback not found",
            details={"wonder_id": str(wonder_id), "feedback_id": str(feedback_id)},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{wonder_id}/explore", response_model=DeepExploreResponse)
async def explore_wonder(wonder_id: UUID, container: Container) -> DeepExploreResponse:
    wonder = await _require_wonder(wonder_id, container)
    if wonder.candidate_id is None:
        raise ConflictError("wonder has no source candidate")
    candidate = await container.repositories.candidates.get(wonder.candidate_id)
    if candidate is None:
        raise ConflictError(
            "wonder source candidate is missing",
            details={"candidate_id": str(wonder.candidate_id)},
        )
    context = []
    for item_id in candidate.source_items:
        item = await container.repositories.knowledge.get(item_id)
        if item is not None:
            context.append(item)
    session = await container.repositories.sessions.get(candidate.session_id)
    max_runtime_calls = session.budget.max_runtime_calls if session is not None else 0
    evaluation = await container.deep_evaluation.evaluate(
        candidate,
        context,
        max_runtime_calls=max_runtime_calls,
    )
    wonder = _merge_evaluation(wonder, evaluation.model_dump(mode="json"))
    await container.repositories.wonders.update(wonder)
    return DeepExploreResponse(wonder=wonder, evaluation=evaluation.model_dump(mode="json"))


@router.post("/{wonder_id}/rewonder", response_model=Wonder | None)
async def rewonder(wonder_id: UUID, container: Container) -> Wonder | None:
    wonder = await _require_wonder(wonder_id, container)
    return await container.rewonder.run(wonder)


@router.delete("/{wonder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wonder(wonder_id: UUID, container: Container) -> Response:
    if not await container.deletion.delete_wonder(wonder_id):
        raise NotFoundError("wonder not found", details={"id": str(wonder_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _require_wonder(wonder_id: UUID, container: ApplicationContainer) -> Wonder:
    wonder = await container.repositories.wonders.get(wonder_id)
    if wonder is None:
        raise NotFoundError("wonder not found", details={"id": str(wonder_id)})
    return wonder


def _merge_evaluation(wonder: Wonder, evaluation: dict[str, Any]) -> Wonder:
    explorer = evaluation.get("explorer")
    evidence = evaluation["evidence"]
    critic = evaluation["critic"]
    if explorer:
        wonder.explanation = explorer["expanded_idea"]
        wonder.questions = explorer["follow_up_questions"]
    wonder.supporting_evidence = evidence["supporting_evidence"]
    wonder.counter_evidence = evidence["counter_evidence"]
    wonder.confidence = min(wonder.confidence, 1.0 - evidence["uncertainty"] / 2)
    if critic["verdict"] != CriticVerdict.PASS.value:
        wonder.confidence = min(wonder.confidence, 0.35)
    wonder.metadata["deep_evaluation"] = evaluation
    return wonder
