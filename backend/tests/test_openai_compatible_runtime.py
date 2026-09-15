import json

import httpx
import pytest
from pydantic import SecretStr

from wandermind.runtime import (
    OpenAICompatibleRuntimeAdapter,
    RuntimeExecutionError,
    RuntimeMalformedOutputError,
    RuntimeTask,
)

SCHEMA = {
    "type": "object",
    "required": ["answer"],
    "properties": {"answer": {"type": "string"}},
    "additionalProperties": False,
}


def completion(
    content: str = '{"answer":"yes"}',
    *,
    response_id: str = "completion-1",
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": response_id,
            "model": "agnes-2.5-flash",
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 4,
                "total_tokens": 16,
            },
        },
    )


def adapter(handler: httpx.AsyncBaseTransport) -> OpenAICompatibleRuntimeAdapter:
    return OpenAICompatibleRuntimeAdapter(
        base_url="https://example.test/v1/",
        credential=SecretStr("test-secret"),
        model="agnes-2.5-flash",
        transport=handler,
    )


@pytest.mark.asyncio
async def test_openai_compatible_runtime_sends_structured_request_and_maps_usage() -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://example.test/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-secret"
        payload = json.loads(request.content)
        assert payload["model"] == "agnes-2.5-flash"
        assert payload["response_format"] == {"type": "json_object"}
        assert "JSON Schema" in payload["messages"][0]["content"]
        return completion()

    runtime = adapter(httpx.MockTransport(handle))
    session = await runtime.start_session("explorer")
    result = await runtime.run_task(
        session,
        RuntimeTask(prompt="Return an answer", output_schema=SCHEMA),
    )

    assert result.structured == {"answer": "yes"}
    assert result.external_turn_id == "completion-1"
    assert result.usage == {
        "provider": "openai-compatible",
        "model": "agnes-2.5-flash",
        "input_tokens": 12,
        "output_tokens": 4,
        "total_tokens": 16,
    }
    assert session.status.value == "completed"


@pytest.mark.asyncio
async def test_openai_compatible_runtime_retries_without_json_mode() -> None:
    requests: list[dict[str, object]] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(400, json={"error": "response_format is unsupported"})
        return completion('```json\n{"answer":"fallback"}\n```')

    runtime = adapter(httpx.MockTransport(handle))
    session = await runtime.start_session("explorer")
    result = await runtime.run_task(
        session,
        RuntimeTask(prompt="Return an answer", output_schema=SCHEMA),
    )

    assert result.structured == {"answer": "fallback"}
    assert "response_format" in requests[0]
    assert "response_format" not in requests[1]


@pytest.mark.asyncio
async def test_openai_compatible_runtime_rejects_invalid_structured_output() -> None:
    runtime = adapter(httpx.MockTransport(lambda _request: completion('{"wrong":true}')))
    session = await runtime.start_session("explorer")

    with pytest.raises(RuntimeMalformedOutputError, match="schema validation"):
        await runtime.run_task(
            session,
            RuntimeTask(prompt="Return an answer", output_schema=SCHEMA),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "retryable"),
    [(401, False), (429, True), (503, True)],
)
async def test_openai_compatible_runtime_maps_http_errors(
    status_code: int,
    retryable: bool,
) -> None:
    runtime = adapter(
        httpx.MockTransport(lambda _request: httpx.Response(status_code, json={"error": "safe"}))
    )
    session = await runtime.start_session("explorer")

    with pytest.raises(RuntimeExecutionError) as raised:
        await runtime.run_task(
            session,
            RuntimeTask(prompt="Return an answer", output_schema=SCHEMA),
        )

    assert raised.value.retryable is retryable
