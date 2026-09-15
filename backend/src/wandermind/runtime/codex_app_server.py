from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate

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
    SandboxMode,
)


class JsonRpcProcess:
    def __init__(self, executable: str, cwd: str) -> None:
        self.executable = executable
        self.cwd = cwd
        self.process: asyncio.subprocess.Process | None = None
        self.pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self.notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.reader_task: asyncio.Task[None] | None = None
        self.stderr_task: asyncio.Task[None] | None = None
        self.next_id = 1
        self.stderr_lines: list[str] = []

    async def start(self) -> None:
        if self.process is not None:
            return
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.executable,
                "app-server",
                "--stdio",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )
        except OSError as error:
            raise RuntimeUnavailableError(f"cannot start Codex app-server: {error}") from error
        self.reader_task = asyncio.create_task(self._read_stdout())
        self.stderr_task = asyncio.create_task(self._read_stderr())
        await self.call(
            "initialize",
            {
                "clientInfo": {
                    "name": "wandermind",
                    "title": "WanderMind Runtime Adapter",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
            timeout_seconds=15.0,
        )
        await self.notify("initialized")

    async def call(
        self,
        method: str,
        params: dict[str, Any],
        *,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self.pending[request_id] = future
        await self._send({"id": request_id, "method": method, "params": params})
        try:
            return await asyncio.wait_for(future, timeout=timeout_seconds)
        except TimeoutError as error:
            self.pending.pop(request_id, None)
            raise RuntimeTimeoutError(f"Codex RPC timed out: {method}") from error

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"method": method}
        if params is not None:
            payload["params"] = params
        await self._send(payload)

    async def close(self) -> None:
        if self.process is None:
            return
        if self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
        for task in (self.reader_task, self.stderr_task):
            if task is not None:
                task.cancel()
        self.process = None

    async def _send(self, payload: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeUnavailableError("Codex app-server is not running")
        encoded = (json.dumps(payload, ensure_ascii=False) + chr(10)).encode("utf-8")
        self.process.stdin.write(encoded)
        await self.process.stdin.drain()

    async def _read_stdout(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        while line := await self.process.stdout.readline():
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            request_id = message.get("id")
            if request_id is not None and ("result" in message or "error" in message):
                future = self.pending.pop(request_id, None)
                if future is None:
                    continue
                if "error" in message:
                    error = message["error"]
                    future.set_exception(
                        RuntimeExecutionError(
                            f"Codex RPC error {error.get('code')}: {error.get('message')}",
                            retryable=False,
                        )
                    )
                else:
                    future.set_result(message.get("result", {}))
            elif "method" in message:
                await self.notifications.put(message)
        error = RuntimeUnavailableError("Codex app-server exited")
        for future in self.pending.values():
            if not future.done():
                future.set_exception(error)
        self.pending.clear()

    async def _read_stderr(self) -> None:
        assert self.process is not None and self.process.stderr is not None
        while line := await self.process.stderr.readline():
            text = line.decode("utf-8", errors="replace").strip()
            if text:
                self.stderr_lines.append(text)
                self.stderr_lines = self.stderr_lines[-100:]


class CodexRuntimeAdapter(AgentRuntimeAdapter):
    def __init__(
        self,
        *,
        executable: str = "codex",
        cwd: str | None = None,
        allow_workspace_write: bool = False,
    ) -> None:
        resolved_cwd = str(Path(cwd or Path.cwd()).resolve())
        self.client = JsonRpcProcess(executable, resolved_cwd)
        self.cwd = resolved_cwd
        self.allow_workspace_write = allow_workspace_write
        self.active_turns: dict[str, str] = {}

    async def start_session(self, purpose: str) -> RuntimeSession:
        await self.client.start()
        response = await self.client.call(
            "thread/start",
            {
                "cwd": self.cwd,
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "ephemeral": False,
                "serviceName": "wandermind",
            },
            timeout_seconds=20.0,
        )
        thread = response.get("thread", {})
        thread_id = thread.get("id")
        if not isinstance(thread_id, str):
            raise RuntimeMalformedOutputError("thread/start response has no thread id")
        return RuntimeSession(
            provider="codex-app-server",
            purpose=purpose,
            external_session_id=thread_id,
            metadata={"cwd": self.cwd},
        )

    async def resume_session(self, session: RuntimeSession) -> RuntimeSession:
        thread_id = self._thread_id(session)
        await self.client.start()
        await self.client.call(
            "thread/resume",
            {
                "threadId": thread_id,
                "cwd": self.cwd,
                "approvalPolicy": "never",
                "sandbox": "read-only",
            },
            timeout_seconds=20.0,
        )
        session.status = RuntimeSessionStatus.ACTIVE
        return session

    async def run_task(self, session: RuntimeSession, task: RuntimeTask) -> RuntimeTaskResult:
        started = time.perf_counter()
        text_parts: list[str] = []
        completed_turn: dict[str, Any] | None = None
        turn_id: str | None = None
        try:
            async with asyncio.timeout(task.timeout_seconds):
                async for event in self.stream_task(session, task):
                    if event.type == "delta":
                        text_parts.append(str(event.data.get("text", "")))
                    elif event.type == "completed":
                        completed_turn = event.data.get("turn")
                        turn_id = event.data.get("turn_id")
        except TimeoutError as error:
            await self.interrupt(session)
            raise RuntimeTimeoutError("Codex turn exceeded its time budget") from error
        if completed_turn is None:
            raise RuntimeExecutionError("Codex turn ended without completion")
        status = completed_turn.get("status")
        if status not in {"completed", "success"}:
            raise RuntimeExecutionError(
                f"Codex turn failed with status {status}: {completed_turn.get('error')}",
                retryable=status in {"failed", "interrupted"},
            )
        text = "".join(text_parts).strip() or _agent_text(completed_turn)
        structured = _parse_structured(text, task.output_schema)
        session.status = RuntimeSessionStatus.COMPLETED
        raw_usage = completed_turn.get("usage", {})
        usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}
        usage.update(
            {
                "runtime_calls": 1,
                "provider": session.provider,
                "duration_seconds": time.perf_counter() - started,
            }
        )
        return RuntimeTaskResult(
            session_id=session.id,
            external_turn_id=turn_id,
            text=text,
            structured=structured,
            usage=usage,
        )

    async def stream_task(
        self,
        session: RuntimeSession,
        task: RuntimeTask,
    ) -> AsyncIterator[RuntimeStreamEvent]:
        if session.status is RuntimeSessionStatus.INTERRUPTED:
            raise RuntimeInterruptedError("runtime session was interrupted")
        if task.sandbox is SandboxMode.WORKSPACE_WRITE and not self.allow_workspace_write:
            raise RuntimeExecutionError("workspace-write requires explicit adapter policy")
        thread_id = self._thread_id(session)
        await self.client.start()
        response = await self.client.call(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": task.prompt}],
                "outputSchema": task.output_schema,
                "approvalPolicy": "never",
                "sandboxPolicy": self._sandbox_policy(task),
                "cwd": self.cwd,
            },
            timeout_seconds=min(20.0, task.timeout_seconds),
        )
        turn = response.get("turn", {})
        turn_id = turn.get("id")
        if not isinstance(turn_id, str):
            raise RuntimeMalformedOutputError("turn/start response has no turn id")
        self.active_turns[thread_id] = turn_id
        yield RuntimeStreamEvent(type="started", data={"thread_id": thread_id, "turn_id": turn_id})
        while True:
            notification = await self.client.notifications.get()
            method = notification.get("method")
            params = notification.get("params", {})
            if params.get("threadId") != thread_id or params.get("turnId", turn_id) != turn_id:
                continue
            if method == "item/agentMessage/delta":
                yield RuntimeStreamEvent(type="delta", data={"text": params.get("delta", "")})
            elif method == "turn/completed":
                self.active_turns.pop(thread_id, None)
                yield RuntimeStreamEvent(
                    type="completed",
                    data={"turn_id": turn_id, "turn": params.get("turn", {})},
                )
                return

    async def interrupt(self, session: RuntimeSession) -> None:
        thread_id = self._thread_id(session)
        turn_id = self.active_turns.get(thread_id)
        if turn_id is not None:
            await self.client.call(
                "turn/interrupt",
                {"threadId": thread_id, "turnId": turn_id},
                timeout_seconds=10.0,
            )
        session.status = RuntimeSessionStatus.INTERRUPTED

    async def close_session(self, session: RuntimeSession) -> None:
        thread_id = self._thread_id(session)
        if thread_id in self.active_turns:
            await self.interrupt(session)
        await self.client.call(
            "thread/archive",
            {"threadId": thread_id},
            timeout_seconds=10.0,
        )
        session.status = RuntimeSessionStatus.CLOSED

    async def close(self) -> None:
        await self.client.close()

    def _thread_id(self, session: RuntimeSession) -> str:
        if session.external_session_id is None:
            raise RuntimeExecutionError("runtime session has no external thread id")
        return session.external_session_id

    def _sandbox_policy(self, task: RuntimeTask) -> dict[str, Any]:
        if task.sandbox is SandboxMode.READ_ONLY:
            return {"type": "readOnly", "networkAccess": False}
        roots = task.workspace_roots or [self.cwd]
        return {
            "type": "workspaceWrite",
            "writableRoots": roots,
            "networkAccess": False,
        }


def _agent_text(turn: dict[str, Any]) -> str:
    messages = [
        item.get("text", "") for item in turn.get("items", []) if item.get("type") == "agentMessage"
    ]
    return chr(10).join(part for part in messages if part).strip()


def _parse_structured(text: str, schema: dict[str, Any]) -> dict[str, Any]:
    candidate = text.strip()
    fence = chr(96) * 3
    if candidate.startswith(fence):
        lines = candidate.splitlines()
        candidate = chr(10).join(lines[1:-1])
        if candidate.lstrip().startswith("json"):
            candidate = candidate.lstrip()[4:].lstrip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise RuntimeMalformedOutputError("Codex response is not valid JSON") from error
    if not isinstance(value, dict):
        raise RuntimeMalformedOutputError("Codex structured output must be an object")
    try:
        validate(instance=value, schema=schema)
    except JsonSchemaValidationError as error:
        raise RuntimeMalformedOutputError(
            f"Codex output failed schema validation: {error.message}"
        ) from error
    return value
