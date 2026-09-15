from wandermind.cognitive.operators.abstraction import AbstractionOperator
from wandermind.cognitive.operators.analogy import AnalogyOperator
from wandermind.cognitive.operators.base import CognitiveOperator, OperatorContext, OperatorResult
from wandermind.cognitive.operators.blend import ConceptualBlendOperator
from wandermind.cognitive.operators.counterfactual import CounterfactualOperator
from wandermind.cognitive.operators.inversion import InversionOperator
from wandermind.cognitive.operators.second_order import SecondOrderConsequenceOperator
from wandermind.cognitive.operators.selector import OperatorSelector


def default_operators() -> list[CognitiveOperator]:
    return [
        AnalogyOperator(),
        ConceptualBlendOperator(),
        CounterfactualOperator(),
        InversionOperator(),
        AbstractionOperator(),
        SecondOrderConsequenceOperator(),
    ]


__all__ = [
    "AbstractionOperator",
    "AnalogyOperator",
    "CognitiveOperator",
    "ConceptualBlendOperator",
    "CounterfactualOperator",
    "InversionOperator",
    "OperatorContext",
    "OperatorResult",
    "OperatorSelector",
    "SecondOrderConsequenceOperator",
    "default_operators",
]
