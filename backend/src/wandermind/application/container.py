from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from wandermind.application.candidate_runtime_service import (
    CandidateReviewOutput,
    CandidateSynthesisOutput,
    RuntimeCandidateReviewer,
    RuntimeCandidateSynthesizer,
)
from wandermind.application.deletion_service import DataDeletionService
from wandermind.application.evaluation import (
    CriticOutput,
    CriticVerdict,
    EvidenceOutput,
    ExplorerOutput,
)
from wandermind.application.explore_service import (
    CriticService,
    DeepEvaluationService,
    EvidenceService,
    ExplorerService,
)
from wandermind.application.graph_service import IdeaGraphService
from wandermind.application.incubation_service import (
    IncubationScheduler,
    IncubationService,
    ReWonderService,
)
from wandermind.application.wonder_service import FeedbackService, WonderPromotionService
from wandermind.cognitive.embedding import HashEmbeddingAdapter
from wandermind.cognitive.engine import WanderEngine
from wandermind.cognitive.ingestion import IngestionService
from wandermind.cognitive.operators import OperatorSelector, default_operators
from wandermind.cognitive.scoring import ScoreWeights, ThresholdPolicy, WonderScorer
from wandermind.infrastructure.config import Settings
from wandermind.infrastructure.database import create_engine, create_session_factory
from wandermind.infrastructure.tracked_runtime import TrackedRuntimeAdapter
from wandermind.repositories import InMemoryRepositoryBundle, SQLAlchemyRepositoryBundle
from wandermind.repositories.protocols import RepositoryBundle
from wandermind.runtime import (
    AgentRuntimeAdapter,
    CodexRuntimeAdapter,
    MockRuntimeAdapter,
    OpenAICompatibleRuntimeAdapter,
)


@dataclass(slots=True)
class ApplicationContainer:
    settings: Settings
    repositories: RepositoryBundle
    embedding: HashEmbeddingAdapter
    ingestion: IngestionService
    wander_engine: WanderEngine
    runtime: AgentRuntimeAdapter
    deep_evaluation: DeepEvaluationService
    promotion: WonderPromotionService
    feedback: FeedbackService
    deletion: DataDeletionService
    graph: IdeaGraphService
    incubation: IncubationService
    rewonder: ReWonderService
    scheduler: IncubationScheduler
    database_engine: AsyncEngine | None = None


def build_container(
    settings: Settings,
    *,
    repositories: RepositoryBundle | None = None,
    runtime: AgentRuntimeAdapter | None = None,
) -> ApplicationContainer:
    database_engine: AsyncEngine | None = None
    if repositories is None:
        database_engine = create_engine(settings.database_url)
        selected_repositories: RepositoryBundle = SQLAlchemyRepositoryBundle(
            create_session_factory(database_engine)
        )
    else:
        selected_repositories = repositories
    embedding = HashEmbeddingAdapter(settings.embedding_dimensions)
    scorer = WonderScorer(
        embedding,
        weights=ScoreWeights.model_validate(settings.score_weights),
        thresholds=ThresholdPolicy(
            explore_above=settings.cheap_score_threshold,
            surface_above=settings.wonder_threshold,
        ),
    )
    runtime_delegate = runtime or _build_runtime(settings)
    selected_runtime = TrackedRuntimeAdapter(
        runtime_delegate,
        selected_repositories.runtime_sessions,
    )
    deep_evaluation = DeepEvaluationService(
        ExplorerService(
            selected_runtime,
            max_retries=settings.runtime_max_retries,
            timeout_seconds=settings.runtime_timeout_seconds,
        ),
        EvidenceService(
            selected_runtime,
            max_retries=settings.runtime_max_retries,
            timeout_seconds=settings.runtime_timeout_seconds,
        ),
        CriticService(
            selected_runtime,
            max_retries=settings.runtime_max_retries,
            timeout_seconds=settings.runtime_timeout_seconds,
        ),
    )
    wander_engine = WanderEngine(
        selected_repositories,
        embedding,
        OperatorSelector(default_operators()),
        scorer,
        candidate_synthesizer=RuntimeCandidateSynthesizer(
            selected_runtime,
            max_retries=settings.runtime_max_retries,
            timeout_seconds=settings.runtime_timeout_seconds,
        ),
        candidate_reviewer=RuntimeCandidateReviewer(
            selected_runtime,
            max_retries=settings.runtime_max_retries,
            timeout_seconds=settings.runtime_timeout_seconds,
        ),
    )
    incubation = IncubationService(selected_repositories, wander_engine)
    return ApplicationContainer(
        settings=settings,
        repositories=selected_repositories,
        embedding=embedding,
        ingestion=IngestionService(selected_repositories.knowledge, embedding),
        wander_engine=wander_engine,
        runtime=selected_runtime,
        deep_evaluation=deep_evaluation,
        promotion=WonderPromotionService(
            selected_repositories, threshold=settings.wonder_threshold
        ),
        feedback=FeedbackService(selected_repositories),
        deletion=DataDeletionService(selected_repositories),
        graph=IdeaGraphService(selected_repositories),
        incubation=incubation,
        rewonder=ReWonderService(selected_repositories, wander_engine),
        scheduler=IncubationScheduler(
            incubation,
            interval_minutes=settings.incubation_interval_minutes,
        ),
        database_engine=database_engine,
    )


