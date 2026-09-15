from __future__ import annotations

from wandermind.cognitive.association import AssociationType
from wandermind.cognitive.operators.base import CognitiveOperator, OperatorContext


class OperatorSelector:
    def __init__(self, operators: list[CognitiveOperator]) -> None:
        self.operators = {operator.name: operator for operator in operators}
        if not self.operators:
            raise ValueError("at least one cognitive operator is required")

    def select(
        self, context: OperatorContext, previous: list[str] | None = None
    ) -> CognitiveOperator:
        previous_names = set(previous or [])
        preferred = self._preferred(context)
        for name in preferred:
            if name in self.operators and name not in previous_names:
                return self.operators[name]
        for operator in self.operators.values():
            if operator.name not in previous_names:
                return operator
        return (
            self.operators[preferred[0]]
            if preferred[0] in self.operators
            else next(iter(self.operators.values()))
        )

    def _preferred(self, context: OperatorContext) -> list[str]:
        association_type = context.association.type
        if association_type is AssociationType.CONTRADICTION:
            return ["counterfactual", "inversion", "abstraction"]
        if association_type is AssociationType.CAUSAL_CANDIDATE:
            return ["second_order", "counterfactual", "abstraction"]
        if association_type is AssociationType.SHARED_PATTERN:
            return ["abstraction", "conceptual_blend", "analogy"]
        if association_type is AssociationType.ANALOGY_CANDIDATE:
            return ["analogy", "conceptual_blend", "inversion"]
        return ["conceptual_blend", "analogy", "abstraction"]
