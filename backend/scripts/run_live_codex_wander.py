from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from wandermind.application.container import build_container
from wandermind.application.runtime_summary import summarize_runtime
from wandermind.infrastructure.config import Settings
from wandermind.models import Seed, WanderBudget
from wandermind.repositories import InMemoryRepositoryBundle


async def run(executable: str, cwd: str, timeout_seconds: float) -> dict[str, object]:
    settings = Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        runtime_adapter="codex",
        codex_executable=executable,
        runtime_cwd=cwd,
        runtime_timeout_seconds=timeout_seconds,
        runtime_max_retries=0,
        cheap_score_threshold=0.0,
        wonder_threshold=0.4,
        auto_create_schema=False,
    )
    container = build_container(settings, repositories=InMemoryRepositoryBundle())
    started = time.perf_counter()
    try:
        for title, content, domain in [
            (
                "Distributed queue backpressure",
                "A queue can slow admission when local depth and processing delay exceed safe limits.",
                "software",
            ),
            (
                "Ant pheromone decay",
                "Ant colonies reduce traffic on stale paths as pheromone signals decay without reinforcement.",
                "ecology",
            ),
            (
                "Attention switching cost",
                "Knowledge workers lose effective capacity when too many tasks remain concurrently active.",
                "cognition",
            ),
        ]:
            await container.ingestion.ingest_text(
                content,
                title=title,
                source="codex-live-smoke",
                source_ref=f"smoke://{domain}",
                metadata={"domain": domain},
            )
        seed = await container.repositories.seeds.create(
            Seed(
                content=(
                    "How could queue backpressure and pheromone decay create a testable protocol "
                    "for preventing attention overload?"
                )
            )
        )
        result = await container.wander_engine.run(
            seed,
            WanderBudget(
                max_steps=4,
                max_patch_switches=2,
                max_candidates=1,
                max_runtime_calls=2,
                time_budget_seconds=timeout_seconds * 2 + 30,
            ),
        )
        runtime_sessions = await container.repositories.runtime_sessions.list_for_wander(
            result.session.id
        )
        runtime = summarize_runtime(settings.runtime_adapter, runtime_sessions)
        return {
            "success": bool(
                result.session.status.value == "completed"
                and result.candidates
                and runtime.verified
                and runtime.calls == 2
                and runtime.purposes == ["candidate_synthesis", "candidate_review"]
            ),
            "duration_seconds": round(time.perf_counter() - started, 3),
            "session_status": result.session.status.value,
            "stop_reason": result.session.trace.stop_reason,
            "candidate_count": len(result.candidates),
            "wonder_count": len(result.wonders),
            "candidate_status": result.candidates[0].status.value if result.candidates else None,
            "runtime": runtime.model_dump(mode="json"),
            "runtime_sessions": [
                {
                    "purpose": session.purpose,
                    "status": session.status.value,
                    "last_error": session.metadata.get("last_error"),
                    "last_error_message": session.metadata.get("last_error_message"),
                }
                for session in runtime_sessions
            ],
        }
    finally:
        await container.runtime.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run a real end-to-end Codex Wander smoke test")
    parser.add_argument("--executable", default="codex")
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    arguments = parser.parse_args()
    result = await run(arguments.executable, arguments.cwd, arguments.timeout_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
