from wandermind.cognitive.operators.base import CognitiveOperator, OperatorContext, OperatorResult
from wandermind.models import WonderType


class AnalogyOperator(CognitiveOperator):
    name = "analogy"

    async def apply(self, context: OperatorContext) -> OperatorResult:
        shared = context.association.shared_terms or [
            "resource allocation",
            "feedback",
            "adaptation",
        ]
        mapping = {
            "source_system": context.left.title,
            "target_system": context.right.title,
            "shared_structure": shared,
        }
        break_points = [
            f"{context.left.title} and {context.right.title} operate under different constraints.",
            "The mapping is structural and must not be treated as factual identity.",
        ]
        statement = (
            f"What if {context.left.title} behaves more like {context.right.title} "
            f"through the shared structure of {', '.join(shared[:3])}?"
        )
        return OperatorResult(
            wonder_type=WonderType.CONNECTION,
            statement=statement,
            explanation=(
                f"The analogy transfers a relationship pattern from {context.right.title} to "
                f"{context.left.title}, while explicitly preserving where the analogy breaks."
            ),
            structured={
                "source": context.left.title,
                "target": context.right.title,
                "shared_structure": shared,
                "mapping": mapping,
                "break_points": break_points,
                "possible_insight": statement,
            },
            questions=[f"Which prediction from {context.right.title} can be tested here?"],
        )
