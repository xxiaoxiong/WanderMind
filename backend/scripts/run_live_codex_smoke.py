from __future__ import annotations

import argparse
import asyncio
import json
import time
from contextlib import suppress
from pathlib import Path

from wandermind.runtime import (
    CodexRuntimeAdapter,
    RuntimeErrorBase,
    RuntimeSession,
    RuntimeTask,
    SandboxMode,
)


async def run(executable: str, cwd: str, timeout_seconds: float) -> dict[str, object]:
    runtime = CodexRuntimeAdapter(executable=executable, cwd=cwd)
    session: RuntimeSession | None = None
    started = time.perf_counter()
    try:
        session = await runtime.start_session("codex_live_smoke")
        result = await runtime.run_task(
            session,
            RuntimeTask(
                prompt=(
                    "This is a read-only WanderMind runtime smoke test. Return a JSON object with "
                    'status set to "ok" and runtime set to "codex-app-server". Do not inspect or '
                    "modify workspace files."
                ),
                output_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["status", "runtime"],
                    "properties": {
                        "status": {"type": "string", "const": "ok"},
                        "runtime": {"type": "string", "const": "codex-app-server"},
                    },
                },
                sandbox=SandboxMode.READ_ONLY,
                timeout_seconds=timeout_seconds,
            ),
        )
        return {
            "success": True,
            "provider": session.provider,
            "schema_valid": result.structured
            == {"status": "ok", "runtime": "codex-app-server"},
            "duration_seconds": round(time.perf_counter() - started, 3),
        }
    finally:
        if session is not None:
            with suppress(RuntimeErrorBase):
                await runtime.close_session(session)
        await runtime.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run a real Codex app-server smoke test")
    parser.add_argument("--executable", default="codex")
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    arguments = parser.parse_args()
    result = await run(arguments.executable, arguments.cwd, arguments.timeout_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
