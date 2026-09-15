from wandermind.cognitive.operators.base import CognitiveOperator, OperatorContext, OperatorResult
from wandermind.models import WonderType


class CounterfactualOperator(CognitiveOperator):
    name = "counterfactual"

    async def apply(self, context: OperatorContext) -> OperatorResult:
        assumption = f"{context.left.title} must preserve its current organizing principle"
        counterfactual = (
            f"{context.left.title} instead adopts the organizing principle of {context.right.title}"
        )
        consequences = [
            "Existing optimization targets may become secondary.",
            "New coordination costs and opportunities would appear.",
            "Previously invisible stakeholders may become central.",
        ]
        statement = (
            f"If {counterfactual}, which conclusions about the original system stop being true?"
        )
        return OperatorResult(
            wonder_type=WonderType.QUESTION,
            statement=statement,
            explanation="The counterfactual exposes conclusions that depend on an unexamined default.",
            structured={
                "assumption": assumption,
                "counterfactual": counterfactual,
                "consequences": consequences,
                "new_questions": [statement],
            },
            questions=[statement],
        )
