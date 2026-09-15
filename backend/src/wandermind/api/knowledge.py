from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from wandermind.api.dependencies import get_container
from wandermind.api.schemas import KnowledgeCreate, KnowledgeListResponse
from wandermind.application.container import ApplicationContainer
from wandermind.infrastructure.errors import NotFoundError, UnsafeInputError
from wandermind.infrastructure.security import validate_safe_metadata, validate_safe_text
from wandermind.models import KnowledgeItem, KnowledgeType

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.post("", response_model=KnowledgeItem, status_code=status.HTTP_201_CREATED)
async def create_knowledge(payload: KnowledgeCreate, container: Container) -> KnowledgeItem:
    content = validate_safe_text(payload.content, max_length=200_000)
    metadata = validate_safe_metadata(payload.metadata)
    return await container.ingestion.ingest_text(
        content,
        title=payload.title,
        item_type=payload.type,
        source=payload.source,
        source_ref=payload.source_ref,
        metadata=metadata,
    )


@router.post("/document", response_model=KnowledgeItem, status_code=status.HTTP_201_CREATED)
async def upload_document(
    container: Container,
    file: UploadFile = File(...),
) -> KnowledgeItem:
    raw = await file.read(2_000_001)
    if len(raw) > 2_000_000:
        raise UnsafeInputError("document exceeds the 2 MB upload limit")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise UnsafeInputError("document must be UTF-8 text") from error
    content = validate_safe_text(content, max_length=200_000)
    return await container.ingestion.ingest_text(
        content,
        title=file.filename or "Uploaded document",
        item_type=KnowledgeType.DOCUMENT,
        source="upload",
        source_ref=file.filename,
    )


@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge(
    container: Container,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> KnowledgeListResponse:
    items = await container.repositories.knowledge.list(offset=offset, limit=limit)
    return KnowledgeListResponse(items=items, offset=offset, limit=limit)


@router.get("/search", response_model=list[KnowledgeItem])
async def search_knowledge(
    container: Container,
    q: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[KnowledgeItem]:
    return await container.repositories.knowledge.search(q, limit=limit)


@router.get("/{item_id}", response_model=KnowledgeItem)
async def get_knowledge(item_id: UUID, container: Container) -> KnowledgeItem:
    item = await container.repositories.knowledge.get(item_id)
    if item is None:
        raise NotFoundError("knowledge item not found", details={"id": str(item_id)})
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(item_id: UUID, container: Container) -> Response:
    if not await container.deletion.delete_knowledge(item_id):
        raise NotFoundError("knowledge item not found", details={"id": str(item_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
