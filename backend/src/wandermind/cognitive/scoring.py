from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from wandermind.cognitive.association import Association
from wandermind.cognitive.embedding import EmbeddingAdapter
from wandermind.cognitive.operators import OperatorResult
from wandermind.cognitive.text import jaccard_similarity, normalize_text, significant_tokens
from wandermind.models import (
    Candidate,
    Feedback,
    FeedbackAction,
    KnowledgeItem,
    Seed,
    Wonder,
    WonderScores,
)
from wandermind.models.base import DomainModel


class ScoreDetail(DomainModel):
    value: float = Field(ge=0.0, le=1.0)
    reason: str


class ScoreExplanation(DomainModel):
    dimensions: dict[str, ScoreDetail]
    penalties: dict[str, ScoreDetail]
    total: float = Field(ge=0.0, le=1.0)


class ThresholdDecision(StrEnum):
    REJECT = "reject"
    KEEP_CANDIDATE = "keep_candidate"
    DEEP_EXPLORE = "deep_explore"
    SURFACE = "surface"


class ScoreWeights(DomainModel):
    novelty: float = Field(default=0.18, ge=0.0, le=1.0)
    surprise: float = Field(default=0.12, ge=0.0, le=1.0)
    personal_relevance: float = Field(default=0.18, ge=0.0, le=1.0)
    coherence: float = Field(default=0.12, ge=0.0, le=1.0)
    generativity: float = Field(default=0.14, ge=0.0, le=1.0)
    explanatory_power: float = Field(default=0.10, ge=0.0, le=1.0)
    evidence_potential: float = Field(default=0.08, ge=0.0, le=1.0)
    cross_domain_value: float = Field(default=0.08, ge=0.0, le=1.0)
    redundancy_penalty: float = Field(default=0.12, ge=0.0, le=1.0)
    arbitrariness_penalty: float = Field(default=0.10, ge=0.0, le=1.0)
    hallucination_risk_penalty: float = Field(default=0.15, ge=0.0, le=1.0)


class ThresholdPolicy(DomainModel):
    reject_below: float = Field(default=0.25, ge=0.0, le=1.0)
    explore_above: float = Field(default=0.45, ge=0.0, le=1.0)
    surface_above: float = Field(default=0.58, ge=0.0, le=1.0)

    def decide(self, score: float) -> ThresholdDecision:
        if score < self.reject_below:
            return ThresholdDecision.REJECT
        if score >= self.surface_above:
            return ThresholdDecision.SURFACE
        if score >= self.explore_above:
            return ThresholdDecision.DEEP_EXPLORE
        return ThresholdDecision.KEEP_CANDIDATE


