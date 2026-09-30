from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import combinations

from wandermind.application.autopilot_quality import (
    AutopilotQualityPolicy,
    QualityGateResult,
)
from wandermind.application.runtime_summary import RuntimeSummary, summarize_runtime
from wandermind.application.wander_coordinator import WanderCoordinator
from wandermind.cognitive.ingestion import DuplicateKnowledgeError, IngestionService
from wandermind.models import (
    AutopilotCampaign,
    AutopilotStatus,
    KnowledgeEdge,
    KnowledgeItem,
    KnowledgeStatus,
    KnowledgeType,
    RelationType,
    Seed,
    SeedSource,
    SessionStatus,
    WanderBudget,
    WanderSession,
    Wonder,
    WonderStatus,
)
from wandermind.models.base import DomainModel, utc_now
from wandermind.repositories.protocols import RepositoryBundle

logger = logging.getLogger(__name__)

DEFAULT_AUTOPILOT_OBJECTIVE = (
    "持续检查知识场中的隐含假设、矛盾、跨领域机制和二阶后果;产出可验证、"
    "有反证路径且不重复既有成果的高质量新洞见。"
)

EXPLORATION_MODES = (
    "mechanism_transfer",
    "contradiction_hunt",
    "boundary_test",
    "second_order_consequence",
    "counterfactual_stress",
    "multi_scale_synthesis",
)


class AutopilotSnapshot(DomainModel):
    campaign: AutopilotCampaign | None = None
    current_session: WanderSession | None = None
    current_seed: Seed | None = None
    current_runtime: RuntimeSummary
    latest_wonders: list[Wonder]
    knowledge_count: int = 0
    generated_knowledge_count: int = 0
    accepted_generated_knowledge_count: int = 0
    rejected_generated_knowledge_count: int = 0
    worker_running: bool = False


@dataclass(slots=True)
class AutopilotSeedPlanner:
    async def plan(
        self,
        campaign: AutopilotCampaign,
        items: list[KnowledgeItem],
        historical_seeds: list[Seed],
        historical_wonders: list[Wonder],
    ) -> Seed | None:
        active_items = [item for item in items if item.status is KnowledgeStatus.ACTIVE]
        if len(active_items) < 2:
            return None
        pair_attempts = Counter(
            str(seed.metadata.get("pair_key"))
            for seed in historical_seeds
            if seed.metadata.get("autopilot_campaign_id") == str(campaign.id)
            and seed.metadata.get("pair_key")
        )
        ranked_pairs = sorted(
            combinations(active_items, 2),
            key=lambda pair: self._pair_rank(pair, pair_attempts),
        )
        least_attempts = pair_attempts[self._pair_key(ranked_pairs[0])]
        frontier = [
            pair for pair in ranked_pairs if pair_attempts[self._pair_key(pair)] == least_attempts
        ]
        selected = frontier[campaign.cycles_started % len(frontier)]
        mode = EXPLORATION_MODES[campaign.cycles_started % len(EXPLORATION_MODES)]
        previous = sorted(historical_wonders, key=lambda wonder: wonder.created_at, reverse=True)[
            :5
        ]
        content = self._prompt(campaign, selected, mode, previous)
        pair_key = self._pair_key(selected)
        return Seed(
            content=content,
            source=SeedSource.RANDOM_REVIVAL,
            priority=0.95,
            source_item_id=selected[0].id,
            metadata={
                "trigger": "autopilot",
                "autopilot_campaign_id": str(campaign.id),
                "cycle_number": campaign.cycles_started + 1,
                "mode": mode,
                "pair_key": pair_key,
                "paired_item_ids": [str(item.id) for item in selected],
                "pair_attempt": pair_attempts[pair_key] + 1,
            },
        )

    def _pair_rank(
        self,
        pair: tuple[KnowledgeItem, KnowledgeItem],
        attempts: Counter[str],
    ) -> tuple[int, int, float, str]:
        generated_count = sum(item.source == "autopilot" for item in pair)
        mixed_lineage_penalty = abs(generated_count - 1)
        age_gap = abs((pair[0].created_at - pair[1].created_at).total_seconds())
        return (
            attempts[self._pair_key(pair)],
            mixed_lineage_penalty,
            -age_gap,
            self._pair_key(pair),
        )

    def _pair_key(self, pair: tuple[KnowledgeItem, KnowledgeItem]) -> str:
        return ":".join(sorted(str(item.id) for item in pair))

    def _prompt(
        self,
        campaign: AutopilotCampaign,
        pair: tuple[KnowledgeItem, KnowledgeItem],
        mode: str,
        previous: list[Wonder],
    ) -> str:
        prior_context = (
            "\n".join(f"- {wonder.statement[:500]}" for wonder in previous)
            or "- 暂无既有洞见,建立第一条可验证基线。"
        )
        left, right = pair
        return (
            f"长期自主探索目标: {campaign.objective}\n"
            f"当前为第 {campaign.cycles_started + 1} 轮,探索模式: {mode}。\n\n"
            "本轮必须:\n"
            "1. 从下列两项知识中寻找非表面、可证伪的结构机制;\n"
            "2. 同时给出支持证据、反证条件、关键假设和可执行验证问题;\n"
            "3. 主动攻击类比的边界,拒绝仅靠词汇相似的连接;\n"
            "4. 与已有洞见比较,优先修正、反驳或产生二阶推进,而不是复述;\n"
            "5. 只有通过独立审查的结果才能进入长期知识场。\n\n"
            "自动生成内容只是待验证假设,不能作为事实证据或精确数值的来源。\n\n"
            f"知识 A | {_source_label(left)} | {left.title}\n"
            f"{left.summary or left.content[:1000]}\n\n"
            f"知识 B | {_source_label(right)} | {right.title}\n"
            f"{right.summary or right.content[:1000]}\n\n"
            f"最近的高质量洞见:\n{prior_context}"
        )[:20_000]


