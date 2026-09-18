from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Literal

from pydantic import Field

from wandermind.application.container import in_memory_container
from wandermind.infrastructure.config import Settings
from wandermind.models import KnowledgeItem, KnowledgeType, Seed
from wandermind.models.base import DomainModel


class BenchmarkCase(DomainModel):
    id: str
    seed: str
    label: Literal["obvious", "interesting", "nonsense", "duplicate"]
    domains: list[str] = Field(default_factory=list, min_length=1)
    rationale: str


class CaseResult(DomainModel):
    id: str
    label: str
    session_id: str
    status: str
    stop_reason: str | None
    candidate_count: int
    wonder_count: int
    top_score: float
    operators: list[str]
    wander_path: list[str]
    patch_count: int


class BenchmarkMetrics(DomainModel):
    wonder_hit_proxy: float
    high_value_proxy: float
    obvious_rate: float
    randomness_rate: float
    redundancy_rate: float
    duplicate_rate: float
    cross_domain_yield: float
    average_candidates: float
    runtime_calls: int


class BenchmarkReport(DomainModel):
    dataset_size: int
    case_count: int
    metrics: BenchmarkMetrics
    cases: list[CaseResult]


def load_knowledge_dataset(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"dataset line {line_number} must be an object")
        records.append(value)
    if len(records) < 2:
        raise ValueError("benchmark dataset must contain at least two knowledge items")
    return records


def load_benchmark_cases(path: Path) -> list[BenchmarkCase]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("benchmark case file must contain a JSON array")
    return [BenchmarkCase.model_validate(item) for item in value]


async def run_benchmark(
    knowledge_records: list[dict[str, object]],
    cases: list[BenchmarkCase],
) -> BenchmarkReport:
    settings = Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        auto_create_schema=False,
    )
    container = in_memory_container(settings)
    knowledge: list[KnowledgeItem] = []
    for record in knowledge_records:
        item = await container.ingestion.ingest_text(
            str(record["content"]),
            title=str(record["title"]),
            item_type=KnowledgeType(str(record.get("type", "note"))),
            source="benchmark",
            source_ref=str(record.get("source_ref", "demo://local")),
            metadata={"domain": str(record.get("domain", "general"))},
        )
        knowledge.append(item)

    case_results: list[CaseResult] = []
    all_wonders = []
    all_candidates = []
    for case in cases:
        seed = await container.repositories.seeds.create(
            Seed(content=case.seed, metadata={"benchmark_case_id": case.id})
        )
        result = await container.wander_engine.run(seed)
        all_wonders.extend(result.wonders)
        all_candidates.extend(result.candidates)
        top_score = max(
            (candidate.scores.total for candidate in result.candidates if candidate.scores),
            default=0.0,
        )
        wander_path = [
            str(item_id) for step in result.session.trace.steps for item_id in step.item_ids
        ]
        case_results.append(
            CaseResult(
                id=case.id,
                label=case.label,
                session_id=str(result.session.id),
                status=result.session.status.value,
                stop_reason=result.session.trace.stop_reason,
                candidate_count=len(result.candidates),
                wonder_count=len(result.wonders),
                top_score=top_score,
                operators=result.session.trace.operators,
                wander_path=list(dict.fromkeys(wander_path)),
                patch_count=len(result.session.trace.patches),
            )
        )

    wonder_scores = [wonder.scores for wonder in all_wonders]
    case_by_id = {case.id: case for case in cases}
    interesting_cases = [
        result for result in case_results if case_by_id[result.id].label == "interesting"
    ]
    obvious_cases = [result for result in case_results if case_by_id[result.id].label == "obvious"]
    nonsense_cases = [
        result for result in case_results if case_by_id[result.id].label == "nonsense"
    ]
    duplicate_cases = [
        result for result in case_results if case_by_id[result.id].label == "duplicate"
    ]
    cross_domain_hits = sum(
        bool(result.wonder_count and len(set(case_by_id[result.id].domains)) > 1)
        for result in interesting_cases
    )
    runtime_sessions = await container.repositories.runtime_sessions.list(
        offset=0,
        limit=100_000,
    )
    runtime_calls = sum(
        int(value)
        for session in runtime_sessions
        if isinstance((value := session.cost.get("runtime_calls")), int | float)
    )
    metrics = BenchmarkMetrics(
        wonder_hit_proxy=sum(bool(result.wonder_count) for result in interesting_cases)
        / max(1, len(interesting_cases)),
        high_value_proxy=sum(
            result.wonder_count > 0 and result.top_score >= 0.65 for result in interesting_cases
        )
        / max(1, len(interesting_cases)),
        obvious_rate=sum(bool(result.wonder_count) for result in obvious_cases)
        / max(1, len(obvious_cases)),
        randomness_rate=sum(bool(result.wonder_count) for result in nonsense_cases)
        / max(1, len(nonsense_cases)),
        redundancy_rate=mean(score.redundancy for score in wonder_scores) if wonder_scores else 0.0,
        duplicate_rate=sum(bool(result.wonder_count) for result in duplicate_cases)
        / max(1, len(duplicate_cases)),
        cross_domain_yield=cross_domain_hits / max(1, len(interesting_cases)),
        average_candidates=mean(result.candidate_count for result in case_results),
        runtime_calls=runtime_calls,
    )
    return BenchmarkReport(
        dataset_size=len(knowledge),
        case_count=len(cases),
        metrics=metrics,
        cases=case_results,
    )


def regression_failures(
    report: BenchmarkReport,
    baseline: dict[str, float],
) -> list[str]:
    metrics = report.metrics.model_dump()
    failures = []
    for name, threshold in baseline.items():
        value = float(metrics[name])
        if name in {"randomness_rate", "redundancy_rate", "obvious_rate", "duplicate_rate"}:
            if value > threshold:
                failures.append(f"{name}={value:.3f} exceeds {threshold:.3f}")
        elif value < threshold:
            failures.append(f"{name}={value:.3f} is below {threshold:.3f}")
    return failures
