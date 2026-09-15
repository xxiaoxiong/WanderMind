from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from wandermind.api.dependencies import get_container
from wandermind.api.schemas import IncubationResponse
from wandermind.application.container import ApplicationContainer

router = APIRouter(prefix="/incubation", tags=["incubation"])
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.post("/run", response_model=IncubationResponse)
async def run_incubation(container: Container) -> IncubationResponse:
    wonder = await container.incubation.run(trigger="api")
    return IncubationResponse(surfaced=wonder is not None, wonder=wonder)
