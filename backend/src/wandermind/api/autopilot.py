from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from wandermind.api.dependencies import get_container
from wandermind.api.schemas import AutopilotStart
from wandermind.application.autopilot_service import AutopilotSnapshot
from wandermind.application.container import ApplicationContainer

router = APIRouter(prefix="/autopilot", tags=["autopilot"])
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.get("/status", response_model=AutopilotSnapshot)
async def autopilot_status(container: Container) -> AutopilotSnapshot:
    return await container.autopilot.snapshot()


@router.post("/start", response_model=AutopilotSnapshot)
async def start_autopilot(
    payload: AutopilotStart,
    container: Container,
) -> AutopilotSnapshot:
    return await container.autopilot.start_or_resume(
        objective=payload.objective,
        budget=payload.budget,
    )


@router.post("/resume", response_model=AutopilotSnapshot)
async def resume_autopilot(container: Container) -> AutopilotSnapshot:
    return await container.autopilot.start_or_resume()


@router.post("/pause", response_model=AutopilotSnapshot)
async def pause_autopilot(container: Container) -> AutopilotSnapshot:
    return await container.autopilot.pause()


@router.post("/stop", response_model=AutopilotSnapshot)
async def stop_autopilot(container: Container) -> AutopilotSnapshot:
    return await container.autopilot.stop()
