from enum import StrEnum


class KnowledgeType(StrEnum):
    NOTE = "note"
    CONCEPT = "concept"
    FACT = "fact"
    DOCUMENT = "document"
    QUESTION = "question"
    HYPOTHESIS = "hypothesis"
    IDEA = "idea"
    INSIGHT = "insight"
    EVIDENCE = "evidence"


class KnowledgeStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class RelationType(StrEnum):
    SIMILAR_TO = "similar_to"
    CONTRADICTS = "contradicts"
    CAUSES = "causes"
    DERIVED_FROM = "derived_from"
    ANALOGY_OF = "analogy_of"
    INSPIRED_BY = "inspired_by"
    EVIDENCE_FOR = "evidence_for"
    EVIDENCE_AGAINST = "evidence_against"
    COMBINES_WITH = "combines_with"
    ABSTRACTS = "abstracts"
    INSTANTIATES = "instantiates"
    QUESTIONS = "questions"
    EVOLVES_FROM = "evolves_from"


class SeedSource(StrEnum):
    EXPLICIT = "explicit"
    RECENT = "recent"
    UNRESOLVED = "unresolved"
    WEAK_IDEA = "weak_idea"
    RANDOM_REVIVAL = "random_revival"


class SeedStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    USED = "used"
    ARCHIVED = "archived"


class WonderType(StrEnum):
    SPARK = "spark"
    QUESTION = "question"
    CONNECTION = "connection"
    HYPOTHESIS = "hypothesis"
    INSIGHT = "insight"


class CandidateStatus(StrEnum):
    GENERATED = "generated"
    FILTERED = "filtered"
    PROMISING = "promising"
    EXPLORED = "explored"
    REJECTED = "rejected"
    PROMOTED = "promoted"


class WonderStatus(StrEnum):
    ACTIVE = "active"
    SAVED = "saved"
    DISMISSED = "dismissed"
    INCUBATING = "incubating"
    SUPERSEDED = "superseded"


class FeedbackAction(StrEnum):
    INTERESTING = "interesting"
    VERY_INTERESTING = "very_interesting"
    NOT_INTERESTING = "not_interesting"
    ALREADY_KNEW = "already_knew"
    SAVE = "save"
    SAVE_FOR_LATER = "save_for_later"
    CONTINUE = "continue"
    CONTINUE_EXPLORE = "continue_explore"
    OBVIOUS = "obvious"
    RANDOM = "random"
    TOO_RANDOM = "too_random"
    WRONG = "wrong"
    IRRELEVANT = "irrelevant"
    INSPIRED_NEW_IDEA = "inspired_new_idea"


class CognitiveState(StrEnum):
    IDLE = "idle"
    SEEDING = "seeding"
    WANDER = "wander"
    COLLISION = "collision"
    GENERATE = "generate"
    SCORE = "score"
    EXPLORE = "explore"
    CRITIQUE = "critique"
    PERSIST = "persist"
    SURFACE = "surface"
    STOPPED = "stopped"
    FAILED = "failed"


class SessionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class RuntimeSessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CLOSED = "closed"
