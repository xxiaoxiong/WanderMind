from fastapi import APIRouter

from wandermind.api import graph, incubation, knowledge, seeds, wander, wonders

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(knowledge.router)
api_router.include_router(graph.router)
api_router.include_router(seeds.router)
api_router.include_router(wander.router)
api_router.include_router(wonders.router)
api_router.include_router(incubation.router)
