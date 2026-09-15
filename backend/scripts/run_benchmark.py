from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from wandermind.evaluation import load_benchmark_cases, load_knowledge_dataset, run_benchmark
from wandermind.evaluation.benchmark import regression_failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deterministic WanderMind benchmark")
    parser.add_argument("--dataset", type=Path, default=Path("../data/demo_knowledge.jsonl"))
    parser.add_argument("--cases", type=Path, default=Path("../data/known_connections.json"))
    parser.add_argument("--baseline", type=Path, default=Path("../data/baseline_v1.json"))
    parser.add_argument("--output", type=Path, default=Path("../reports/benchmark_latest.json"))
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    report = await run_benchmark(
        load_knowledge_dataset(args.dataset),
        load_benchmark_cases(args.cases),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    failures = regression_failures(report, baseline)
    print(report.model_dump_json(indent=2))
    if failures:
        print("Regression gate failed: " + "; ".join(failures))
        return 1
    print("Regression gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