class AutopilotSupervisor:
    def __init__(
        self,
        repositories: RepositoryBundle,
        coordinator: WanderCoordinator,
        ingestion: IngestionService,
        *,
        configured_runtime: str,
        auto_start: bool,
        objective: str = DEFAULT_AUTOPILOT_OBJECTIVE,
        budget: WanderBudget | None = None,
        poll_interval_seconds: float = 5.0,
        cycle_delay_seconds: float = 5.0,
        promotion_threshold: float = 0.58,
        planner: AutopilotSeedPlanner | None = None,
        quality_policy: AutopilotQualityPolicy | None = None,
    ) -> None:
        self.repositories = repositories
        self.coordinator = coordinator
        self.ingestion = ingestion
        self.configured_runtime = configured_runtime
        self.auto_start = auto_start
        self.objective = objective
        self.budget = budget
        self.poll_interval_seconds = poll_interval_seconds
        self.cycle_delay_seconds = cycle_delay_seconds
        self.promotion_threshold = promotion_threshold
        self.planner = planner or AutopilotSeedPlanner()
        self.quality_policy = quality_policy or AutopilotQualityPolicy()
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self.auto_start and await self._latest_campaign() is None:
            await self.repositories.autopilot_campaigns.create(
                AutopilotCampaign(
                    objective=self.objective,
                    budget=self.budget or WanderBudget(),
                    next_cycle_at=utc_now(),
                    metadata={"auto_started": True},
                )
            )
        await self._reconcile_generated_knowledge()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="wandermind-autopilot")

    async def shutdown(self) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def start_or_resume(
        self,
        *,
        objective: str | None = None,
        budget: WanderBudget | None = None,
    ) -> AutopilotSnapshot:
        async with self._lock:
            campaign = await self._latest_campaign()
            if campaign is None:
                campaign = AutopilotCampaign(
                    objective=objective or self.objective,
                    budget=budget or self.budget or WanderBudget(),
                    next_cycle_at=utc_now(),
                )
                await self.repositories.autopilot_campaigns.create(campaign)
            else:
                if objective:
                    campaign.objective = objective
                if budget:
                    campaign.budget = budget
                campaign.status = AutopilotStatus.ACTIVE
                campaign.next_cycle_at = utc_now()
                campaign.last_error = None
                await self._save(campaign)
            await self._tick_locked()
        return await self.snapshot()

    async def pause(self) -> AutopilotSnapshot:
        await self._set_terminal_control(AutopilotStatus.PAUSED)
        return await self.snapshot()

    async def stop(self) -> AutopilotSnapshot:
        await self._set_terminal_control(AutopilotStatus.STOPPED)
        return await self.snapshot()

    async def tick(self) -> None:
        async with self._lock:
            await self._tick_locked()

    async def snapshot(self) -> AutopilotSnapshot:
        campaign = await self._latest_campaign()
        current_session = None
        current_seed = None
        runtime_sessions = []
        if campaign and campaign.current_session_id:
            current_session = await self.repositories.sessions.get(campaign.current_session_id)
            if current_session:
                current_seed = await self.repositories.seeds.get(current_session.seed_id)
                runtime_sessions = await self.repositories.runtime_sessions.list_for_wander(
                    current_session.id
                )
        knowledge = await self.repositories.knowledge.list(offset=0, limit=10_000)
        active_knowledge = [item for item in knowledge if item.status is KnowledgeStatus.ACTIVE]
        generated_knowledge = [item for item in knowledge if item.source == "autopilot"]
        latest_wonders = await self._campaign_wonders(
            campaign,
            limit=12,
            accepted_only=True,
        )
        return AutopilotSnapshot(
            campaign=campaign,
            current_session=current_session,
            current_seed=current_seed,
            current_runtime=summarize_runtime(self.configured_runtime, runtime_sessions),
            latest_wonders=latest_wonders,
            knowledge_count=len(active_knowledge),
            generated_knowledge_count=len(generated_knowledge),
            accepted_generated_knowledge_count=sum(
                item.status is KnowledgeStatus.ACTIVE for item in generated_knowledge
            ),
            rejected_generated_knowledge_count=sum(
                item.status is KnowledgeStatus.REJECTED for item in generated_knowledge
            ),
            worker_running=self._task is not None and not self._task.done(),
        )

    async def _loop(self) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.exception("autopilot tick failed")
                await self._record_loop_error(error)
            await asyncio.sleep(self.poll_interval_seconds)

    async def _tick_locked(self) -> None:
        campaign = await self._latest_campaign()
        if campaign is None or campaign.status is not AutopilotStatus.ACTIVE:
            return
        if campaign.current_session_id is not None:
            session = await self.repositories.sessions.get(campaign.current_session_id)
            if session is None:
                campaign.current_session_id = None
                campaign.last_error = "current_session_missing"
                campaign.next_cycle_at = utc_now()
                await self._save(campaign)
                return
            if session.status in {SessionStatus.PENDING, SessionStatus.RUNNING}:
                if not self.coordinator.is_active(session.id):
                    self.coordinator.submit(session.id)
                return
            await self._finalize_cycle(campaign, session)
            return
        if campaign.next_cycle_at and campaign.next_cycle_at > utc_now():
            return
        await self._start_cycle(campaign)

    async def _start_cycle(self, campaign: AutopilotCampaign) -> None:
        items = await self.repositories.knowledge.list(offset=0, limit=10_000)
        seeds = await self.repositories.seeds.list(offset=0, limit=10_000)
        wonders = await self._campaign_wonders(
            campaign,
            limit=10_000,
            accepted_only=True,
        )
        seed = await self.planner.plan(campaign, items, seeds, wonders)
        if seed is None:
            campaign.last_error = "insufficient_knowledge"
            campaign.next_cycle_at = utc_now() + timedelta(seconds=60)
            await self._save(campaign)
            return
        await self.repositories.seeds.create(seed)
        session = await self.coordinator.create(
            seed,
            campaign.budget,
            metadata={
                "autopilot_campaign_id": str(campaign.id),
                "autopilot_cycle": campaign.cycles_started + 1,
                "autopilot_mode": seed.metadata["mode"],
            },
        )
        now = utc_now()
        campaign.current_session_id = session.id
        campaign.cycles_started += 1
        campaign.last_cycle_started_at = now
        campaign.next_cycle_at = None
        campaign.last_error = None
        campaign.metadata["current_mode"] = seed.metadata["mode"]
        campaign.metadata["current_pair_key"] = seed.metadata["pair_key"]
        await self._save(campaign, now=now)

    async def _finalize_cycle(
        self,
        campaign: AutopilotCampaign,
        session: WanderSession,
    ) -> None:
        candidates = await self.repositories.candidates.list_for_session(session.id)
        wonders = [
            wonder
            for wonder in await self.repositories.wonders.list(offset=0, limit=10_000)
            if wonder.session_id == session.id
        ]
        runtime_sessions = await self.repositories.runtime_sessions.list_for_wander(session.id)
        runtime = summarize_runtime(self.configured_runtime, runtime_sessions)
        promoted = await self._promote_wonders(campaign, wonders)
        now = utc_now()
        campaign.current_session_id = None
        campaign.cycles_completed += 1
        campaign.total_candidates += len(candidates)
        campaign.total_wonders += len(wonders)
        campaign.total_runtime_calls += runtime.calls
        campaign.promoted_knowledge_count += promoted
        campaign.last_cycle_completed_at = now
        failed = session.status is SessionStatus.FAILED
        campaign.consecutive_failures = campaign.consecutive_failures + 1 if failed else 0
        campaign.last_error = session.trace.stop_reason if failed else None
        delay = self.cycle_delay_seconds
        if failed:
            delay = min(300.0, max(delay, 2**campaign.consecutive_failures * 5.0))
        campaign.next_cycle_at = (
            now + timedelta(seconds=delay) if campaign.status is AutopilotStatus.ACTIVE else None
        )
        campaign.metadata.update(
            {
                "last_session_id": str(session.id),
                "last_stop_reason": session.trace.stop_reason,
                "last_cycle_candidates": len(candidates),
                "last_cycle_wonders": len(wonders),
                "last_cycle_runtime_calls": runtime.calls,
                "last_cycle_promoted_knowledge": promoted,
            }
        )
        await self._save(campaign, now=now)

    async def _promote_wonders(
        self,
        campaign: AutopilotCampaign,
        wonders: list[Wonder],
    ) -> int:
        promoted = 0
        for wonder in wonders:
            if wonder.metadata.get("autopilot_promoted_knowledge_id"):
                continue
            quality = self.quality_policy.evaluate(
                wonder,
                configured_threshold=self.promotion_threshold,
            )
            wonder.metadata["autopilot_quality_gate"] = quality.as_metadata()
            if not quality.accepted:
                wonder.metadata["autopilot_promotion_skipped"] = "quality_gate"
                wonder.status = WonderStatus.INCUBATING
                await self.repositories.wonders.update(wonder)
                continue
            evidence = "\n".join(f"- {value}" for value in wonder.supporting_evidence)
            counter = "\n".join(f"- {value}" for value in wonder.counter_evidence)
            questions = "\n".join(f"- {value}" for value in wonder.questions)
            content = (
                f"洞见: {wonder.statement}\n\n"
                f"解释: {wonder.explanation}\n\n"
                f"支持证据:\n{evidence or '- 尚待补充'}\n\n"
                f"反向证据:\n{counter or '- 尚待补充'}\n\n"
                f"后续验证:\n{questions or '- 尚待补充'}"
            )
            try:
                item = await self.ingestion.ingest_text(
                    content,
                    title=f"自主探索洞见 | {wonder.statement[:120]}",
                    item_type=KnowledgeType.INSIGHT,
                    source="autopilot",
                    source_ref=f"wonder://{wonder.id}",
                    metadata={
                        "autopilot_campaign_id": str(campaign.id),
                        "source_wonder_id": str(wonder.id),
                        "source_session_id": str(wonder.session_id),
                        "quality_score": wonder.scores.total,
                        "epistemic_status": "reviewed_hypothesis",
                        "autopilot_quality_gate": quality.as_metadata(),
                        "runtime_review": wonder.metadata.get("runtime_review"),
                    },
                )
            except DuplicateKnowledgeError as error:
                wonder.metadata["autopilot_promotion_skipped"] = error.reason
                await self.repositories.wonders.update(wonder)
                continue
            item.importance = wonder.scores.total
            item.confidence = wonder.confidence
            await self.repositories.knowledge.update(item)
            for source_id in wonder.source_items:
                if source_id == item.id:
                    continue
                await self.repositories.graph.create(
                    KnowledgeEdge(
                        source_id=item.id,
                        target_id=source_id,
                        relation_type=RelationType.DERIVED_FROM,
                        weight=wonder.scores.total,
                        confidence=wonder.confidence,
                        created_by="autopilot",
                        metadata={"wonder_id": str(wonder.id)},
                    )
                )
            wonder.metadata["autopilot_promoted_knowledge_id"] = str(item.id)
            wonder.metadata["autopilot_campaign_id"] = str(campaign.id)
            await self.repositories.wonders.update(wonder)
            promoted += 1
        return promoted

    async def _set_terminal_control(self, status: AutopilotStatus) -> None:
        async with self._lock:
            campaign = await self._latest_campaign()
            if campaign is None:
                return
            campaign.status = status
            campaign.next_cycle_at = None
            await self._save(campaign)
            if campaign.current_session_id is None:
                return
            await self.coordinator.stop(campaign.current_session_id)
            session = await self.repositories.sessions.get(campaign.current_session_id)
            if session is not None and session.status in {
                SessionStatus.COMPLETED,
                SessionStatus.STOPPED,
                SessionStatus.FAILED,
            }:
                await self._finalize_cycle(campaign, session)

    async def _campaign_wonders(
        self,
        campaign: AutopilotCampaign | None,
        *,
        limit: int,
        accepted_only: bool = False,
    ) -> list[Wonder]:
        if campaign is None:
            return []
        sessions = await self.repositories.sessions.list(offset=0, limit=10_000)
        session_ids = {
            session.id
            for session in sessions
            if session.metadata.get("autopilot_campaign_id") == str(campaign.id)
        }
        wonders = await self.repositories.wonders.list(offset=0, limit=10_000)
        results = [wonder for wonder in wonders if wonder.session_id in session_ids]
        if accepted_only:
            results = [
                wonder
                for wonder in results
                if wonder.status in {WonderStatus.ACTIVE, WonderStatus.SAVED}
                and _quality_gate_accepted(wonder)
            ]
        return results[:limit]

    async def _reconcile_generated_knowledge(self) -> None:
        knowledge = await self.repositories.knowledge.list(offset=0, limit=10_000)
        generated = [item for item in knowledge if item.source == "autopilot"]
        if not generated:
            return
        wonders = await self.repositories.wonders.list(offset=0, limit=10_000)
        wonder_by_id = {str(wonder.id): wonder for wonder in wonders}
        accepted = 0
        rejected = 0
        for item in generated:
            source_wonder_id = item.metadata.get("source_wonder_id")
            wonder = wonder_by_id.get(str(source_wonder_id))
            quality = (
                self.quality_policy.evaluate(
                    wonder,
                    configured_threshold=self.promotion_threshold,
                )
                if wonder is not None
                else QualityGateResult(False, ("source_wonder_missing",))
            )
            item.metadata["autopilot_quality_gate"] = quality.as_metadata()
            if quality.accepted:
                accepted += 1
                item.metadata["epistemic_status"] = "reviewed_hypothesis"
            else:
                rejected += 1
                item.status = KnowledgeStatus.REJECTED
                item.metadata["epistemic_status"] = "quality_rejected"
                item.metadata["autopilot_quality_rejected_at"] = utc_now().isoformat()
            await self.repositories.knowledge.update(item)
            if wonder is None:
                continue
            wonder.metadata["autopilot_quality_gate"] = quality.as_metadata()
            if not quality.accepted:
                wonder.status = WonderStatus.INCUBATING
                wonder.metadata["autopilot_promotion_retracted"] = True
            await self.repositories.wonders.update(wonder)
        campaign = await self._latest_campaign()
        if campaign is not None:
            campaign.metadata["quality_gate_version"] = 1
            campaign.metadata["active_generated_knowledge"] = accepted
            campaign.metadata["rejected_generated_knowledge"] = rejected
            await self._save(campaign)

    async def _latest_campaign(self) -> AutopilotCampaign | None:
        campaigns = await self.repositories.autopilot_campaigns.list(offset=0, limit=1)
        return campaigns[0] if campaigns else None

    async def _save(
        self,
        campaign: AutopilotCampaign,
        *,
        now: datetime | None = None,
    ) -> None:
        campaign.updated_at = now or datetime.now(UTC)
        await self.repositories.autopilot_campaigns.update(campaign)

    async def _record_loop_error(self, error: Exception) -> None:
        campaign = await self._latest_campaign()
        if campaign is None:
            return
        campaign.last_error = f"{type(error).__name__}: {str(error)[:1_500]}"
        campaign.consecutive_failures += 1
        campaign.next_cycle_at = utc_now() + timedelta(
            seconds=min(300, 2 ** min(campaign.consecutive_failures, 6) * 5)
        )
        await self._save(campaign)


def _quality_gate_accepted(wonder: Wonder) -> bool:
    value = wonder.metadata.get("autopilot_quality_gate")
    return isinstance(value, dict) and value.get("accepted") is True


def _source_label(item: KnowledgeItem) -> str:
    return "待验证自动生成假设" if item.source == "autopilot" else "原始知识"
