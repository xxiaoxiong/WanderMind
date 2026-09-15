from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from wandermind.cognitive.engine import WanderEngine
from wandermind.infrastructure.observability import record_wander_run
from wandermind.models import KnowledgeItem, Seed, SeedSource, Wonder, WonderStatus
from wandermind.repositories.protocols import RepositoryBundle


class IncubationSampler:
    def __init__(self, *, sample_size: int = 6) -> None:
        if sample_size < 2:
            raise ValueError("incubation sample size must be at least 2")
        self.sample_size = sample_size

    def sample(self, items: list[KnowledgeItem]) -> list[KnowledgeItem]:
        ordered = sorted(items, key=lambda item: item.created_at)
        if len(ordered) <= self.sample_size:
            return ordered
        half = self.sample_size // 2
        old = ordered[:half]
        recent = ordered[-(self.sample_size - half) :]
        return old + [item for item in recent if item.id not in {value.id for value in old}]

    def pair(
        self,
        items: list[KnowledgeItem],
        *,
        excluded_pairs: set[frozenset[object]] | None = None,
    ) -> tuple[KnowledgeItem, KnowledgeItem] | None:
        if len(items) < 2:
            return None
        ordered = sorted(items, key=lambda item: item.created_at)
        excluded = excluded_pairs or set()
        for recent in reversed(ordered):
            for old in ordered:
                pair_ids = frozenset((recent.id, old.id))
                if recent.id != old.id and pair_ids not in excluded:
                    return recent, old
        return None


class IncubationService:
    def __init__(
        self,
        repositories: RepositoryBundle,
        engine: WanderEngine,
        sampler: IncubationSampler | None = None,
    ) -> None:
        self.repositories = repositories
        self.engine = engine
        self.sampler = sampler or IncubationSampler()

    async def run(self, *, trigger: str = "manual") -> Wonder | None:
        items = await self.repositories.knowledge.list(offset=0, limit=10_000)
        sampled = self.sampler.sample(items)
        historical = await self.repositories.wonders.list(offset=0, limit=10_000)
        excluded_pairs: set[frozenset[object]] = {
            frozenset(wonder.source_items) for wonder in historical
        }
        pair = self.sampler.pair(sampled, excluded_pairs=excluded_pairs)
        if pair is None:
            return None
        recent, old = pair
        seed = Seed(
            content=f"What becomes visible when {recent.title} is paired with older knowledge: {old.title}?",
            source=SeedSource.RANDOM_REVIVAL,
            priority=0.35,
            metadata={"trigger": trigger, "paired_item_ids": [str(recent.id), str(old.id)]},
        )
        await self.repositories.seeds.create(seed)
        result = await self.engine.run(seed)
        record_wander_run(result.session, result.candidates, result.wonders)
        if not result.wonders:
            return None
        return result.wonders[0]


class ReWonderService:
    def __init__(self, repositories: RepositoryBundle, engine: WanderEngine) -> None:
        self.repositories = repositories
        self.engine = engine

    async def run(self, wonder: Wonder, *, trigger: str = "user_request") -> Wonder | None:
        knowledge = await self.repositories.knowledge.list(offset=0, limit=10_000)
        fresh = next((item for item in knowledge if item.id not in set(wonder.source_items)), None)
        if fresh is None:
            return None
        seed = Seed(
            content=f"Reconsider this prior wonder with new knowledge: {wonder.statement} / {fresh.title}",
            source=SeedSource.WEAK_IDEA,
            priority=0.8,
            metadata={"trigger": trigger, "parent_wonder_id": str(wonder.id)},
        )
        await self.repositories.seeds.create(seed)
        result = await self.engine.run(seed)
        record_wander_run(result.session, result.candidates, result.wonders)
        if not result.wonders:
            return None
        child = result.wonders[0]
        child.parent_wonder_id = wonder.id
        await self.repositories.wonders.update(child)
        wonder.status = WonderStatus.SUPERSEDED
        wonder.metadata["child_wonder_id"] = str(child.id)
        await self.repositories.wonders.update(wonder)
        return child


class IncubationScheduler:
    def __init__(self, service: IncubationService, *, interval_minutes: int = 360) -> None:
        self.service = service
        self.interval_minutes = interval_minutes
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        if self.scheduler.running:
            return
        self.scheduler.add_job(
            self.service.run,
            trigger="interval",
            minutes=self.interval_minutes,
            kwargs={"trigger": "scheduled"},
            id="wandermind-incubation",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
