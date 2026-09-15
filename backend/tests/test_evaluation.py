from __future__ import annotations

import json
from pathlib import Path

import pytest

from wandermind.evaluation import (
    BenchmarkCase,
    load_benchmark_cases,
    load_knowledge_dataset,
    run_benchmark,
    run_performance_smoke,
)
from wandermind.evaluation.benchmark import regression_failures


def test_load_dataset_and_cases(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps({"title": "One", "content": "Feedback stabilizes ecological systems."}),
                json.dumps({"title": "Two", "content": "Backpressure stabilizes software queues."}),
            ]
        ),
        encoding="utf-8",
    )
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "id": "case-1",
                    "seed": "How do feedback systems transfer?",
                    "label": "interesting",
                    "domains": ["ecology", "software"],
                    "rationale": "Cross-domain control pattern",
                }
            ]
        ),
        encoding="utf-8",
    )
    assert len(load_knowledge_dataset(dataset)) == 2
    assert load_benchmark_cases(cases_path)[0].id == "case-1"


@pytest.mark.asyncio
async def test_benchmark_report_and_regression_gate() -> None:
    records: list[dict[str, object]] = [
        {"title": "Ecology", "content": "Ecological feedback balances shared resources."},
        {"title": "Software", "content": "Software backpressure controls overloaded queues."},
        {"title": "Learning", "content": "Learning improves through delayed corrective feedback."},
    ]
    cases = [
        BenchmarkCase(
            id="cross-feedback",
            seed="How can feedback stabilize different systems?",
            label="interesting",
            domains=["ecology", "software"],
            rationale="Known cross-domain mechanism",
        )
    ]
    report = await run_benchmark(records, cases)
    assert report.dataset_size == 3
    assert report.case_count == 1
    assert report.cases[0].candidate_count >= 1
    assert regression_failures(report, {"randomness_rate": 1.0}) == []


@pytest.mark.asyncio
async def test_small_performance_smoke() -> None:
    report = await run_performance_smoke(knowledge_count=20, session_count=3)
    assert report.knowledge_count == 20
    assert report.session_count == 3
    assert report.unique_wonders == report.surfaced_wonders
    assert report.p95_seconds >= 0
