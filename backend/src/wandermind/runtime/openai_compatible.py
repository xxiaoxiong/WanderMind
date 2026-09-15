from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import httpx
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from pydantic import SecretStr

from wandermind.models.enums import RuntimeSessionStatus
from wandermind.runtime.base import (
    AgentRuntimeAdapter,
    RuntimeExecutionError,
    RuntimeInterruptedError,
    RuntimeMalformedOutputError,
    RuntimeSession,
    RuntimeStreamEvent,
    RuntimeTask,
    RuntimeTaskResult,
    RuntimeTimeoutError,
    RuntimeUnavailableError,
)


class OpenAICompatibleRuntimeAdapter(AgentRuntimeAdapter):
    def __init__(
        self,
        *,
        base_url: str,
        credential: SecretStr | str,
        model: str,
        temperature: float = 0.2,
        max_output_tokens: int = 2_000,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.credential = credential if isinstance(credential, SecretStr) else SecretStr(credential)
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.transport = transport
        self.sessions: dict[UUID, RuntimeSession] = {}
        self._inflight: dict[UUID, asyncio.Task[Any]] = {}

    async def start_session(self, purpose: str) -> RuntimeSession:
        session = RuntimeSession(
            provider="openai-compatible",
            purpose=purpose,
            metadata={"base_url": self.base_url, "model": self.model},
        )
        session.external_session_id = str(session.id)
        self.sessions[session.id] = session
        return session

    async def resume_session(self, session: RuntimeSession) -> RuntimeSession:
        stored = self.sessions.get(session.id)
        if stored is None or stored.status is RuntimeSessionStatus.CLOSED:
            raise RuntimeExecutionError("OpenAI-compatible session cannot be resumed")
        stored.status = RuntimeSessionStatus.ACTIVE
        return stored

    async def run_task(self, session: RuntimeSession, task: RuntimeTask) -> RuntimeTaskResult:
        self._ensure_active(session)
        current_task = asyncio.current_task()
        if current_task is not None:
            self._inflight[session.id] = current_task
        try:
            response = await self._request(task)
        except asyncio.CancelledError as error:
            session.status = RuntimeSessionStatus.INTERRUPTED
            raise RuntimeInterruptedError("OpenAI-compatible task was interrupted") from error
        finally:
            self._inflight.pop(session.id, None)

        structured, text = _parse_response(response, task.output_schema)
        session.status = RuntimeSessionStatus.COMPLETED
        return RuntimeTaskResult(
            session_id=session.id,
            external_turn_id=_response_id(response),
            text=text,
            structured=structured,
            usage=_usage(response, model=self.model),
        )

    async def stream_task(
        self,
        session: RuntimeSession,
        task: RuntimeTask,
    ) -> AsyncIterator[RuntimeStreamEvent]:
        self._ensure_active(session)
        yield RuntimeStreamEvent(type="started", data={"session_id": str(session.id)})
        result = await self.run_task(session, task)
        yield RuntimeStreamEvent(type="delta", data={"text": result.text})
        yield RuntimeStreamEvent(type="completed", data=result.model_dump(mode="json"))

    async def interrupt(self, session: RuntimeSession) -> None:
        self._ensure_active(session)
        session.status = RuntimeSessionStatus.INTERRUPTED
        running = self._inflight.get(session.id)
        if running is not None:
            running.cancel()

    async def close_session(self, session: RuntimeSession) -> None:
        running = self._inflight.get(session.id)
        if running is not None:
            running.cancel()
        session.status = RuntimeSessionStatus.CLOSED

    async def _request(self, task: RuntimeTask) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are WanderMind's structured cognitive evaluation runtime. "
                        "Return exactly one JSON object and no Markdown. The object must validate "
                        f"against this JSON Schema: {json.dumps(task.output_schema, ensure_ascii=False)}"
                    ),
                },
                {"role": "user", "content": task.prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        timeout = httpx.Timeout(task.timeout_seconds)
        headers = {
            "Authorization": f"Bearer {self.credential.get_secret_value()}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                transport=self.transport,
            ) as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload)
                if _should_retry_without_json_mode(response):
                    payload.pop("response_format")
                    response = await client.post(f"{self.base_url}/chat/completions", json=payload)
        except httpx.TimeoutException as error:
            raise RuntimeTimeoutError("OpenAI-compatible request timed out") from error
        except httpx.HTTPError as error:
            raise RuntimeUnavailableError("OpenAI-compatible endpoint is unavailable") from error

        _raise_for_status(response)
        try:
            data = response.json()
        except ValueError as error:
            raise RuntimeMalformedOutputError("runtime response is not valid JSON") from error
        if not isinstance(data, dict):
            raise RuntimeMalformedOutputError("runtime response must be a JSON object")
        return data

    def _ensure_active(self, session: RuntimeSession) -> None:
        if session.status is RuntimeSessionStatus.INTERRUPTED:
            raise RuntimeInterruptedError("runtime session was interrupted")
        if session.status is RuntimeSessionStatus.CLOSED:
            raise RuntimeExecutionError("runtime session is closed")


def _should_retry_without_json_mode(response: httpx.Response) -> bool:
    if response.status_code not in {400, 422}:
        return False
    body = response.text.casefold()
    return "response_format" in body or "json mode" in body


def _raise_for_status(response: httpx.Response) -> None:
    if 200 <= response.status_code < 300:
        return
    if response.status_code in {401, 403}:
        raise RuntimeExecutionError("runtime authentication failed")
    if response.status_code == 404:
        raise RuntimeExecutionError("runtime endpoint or model was not found")
    retryable = response.status_code == 429 or response.status_code >= 500
    raise RuntimeExecutionError(
        f"runtime request failed with HTTP {response.status_code}",
        retryable=retryable,
    )


def _parse_response(
    response: dict[str, Any],
    output_schema: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeMalformedOutputError("runtime response does not contain a completion choice")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeMalformedOutputError("runtime response does not contain a message")
    text = _content_text(message.get("content"))
    try:
        structured = json.loads(_strip_json_fence(text))
    except (TypeError, json.JSONDecodeError) as error:
        raise RuntimeMalformedOutputError("runtime message is not valid structured JSON") from error
    if not isinstance(structured, dict):
        raise RuntimeMalformedOutputError("runtime structured output must be an object")
    try:
        validate(instance=structured, schema=output_schema)
    except JsonSchemaValidationError as error:
        raise RuntimeMalformedOutputError(
            f"runtime output failed schema validation: {error.message}"
        ) from error
    return structured, text


def _content_text(content: object) -> str:
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            text_value = block.get("text")
            if isinstance(text_value, str):
                parts.append(text_value)
        text = "".join(parts)
        if text.strip():
            return text
    raise RuntimeMalformedOutputError("runtime message content is empty")


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _response_id(response: dict[str, Any]) -> str | None:
    value = response.get("id")
    return value if isinstance(value, str) else None


def _usage(response: dict[str, Any], *, model: str) -> dict[str, Any]:
    raw = response.get("usage")
    usage = raw if isinstance(raw, dict) else {}
    result: dict[str, Any] = {
        "provider": "openai-compatible",
        "model": response.get("model") if isinstance(response.get("model"), str) else model,
    }
    mapping = {
        "prompt_tokens": "input_tokens",
        "completion_tokens": "output_tokens",
        "total_tokens": "total_tokens",
    }
    for source, target in mapping.items():
        value = usage.get(source)
        if isinstance(value, int | float):
            result[target] = value
    return result