class WonderScorer:
    def __init__(
        self,
        embedding: EmbeddingAdapter,
        *,
        weights: ScoreWeights | None = None,
        thresholds: ThresholdPolicy | None = None,
    ) -> None:
        self.embedding = embedding
        self.weights = weights or ScoreWeights()
        self.thresholds = thresholds or ThresholdPolicy()

    async def score(
        self,
        candidate: Candidate,
        result: OperatorResult,
        seed: Seed,
        source_items: list[KnowledgeItem],
        association: Association,
        historical_wonders: list[Wonder],
        knowledge_items: list[KnowledgeItem] | None = None,
        feedback_history: list[tuple[Wonder, Feedback]] | None = None,
    ) -> tuple[WonderScores, ScoreExplanation, ThresholdDecision]:
        source_text = " ".join(
            f"{item.title} {item.summary or item.content}" for item in source_items
        )
        candidate_text = f"{candidate.statement} {candidate.explanation}"
        source_similarity = jaccard_similarity(candidate_text, source_text)
        seed_similarity = jaccard_similarity(candidate_text, seed.content)
        seed_source_similarity = jaccard_similarity(seed.content, source_text)
        source_anchor_coverage = _source_anchor_coverage(seed.content, source_items)
        feedback_interest = _feedback_interest(
            seed.content,
            source_items,
            feedback_history or [],
        )
        historical_similarity = max(
            (
                _historical_similarity(candidate, candidate_text, wonder)
                for wonder in historical_wonders
            ),
            default=0.0,
        )
        novelty = _clamp(0.65 + 0.35 * association.distance - 0.45 * historical_similarity)
        surprise = _clamp(1.0 - abs(association.distance - 0.65) / 0.65)
        personal_relevance = _clamp(
            0.35
            + 0.50 * max(seed_similarity, source_similarity * 0.5)
            + 0.15 * source_anchor_coverage
            + 0.12 * feedback_interest
        )
        coherence = _clamp(
            0.45 + 0.45 * association.strength + 0.10 * (len(result.explanation) > 80)
        )
        question_count = len(result.questions)
        generativity = _clamp(
            0.35 + min(0.45, question_count * 0.18) + 0.20 * _has_future_terms(candidate_text)
        )
        explanatory_power = _clamp(
            0.40 + min(0.35, len(result.explanation) / 800) + 0.25 * association.strength
        )
        evidence_potential = _clamp(
            0.35 + 0.20 * question_count + 0.20 * _has_testable_terms(candidate_text)
        )
        source_topics = {topic for item in source_items for topic in item.topics}
        cross_domain_value = _clamp(
            0.30 + 0.18 * len(source_topics) + 0.30 * (association.distance > 0.45)
        )
        direct_restatement = _is_direct_restatement(
            seed.content,
            knowledge_items or source_items,
        )
        redundancy = _clamp(
            max(
                historical_similarity,
                seed_source_similarity,
                _has_obviousness_markers(seed.content),
                direct_restatement,
            )
        )
        arbitrariness = _clamp(
            max(
                1.0 - association.strength,
                0.8 * _has_obviousness_markers(seed.content),
                has_arbitrary_framing(seed.content),
            )
        )
        hallucination_risk = _clamp(
            0.15
            + 0.85 * _has_absolute_claims(f"{seed.content} {candidate_text}")
            - 0.1 * question_count
        )
        positive = (
            self.weights.novelty * novelty
            + self.weights.surprise * surprise
            + self.weights.personal_relevance * personal_relevance
            + self.weights.coherence * coherence
            + self.weights.generativity * generativity
            + self.weights.explanatory_power * explanatory_power
            + self.weights.evidence_potential * evidence_potential
            + self.weights.cross_domain_value * cross_domain_value
        )
        penalties = (
            self.weights.redundancy_penalty * redundancy
            + self.weights.arbitrariness_penalty * arbitrariness
            + self.weights.hallucination_risk_penalty * hallucination_risk
        )
        total = _clamp(positive - penalties)
        scores = WonderScores(
            novelty=novelty,
            surprise=surprise,
            personal_relevance=personal_relevance,
            coherence=coherence,
            generativity=generativity,
            explanatory_power=explanatory_power,
            evidence_potential=evidence_potential,
            cross_domain_value=cross_domain_value,
            redundancy=redundancy,
            arbitrariness=arbitrariness,
            hallucination_risk=hallucination_risk,
            total=total,
        )
        explanation = ScoreExplanation(
            dimensions={
                "novelty": ScoreDetail(
                    value=novelty, reason="semantic distance minus historical overlap"
                ),
                "surprise": ScoreDetail(value=surprise, reason="rewarded semantic sweet spot"),
                "personal_relevance": ScoreDetail(
                    value=personal_relevance,
                    reason="seed/source anchors plus explicit feedback topic overlap",
                ),
                "coherence": ScoreDetail(
                    value=coherence, reason="association strength and explanation quality"
                ),
                "generativity": ScoreDetail(
                    value=generativity, reason="follow-up questions and implications"
                ),
                "explanatory_power": ScoreDetail(
                    value=explanatory_power, reason="bridge clarity and detail"
                ),
                "evidence_potential": ScoreDetail(
                    value=evidence_potential, reason="testability signals"
                ),
                "cross_domain_value": ScoreDetail(
                    value=cross_domain_value, reason="topic diversity and distance"
                ),
            },
            penalties={
                "redundancy": ScoreDetail(
                    value=redundancy, reason="similarity to historical wonders"
                ),
                "arbitrariness": ScoreDetail(
                    value=arbitrariness, reason="weak structural association"
                ),
                "hallucination_risk": ScoreDetail(
                    value=hallucination_risk, reason="unsupported absolute claims"
                ),
            },
            total=total,
        )
        decision = self.thresholds.decide(total)
        if decision is ThresholdDecision.SURFACE and (
            redundancy >= 0.85 or arbitrariness >= 0.8 or hallucination_risk >= 0.75
        ):
            decision = ThresholdDecision.DEEP_EXPLORE
        return scores, explanation, decision


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _has_future_terms(text: str) -> float:
    terms = set(significant_tokens(text))
    return float(
        bool(terms & {"prediction", "implication", "future", "direction", "预测", "影响", "方向"})
    )


def _has_testable_terms(text: str) -> float:
    terms = set(significant_tokens(text))
    return float(
        bool(terms & {"test", "measure", "evidence", "prediction", "验证", "衡量", "证据"})
    )


