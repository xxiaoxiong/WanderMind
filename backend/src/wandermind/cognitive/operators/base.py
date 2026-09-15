from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from wandermind.cognitive.association import Association
from wandermind.models import KnowledgeItem, Seed, WonderType
from wandermind.models.base import DomainModel


class OperatorContext(DomainModel):
    seed: Seed
    left: KnowledgeItem
    right: KnowledgeItem
    association: Association


class OperatorResult(DomainModel):
    wonder_type: WonderType
    statement: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    structured: dict[str, Any] = Field(default_factory=dict)
    questions: list[str] = Field(default_factory=list)


class CognitiveOperator(ABC):
    name: str
    input_schema = OperatorContext
    output_schema = OperatorResult

    @abstractmethod
    async def apply(self, context: OperatorContext) -> OperatorResult:
        raise NotImplementedError
