from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from wandermind.api import create_app
from wandermind.application.container import ApplicationContainer, in_memory_container
from wandermind.infrastructure.config import Settings


@pytest.fixture
async def api_client() -> AsyncIterator[tuple[AsyncClient, ApplicationContainer]]:
    settings = Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        auto_create_schema=False,
        wonder_threshold=0.0,
        cheap_score_threshold=0.0,
    )
    container = in_memory_container(settings)
    app = create_app(settings, container=container)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client, container


@pytest.mark.asyncio
async def test_health_and_error_contracts(
    api_client: tuple[AsyncClient, ApplicationContainer],
) -> None:
    client, _ = api_client
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "version": "0.1.0",
        "environment": "test",
        "storage": "memory",
        "runtime": "mock",
    }

    invalid = await client.post("/api/v1/knowledge", json={"content": ""})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    unsafe = await client.post("/api/v1/knowledge", json={"content": "x" * 128})
    assert unsafe.status_code == 422
    assert unsafe.json()["error"]["code"] == "unsafe_input"

    credential_metadata = await client.post(
        "/api/v1/knowledge",
        json={"content": "Safe text", "metadata": {"api_token": "must-not-be-stored"}},
    )
    assert credential_metadata.status_code == 422
    assert credential_metadata.json()["error"]["code"] == "unsafe_input"

    deeply_nested_metadata = await client.post(
        "/api/v1/knowledge",
        json={
            "content": "Another safe text",
            "metadata": {"a": {"b": {"c": {"d": {"e": {"f": "too deep"}}}}}},
        },
    )
    assert deeply_nested_metadata.status_code == 422
    assert deeply_nested_metadata.json()["error"]["code"] == "unsafe_input"

    missing = await client.get(f"/api/v1/knowledge/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"

    oversized = await client.post(
        "/api/v1/knowledge",
        headers={"content-length": "3000000"},
        content=b"{}",
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "payload_too_large"


@pytest.mark.asyncio
async def test_wander_rejects_insufficient_knowledge_before_creating_work(
    api_client: tuple[AsyncClient, ApplicationContainer],
) -> None:
    client, container = api_client

    response = await client.post(
        "/api/v1/wander",
        json={"content": "How might these ideas connect?"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "insufficient_knowledge",
            "message": "at least two knowledge items are required to run a wander",
            "details": {"available_count": 0, "required_count": 2},
            "retryable": False,
        }
    }
    assert await container.repositories.seeds.list(offset=0, limit=10) == []
    assert await container.repositories.sessions.list(offset=0, limit=10) == []


@pytest.mark.asyncio
async def test_optional_basic_access_protects_everything_except_health() -> None:
    settings = Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        auto_create_schema=False,
        access_username="owner",
        access_password="correct horse battery staple",
    )
    app = create_app(settings, container=in_memory_container(settings))
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        assert (await client.get("/health")).status_code == 200
        unauthorized = await client.get("/api/v1/knowledge")
        assert unauthorized.status_code == 401
        assert unauthorized.headers["www-authenticate"].startswith("Basic ")
        assert unauthorized.json()["error"]["code"] == "authentication_required"
        authorized = await client.get(
            "/api/v1/knowledge",
            auth=("owner", "correct horse battery staple"),
        )
        assert authorized.status_code == 200


@pytest.mark.asyncio
async def test_knowledge_seed_wander_and_wonder_flow(
    api_client: tuple[AsyncClient, ApplicationContainer],
) -> None:
    client, container = api_client
    knowledge_payloads = [
        {
            "title": "Ant colonies",
            "content": (
                "Ant colonies allocate workers through local pheromone feedback without a central "
                "planner."
            ),
            "source_ref": "kb://ants",
        },
        {
            "title": "Distributed queues",
            "content": (
                "Distributed software queues use backpressure to prevent overloaded workers and "
                "stabilize throughput."
            ),
            "source_ref": "kb://queues",
        },
        {
            "title": "Urban gardens",
            "content": (
                "Urban gardens increase resilience by distributing food production across many "
                "neighborhoods."
            ),
            "source_ref": "kb://gardens",
        },
    ]
    created_items = []
    for payload in knowledge_payloads:
        response = await client.post("/api/v1/knowledge", json=payload)
        assert response.status_code == 201
        created_items.append(response.json())

    duplicate = await client.post("/api/v1/knowledge", json=knowledge_payloads[0])
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_knowledge"

    search = await client.get("/api/v1/knowledge/search", params={"q": "backpressure"})
    assert search.status_code == 200
    assert search.json()[0]["title"] == "Distributed queues"

    seed = await client.post(
        "/api/v1/seeds",
        json={
            "content": "How can decentralized systems avoid overload?",
            "source_item_id": created_items[1]["id"],
        },
    )
    assert seed.status_code == 201

    wander = await client.post(
        "/api/v1/wander",
        json={
            "seed_id": seed.json()["id"],
            "budget": {
                "max_steps": 8,
                "max_patch_switches": 2,
                "max_candidates": 3,
                "max_runtime_calls": 3,
                "time_budget_seconds": 30,
            },
        },
    )
    assert wander.status_code == 200
    wander_body = wander.json()
    assert wander_body["session"]["status"] == "completed"
    assert wander_body["candidates"]
    assert wander_body["wonders"]
    assert wander_body["runtime"]["verified"] is True
    assert wander_body["runtime"]["provider"] == "mock"
    assert wander_body["runtime"]["calls"] == 3
    assert wander_body["runtime"]["completed_calls"] == 3
    assert wander_body["runtime"]["purposes"] == [
        "candidate_synthesis",
        "evidence",
        "critic",
    ]

    metrics = await client.get("/metrics")
    assert metrics.status_code == 200
    for metric_name in (
        "wandermind_wander_duration_seconds",
        "wandermind_wander_step_count",
        "wandermind_patch_switch_count",
        "wandermind_candidate_count",
        "wandermind_wonder_score",
        "wandermind_wonder_count",
    ):
        assert metric_name in metrics.text

    session_id = wander_body["session"]["id"]
    stream = await client.get(f"/api/v1/wander/{session_id}/stream")
    assert stream.status_code == 200
    assert "event: wander_step" in stream.text
    assert "event: completed" in stream.text
    assert '"candidate_count":' in stream.text
    assert '"current_patch":' in stream.text

    wonder_id = wander_body["wonders"][0]["id"]
    detail = await client.get(f"/api/v1/wonders/{wonder_id}")
    assert detail.status_code == 200

    explored = await client.post(f"/api/v1/wonders/{wonder_id}/explore")
    assert explored.status_code == 200
    assert explored.json()["evaluation"]["critic"]["verdict"] == "pass"
    assert explored.json()["wonder"]["metadata"]["deep_evaluation"]
    assert explored.json()["evaluation"]["evidence"]["supporting_evidence"] == []
    assert explored.json()["evaluation"]["evidence"]["uncertainty"] >= 0.8
    runtime_sessions = await container.repositories.runtime_sessions.list(offset=0, limit=10)
    assert len(runtime_sessions) == 6
    assert all(str(value.wander_session_id) == session_id for value in runtime_sessions)
    assert all(value.status.value == "closed" for value in runtime_sessions)
    assert all(value.cost["runtime_calls"] == 1 for value in runtime_sessions)
    metrics = await client.get("/metrics")
    assert "wandermind_runtime_calls_total" in metrics.text

    feedback = await client.post(
        f"/api/v1/wonders/{wonder_id}/feedback",
        json={"action": "save", "note": "Worth testing"},
    )
    assert feedback.status_code == 201
    feedback_id = feedback.json()["id"]
    updated = await client.get(f"/api/v1/wonders/{wonder_id}")
    assert updated.json()["status"] == "saved"

    deleted_feedback = await client.delete(f"/api/v1/wonders/{wonder_id}/feedback/{feedback_id}")
    assert deleted_feedback.status_code == 204
    assert await container.repositories.feedback.get(UUID(feedback_id)) is None

    replacement_feedback = await client.post(
        f"/api/v1/wonders/{wonder_id}/feedback",
        json={"action": "save_for_later"},
    )
    replacement_feedback_id = replacement_feedback.json()["id"]

    child = await client.post(f"/api/v1/wonders/{wonder_id}/rewonder")
    assert child.status_code == 200
    assert child.json()["parent_wonder_id"] == wonder_id
    child_id = child.json()["id"]
    child_feedback = await client.post(
        f"/api/v1/wonders/{child_id}/feedback",
        json={"action": "interesting"},
    )
    child_feedback_id = child_feedback.json()["id"]
    assert (await client.delete(f"/api/v1/wonders/{child_id}")).status_code == 204
    assert (await client.get(f"/api/v1/wonders/{child_id}")).status_code == 404
    assert await container.repositories.feedback.get(UUID(child_feedback_id)) is None

    candidate_id = wander_body["candidates"][0]["id"]
    assert (await client.delete(f"/api/v1/wander/{session_id}")).status_code == 204
    assert (await client.get(f"/api/v1/wander/{session_id}")).status_code == 404
    assert (await client.get(f"/api/v1/wonders/{wonder_id}")).status_code == 404
    assert await container.repositories.candidates.get(UUID(candidate_id)) is None
    assert await container.repositories.feedback.get(UUID(replacement_feedback_id)) is None
    stored_runtime_sessions = await container.repositories.runtime_sessions.list(
        offset=0,
        limit=10,
    )
    assert all(str(value.wander_session_id) != session_id for value in stored_runtime_sessions)


@pytest.mark.asyncio
async def test_incubation_is_silent_without_enough_knowledge(
    api_client: tuple[AsyncClient, ApplicationContainer],
) -> None:
    client, _ = api_client
    response = await client.post("/api/v1/incubation/run")
    assert response.status_code == 200
    assert response.json() == {"surfaced": False, "wonder": None}


@pytest.mark.asyncio
async def test_recent_seed_and_incubation_can_surface(
    api_client: tuple[AsyncClient, ApplicationContainer],
) -> None:
    client, _ = api_client
    for title, content in [
        ("Old ecology", "Old ecological systems recover through diverse local feedback."),
        ("New software", "New software systems use circuit breakers for cascade control."),
        ("Extra context", "Communities distribute response capacity before uncertain shocks."),
    ]:
        response = await client.post(
            "/api/v1/knowledge",
            json={"title": title, "content": content},
        )
        assert response.status_code == 201

    recent_wander = await client.post("/api/v1/wander", json={})
    assert recent_wander.status_code == 200
    seed_id = recent_wander.json()["session"]["seed_id"]
    seed = await client.get(f"/api/v1/seeds/{seed_id}")
    assert seed.json()["source"] == "recent"

    incubation = await client.post("/api/v1/incubation/run")
    assert incubation.status_code == 200
    assert incubation.json()["surfaced"] is True
    assert incubation.json()["wonder"] is not None


@pytest.mark.asyncio
async def test_document_upload_and_delete(
    api_client: tuple[AsyncClient, ApplicationContainer],
) -> None:
    client, _ = api_client
    response = await client.post(
        "/api/v1/knowledge/document",
        files={"file": ("notes.txt", b"A short UTF-8 knowledge document.", "text/plain")},
    )
    assert response.status_code == 201
    item_id = response.json()["id"]
    deleted = await client.delete(f"/api/v1/knowledge/{item_id}")
    assert deleted.status_code == 204
    missing = await client.get(f"/api/v1/knowledge/{item_id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_idea_graph_api_supports_relation_queries(
    api_client: tuple[AsyncClient, ApplicationContainer],
) -> None:
    client, _ = api_client
    source = await client.post(
        "/api/v1/knowledge",
        json={"title": "Hypothesis", "content": "Local feedback stabilizes demand."},
    )
    evidence = await client.post(
        "/api/v1/knowledge",
        json={"title": "Evidence", "content": "Queue measurements remain bounded."},
    )
    assert source.status_code == 201
    assert evidence.status_code == 201

    edge = await client.post(
        "/api/v1/graph/edges",
        json={
            "source_id": evidence.json()["id"],
            "target_id": source.json()["id"],
            "relation_type": "evidence_for",
            "metadata": {"experiment": "queue-load-01"},
        },
    )
    assert edge.status_code == 201

    neighbors = await client.get(f"/api/v1/graph/{source.json()['id']}/neighbors")
    evidence_view = await client.get(f"/api/v1/graph/{source.json()['id']}/evidence")
    contradictions = await client.get(f"/api/v1/graph/{source.json()['id']}/contradictions")
    assert len(neighbors.json()["items"]) == 2
    assert evidence_view.json()["edges"][0]["id"] == edge.json()["id"]
    assert contradictions.json()["edges"] == []

    deleted = await client.delete(f"/api/v1/graph/edges/{edge.json()['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/graph/{source.json()['id']}/evidence")).json()["edges"] == []


@pytest.mark.asyncio
async def test_embedding_failure_uses_retryable_error_contract(
    api_client: tuple[AsyncClient, ApplicationContainer],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, container = api_client

    async def fail_embedding(_text: str) -> list[float]:
        raise OSError("embedding provider unavailable")

    monkeypatch.setattr(container.ingestion.embedding, "embed_text", fail_embedding)
    response = await client.post(
        "/api/v1/knowledge",
        json={"title": "Failure probe", "content": "A unique embedding failure probe."},
    )

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "embedding_error",
        "message": "knowledge embedding failed",
        "details": {},
        "retryable": True,
    }