def in_memory_container(settings: Settings | None = None) -> ApplicationContainer:
    selected_settings = settings or Settings(
        env="test", database_url="sqlite+aiosqlite:///:memory:"
    )
    return build_container(selected_settings, repositories=InMemoryRepositoryBundle())


def _build_runtime(settings: Settings) -> AgentRuntimeAdapter:
    if settings.runtime_adapter == "codex":
        return CodexRuntimeAdapter(
            executable=settings.codex_executable,
            cwd=settings.runtime_cwd,
            allow_workspace_write=False,
        )
    if settings.runtime_adapter == "openai":
        if settings.llm_api_key is None or not settings.llm_api_key.get_secret_value():
            raise ValueError("WANDERMIND_LLM_API_KEY is required for the OpenAI runtime")
        return OpenAICompatibleRuntimeAdapter(
            base_url=settings.llm_base_url,
            credential=settings.llm_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
        )
    return MockRuntimeAdapter(
        responses={
            "candidate_synthesis": CandidateSynthesisOutput(
                statement=(
                    "Decentralized systems can limit overload by turning local saturation signals "
                    "into admission control before capacity collapses."
                ),
                explanation=(
                    "The source domains share a feedback structure: individual workers expose "
                    "local capacity signals, while the wider system slows or redirects incoming "
                    "work. The connection is testable by measuring whether earlier local feedback "
                    "reduces queue growth without central coordination."
                ),
                assumptions=["Local capacity signals are observable before system-wide failure."],
                implications=["Admission thresholds can be tuned from local feedback latency."],
                questions=["Does earlier local backpressure reduce peak queue depth?"],
            ).model_dump(mode="json"),
            "candidate_review": CandidateReviewOutput(
                expanded_idea=(
                    "Treat the connection as a falsifiable control hypothesis: earlier local "
                    "saturation signals should reduce peak queue depth without centralized routing."
                ),
                supporting_evidence=[
                    "Both knowledge items describe local feedback changing system-wide allocation."
                ],
                counter_evidence=[
                    "Domain-specific delays may make the control loops behave differently."
                ],
                source_refs=[],
                uncertainty=0.9,
                weaknesses=["The transfer still requires an operational comparison."],
                obviousness=0.2,
                factual_risk=0.3,
                alternative_explanations=[
                    "The overlap may reflect generic resource-allocation language."
                ],
                verdict="pass",
            ).model_dump(mode="json"),
            "explorer": ExplorerOutput(
                expanded_idea="The connection can be explored as a testable structural analogy.",
                implications=[
                    "The shared allocation mechanism may create comparable failure modes."
                ],
                follow_up_questions=["Which shared mechanism can be measured first?"],
                possible_support=["Compare observed feedback loops in both source domains."],
                possible_failure_modes=["The analogy may ignore domain-specific constraints."],
            ).model_dump(mode="json"),
            "evidence": EvidenceOutput(
                source_refs=[],
                uncertainty=0.9,
            ).model_dump(mode="json"),
            "critic": CriticOutput(
                weakness=["Evidence is currently limited to the local knowledge base."],
                obviousness=0.2,
                over_analogy=False,
                factual_risk=0.35,
                alternative_explanation=[
                    "The overlap may come from generic resource-allocation language."
                ],
                verdict=CriticVerdict.PASS,
            ).model_dump(mode="json"),
        }
    )
