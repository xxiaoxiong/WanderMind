from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from wandermind.api.dependencies import get_container
from wandermind.api.schemas import GraphViewResponse, KnowledgeEdgeCreate
from wandermind.application.container import ApplicationContainer
from wandermind.infrastructure.errors import NotFoundError
from wandermind.infrastructure.security import validate_safe_metadata
from wandermind.models import KnowledgeEdge, RelationType

router = APIRouter(prefix="/graph", tags=["idea-graph"])
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.post("/edges", response_model=KnowledgeEdge, status_code=status.HTTP_201_CREATED)
async def create_edge(payload: KnowledgeEdgeCreate, container: Container) -> KnowledgeEdge:
    metadata = validate_safe_metadata(payload.metadata)
    return await container.graph.create_edge(payload.to_domain(metadata=metadata))


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(edge_id: UUID, container: Container) -> Response:
    if not await container.repositories.graph.delete(edge_id):
        raise NotFoundError("knowledge edge not found", details={"id": str(edge_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{item_id}/neighbors", response_model=GraphViewResponse)
async def get_neighbors(
    item_id: UUID,
    container: Container,
    relation_type: list[RelationType] | None = Query(default=None),
) -> GraphViewResponse:
    relations = set(relation_type) if relation_type else None
    return GraphViewResponse.from_view(await container.graph.neighbors(item_id, relations))


@router.get("/{item_id}/lineage", response_model=GraphViewResponse)
async def get_lineage(
    item_id: UUID,
    container: Container,
    max_depth: int = Query(default=10, ge=1, le=50),
) -> GraphViewResponse:
    return GraphViewResponse.from_view(await container.graph.lineage(item_id, max_depth=max_depth))


@router.get("/{item_id}/evidence", response_model=GraphViewResponse)
async def get_evidence(item_id: UUID, container: Container) -> GraphViewResponse:
    return GraphViewResponse.from_view(await container.graph.evidence(item_id))


@router.get("/{item_id}/contradictions", response_model=GraphViewResponse)
async def get_contradictions(item_id: UUID, container: Container) -> GraphViewResponse:
    return GraphViewResponse.from_view(await container.graph.contradictions(item_id))
