from wandermind.cognitive.operators.base import CognitiveOperator, OperatorContext, OperatorResult
from wandermind.models import WonderType


class ConceptualBlendOperator(CognitiveOperator):
    name = "conceptual_blend"

    async def apply(self, context: OperatorContext) -> OperatorResult:
        generic = context.association.shared_terms or ["selection", "constraints", "adaptation"]
        blended = f"{context.left.title} as a {context.right.title}-inspired system"
        emergent = [
            f"A new feedback loop combining {context.left.title} with {context.right.title}",
            "A hybrid set of constraints neither input exposes alone",
        ]
        statement = f"Design {blended}: what emergent behavior would appear?"
        return OperatorResult(
            wonder_type=WonderType.HYPOTHESIS,
            statement=statement,
            explanation=(
                f"The blend combines the organizing logic of {context.left.title} and "
                f"{context.right.title} instead of merely comparing them."
            ),
            structured={
                "input_a": context.left.title,
                "input_b": context.right.title,
                "generic_structure": generic,
                "blended_structure": blended,
                "emergent_properties": emergent,
            },
            questions=[
                "Which emergent property is measurable?",
                "What failure mode appears first?",
            ],
        )
