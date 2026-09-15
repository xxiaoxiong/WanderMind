from wandermind.cognitive.operators.base import CognitiveOperator, OperatorContext, OperatorResult
from wandermind.models import WonderType


class AbstractionOperator(CognitiveOperator):
    name = "abstraction"

    async def apply(self, context: OperatorContext) -> OperatorResult:
        shared = context.association.shared_terms or ["limited resources", "selection", "feedback"]
        pattern = f"systems that adapt through {', '.join(shared[:3])}"
        statement = f"Both examples may instantiate a broader class: {pattern}."
        return OperatorResult(
            wonder_type=WonderType.INSIGHT,
            statement=statement,
            explanation=(
                "Abstraction removes domain-specific details and preserves a reusable causal or "
                "organizational pattern."
            ),
            structured={
                "instances": [context.left.title, context.right.title],
                "abstract_pattern": pattern,
                "invariants": shared,
                "possible_new_instances": [],
            },
            questions=["What third domain would falsify or strengthen this abstraction?"],
        )
