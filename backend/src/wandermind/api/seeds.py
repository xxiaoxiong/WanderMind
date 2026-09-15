from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from wandermind.api.dependencies import get_container
from wandermind.api.schemas import SeedCreate
from wandermind.application.container import ApplicationContainer
from wandermind.infrastructure.errors import NotFoundError
from wandermind.infrastructure.security import validate_safe_metadata, validate_safe_text
from wandermind.models import Seed

router = APIRouter(prefix="/seeds", tags=["seeds"])
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.post("", response_model=Seed, status_code=status.HTTP_201_CREATED)
async def create_seed(payload: SeedCreate, container: Container) -> Seed:
    validate_safe_text(payload.content, max_length=20_000)
    validate_safe_metadata(payload.metadata)
    if payload.source_item_id is not None:
        source_item = await container.repositories.knowledge.get(payload.source_item_id)
        if source_item is None:
            raise NotFoundError(
                "seed source knowledge not found",
                details={"id": str(payload.source_item_id)},
            )
    return await container.repositories.seeds.create(payload.to_domain())


@router.get("", response_model=list[Seed])
async def list_seeds(
    container: Container,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Seed]:
    return await container.repositories.seeds.list(offset=offset, limit=limit)


@router.get("/{seed_id}", response_model=Seed)
async def get_seed(seed_id: UUID, container: Container) -> Seed:
    seed = await container.repositories.seeds.get(seed_id)
    if seed is None:
        raise NotFoundError("seed not found", details={"id": str(seed_id)})
    return seed
