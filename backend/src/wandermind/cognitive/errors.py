class CognitiveError(RuntimeError):
    code = "cognitive_error"
    retryable = False


class EmbeddingError(CognitiveError):
    code = "embedding_error"
    retryable = True


class OperatorExecutionError(CognitiveError):
    code = "operator_error"


class EvaluationError(CognitiveError):
    code = "evaluation_error"
