from wandermind.cognitive.operators.base import CognitiveOperator, OperatorContext, OperatorResult
from wandermind.models import WonderType


class SecondOrderConsequenceOperator(CognitiveOperator):
    name = "second_order"

    async def apply(self, context: OperatorContext) -> OperatorResult:
        first_order = f"{context.left.title} adopts a mechanism found in {context.right.title}"
        second_order = "Actors adapt to the mechanism, changing incentives and the mechanism itself"
        third_order = "The surrounding institution may evolve to manage the new adaptation loop"
        statement = f"If {first_order}, could {second_order.lower()}?"
        return OperatorResult(
            wonder_type=WonderType.HYPOTHESIS,
            statement=statement,
            explanation="The operator follows adaptation beyond the immediate effect into feedback loops.",
            structured={
                "first_order": first_order,
                "second_order": second_order,
                "third_order": third_order,
                "assumptions": ["Participants can observe and respond to the first-order change."],
            },
            questions=["Who adapts first?", "What stabilizes or amplifies the feedback loop?"],
        )
