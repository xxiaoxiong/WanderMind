from wandermind.cognitive.operators.base import CognitiveOperator, OperatorContext, OperatorResult
from wandermind.models import WonderType


class InversionOperator(CognitiveOperator):
    name = "inversion"

    async def apply(self, context: OperatorContext) -> OperatorResult:
        original = f"Use {context.left.title} to explain or improve {context.right.title}"
        inverted = f"Use {context.right.title} to expose limits in {context.left.title}"
        statement = f"Invert the direction: {inverted}. What becomes visible?"
        return OperatorResult(
            wonder_type=WonderType.SPARK,
            statement=statement,
            explanation="Reversing explanatory direction reveals asymmetries hidden by the default framing.",
            structured={
                "original_direction": original,
                "inverted_direction": inverted,
                "new_constraints": ["Causality must not be inferred from a useful comparison."],
            },
            questions=["Which asymmetry survives the inversion?"],
        )
