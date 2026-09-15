from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from wandermind.evaluation import run_performance_smoke


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WanderMind scale and leak smoke checks")
    parser.add_argument("--knowledge", type=int, default=1_000)
    parser.add_argument("--sessions", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("../reports/performance_latest.json"))
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    report = await run_performance_smoke(
        knowledge_count=args.knowledge,
        session_count=args.sessions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
