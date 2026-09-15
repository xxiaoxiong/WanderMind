from __future__ import annotations

import time
import tracemalloc
from statistics import mean, median

from pydantic import Field

from wandermind.application.container import in_memory_container
from wandermind.infrastructure.config import Settings
from wandermind.models import KnowledgeItem, Seed
from wandermind.models.base import DomainModel


class PerformanceReport(DomainModel):
    knowledge_count: int
    session_count: int
    completed_sessions: int
    surfaced_wonders: int
    unique_wonders: int
    p50_seconds: float = Field(ge=0)
    p95_seconds: float = Field(ge=0)
    mean_seconds: float = Field(ge=0)
    peak_memory_mb: float = Field(ge=0)


async def run_performance_smoke(
    *,
    knowledge_count: int = 1_000,
    session_count: int = 100,
) -> PerformanceReport:
    if knowledge_count < 2 or session_count < 1:
        raise ValueError("performance smoke requires two items and one session")
    settings = Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        auto_create_schema=False,
    )
    container = in_memory_container(settings)
    domains = ["ecology", "software", "cities", "learning", "economics", "biology"]
    for index in range(knowledge_count):
        domain = domains[index % len(domains)]
        content = (
            f"{domain} pattern {index} coordinates distributed resources through feedback, "
            f"delays, thresholds, and adaptation cycle {index % 17}."
        )
        embedding = await container.embedding.embed_text(content)
        await container.repositories.knowledge.create(
            KnowledgeItem(
                title=f"{domain.title()} pattern {index}",
                content=content,
                summary=content,
                topics=[domain, "feedback", f"cycle-{index % 17}"],
                embedding=embedding,
                source="performance-smoke",
                metadata={"domain": domain},
            )
        )

    timings: list[float] = []
    wonder_ids: list[str] = []
    completed = 0
    tracemalloc.start()
    for index in range(session_count):
        seed = await container.repositories.seeds.create(
            Seed(content=f"How does feedback pattern {index % 17} transfer across domains?")
        )
        started = time.perf_counter()
        result = await container.wander_engine.run(seed)
        timings.append(time.perf_counter() - started)
        completed += result.session.status.value == "completed"
        wonder_ids.extend(str(wonder.id) for wonder in result.wonders)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ordered = sorted(timings)
    p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return PerformanceReport(
        knowledge_count=knowledge_count,
        session_count=session_count,
        completed_sessions=completed,
        surfaced_wonders=len(wonder_ids),
        unique_wonders=len(set(wonder_ids)),
        p50_seconds=median(timings),
        p95_seconds=ordered[p95_index],
        mean_seconds=mean(timings),
        peak_memory_mb=peak / 1024 / 1024,
    )
