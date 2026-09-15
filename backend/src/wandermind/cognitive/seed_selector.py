from __future__ import annotations

from wandermind.models import Seed, SeedSource, SeedStatus

SOURCE_PRIORITY = {
    SeedSource.EXPLICIT: 5,
    SeedSource.RECENT: 4,
    SeedSource.UNRESOLVED: 3,
    SeedSource.WEAK_IDEA: 2,
    SeedSource.RANDOM_REVIVAL: 1,
}


class SeedSelector:
    def select(self, seeds: list[Seed]) -> Seed | None:
        eligible = [
            seed for seed in seeds if seed.status in {SeedStatus.PENDING, SeedStatus.ACTIVE}
        ]
        if not eligible:
            return None
        return max(
            eligible,
            key=lambda seed: (SOURCE_PRIORITY[seed.source], seed.priority, seed.created_at),
        )