def _has_absolute_claims(text: str) -> float:
    lowered = text.casefold()
    return float(
        any(
            marker in lowered
            for marker in (
                "always",
                "never",
                "prove",
                "proves",
                "directly causes",
                "必然",
                "总是",
                "证明",
            )
        )
    )


def _has_obviousness_markers(text: str) -> float:
    lowered = text.casefold()
    markers = (
        "at the most generic level",
        "are similar to",
        "is similar to itself",
        "最泛化的层面",
        "和自己相似",
    )
    return float(any(marker in lowered for marker in markers))


def has_arbitrary_framing(text: str) -> float:
    lowered = text.casefold()
    markers = (
        "secretly",
        "magically",
        "randomly proves",
        "without any evidence",
        "神秘地",
        "魔法般",
        "毫无依据",
    )
    return float(any(marker in lowered for marker in markers))


def _is_direct_restatement(seed_text: str, source_items: list[KnowledgeItem]) -> float:
    normalized_seed = normalize_text(seed_text).casefold()
    bridge_markers = (
        "analogy",
        "analogue",
        "between",
        "compare",
        "inform",
        "inspired",
        "model for",
        "resemble",
        "similarity",
        "teach",
        "transfer",
        "借鉴",
        "启发",
        "联系",
        "类比",
        "比较",
    )
    if any(marker in normalized_seed for marker in bridge_markers):
        return 0.0
    direct_question = normalized_seed.startswith(
        ("how does ", "why does ", "what is ", "explain ", "如何", "为什么", "什么是")
    )
    if not direct_question:
        return 0.0
    for item in source_items:
        concept_title = normalize_text(item.title.rsplit(":", maxsplit=1)[-1]).casefold()
        if len(concept_title) >= 4 and concept_title in normalized_seed:
            return 0.95
    return 0.0


def _source_anchor_coverage(seed_text: str, source_items: list[KnowledgeItem]) -> float:
    if not source_items:
        return 0.0
    normalized_seed = normalize_text(seed_text).casefold()
    matched = 0
    for item in source_items:
        concept_title = normalize_text(item.title.rsplit(":", maxsplit=1)[-1]).casefold()
        matched += int(len(concept_title) >= 4 and concept_title in normalized_seed)
    return matched / len(source_items)


def _historical_similarity(candidate: Candidate, candidate_text: str, wonder: Wonder) -> float:
    lexical_similarity = jaccard_similarity(
        candidate_text,
        f"{wonder.statement} {wonder.explanation}",
    )
    candidate_sources = set(candidate.source_items)
    wonder_sources = set(wonder.source_items)
    source_union = candidate_sources | wonder_sources
    source_overlap = (
        len(candidate_sources & wonder_sources) / len(source_union) if source_union else 0.0
    )
    return lexical_similarity * (0.35 + 0.65 * source_overlap)


def _feedback_interest(
    seed_text: str,
    source_items: list[KnowledgeItem],
    feedback_history: list[tuple[Wonder, Feedback]],
) -> float:
    current_text = " ".join(
        [seed_text] + [f"{item.title} {' '.join(item.topics)}" for item in source_items]
    )
    positive_actions = {
        FeedbackAction.INTERESTING,
        FeedbackAction.VERY_INTERESTING,
        FeedbackAction.SAVE,
        FeedbackAction.SAVE_FOR_LATER,
        FeedbackAction.CONTINUE,
        FeedbackAction.CONTINUE_EXPLORE,
        FeedbackAction.INSPIRED_NEW_IDEA,
    }
    negative_actions = {
        FeedbackAction.NOT_INTERESTING,
        FeedbackAction.ALREADY_KNEW,
        FeedbackAction.OBVIOUS,
        FeedbackAction.RANDOM,
        FeedbackAction.TOO_RANDOM,
        FeedbackAction.WRONG,
        FeedbackAction.IRRELEVANT,
    }
    weighted_overlap = 0.0
    overlap_total = 0.0
    for wonder, feedback in feedback_history:
        overlap = jaccard_similarity(current_text, f"{wonder.statement} {wonder.explanation}")
        if overlap == 0.0:
            continue
        direction = 0.0
        if feedback.action in positive_actions:
            direction = 1.0
        elif feedback.action in negative_actions:
            direction = -1.0
        weighted_overlap += direction * overlap
        overlap_total += overlap
    if overlap_total == 0.0:
        return 0.0
    return max(-1.0, min(1.0, weighted_overlap / overlap_total))
