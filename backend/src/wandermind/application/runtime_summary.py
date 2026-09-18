from __future__ import annotations

from pydantic import Field

from wandermind.models.base import DomainModel
from wandermind.runtime import RuntimeSession


class RuntimeSummary(DomainModel):
    configured_adapter: str
    provider: str | None = None
    model: str | None = None
    calls: int = Field(default=0, ge=0)
    completed_calls: int = Field(default=0, ge=0)
    failed_calls: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    purposes: list[str] = Field(default_factory=list)
    verified: bool = False


def summarize_runtime(
    configured_adapter: str,
    sessions: list[RuntimeSession],
) -> RuntimeSummary:
    calls = sum(_number(session.cost, "runtime_calls") for session in sessions)
    failed_calls = sum(_number(session.cost, "failures") for session in sessions)
    completed_calls = max(0, calls - failed_calls)
    providers = list(dict.fromkeys(session.provider for session in sessions))
    models = list(
        dict.fromkeys(
            model
            for session in sessions
            if (model := _model(session)) is not None
        )
    )
    return RuntimeSummary(
        configured_adapter=configured_adapter,
        provider=", ".join(providers) or None,
        model=", ".join(models) or None,
        calls=calls,
        completed_calls=completed_calls,
        failed_calls=failed_calls,
        duration_seconds=sum(_float(session.cost, "duration_seconds") for session in sessions),
        input_tokens=sum(_number(session.cost, "input_tokens") for session in sessions),
        output_tokens=sum(_number(session.cost, "output_tokens") for session in sessions),
        total_tokens=sum(_number(session.cost, "total_tokens") for session in sessions),
        purposes=list(dict.fromkeys(session.purpose for session in sessions)),
        verified=completed_calls > 0,
    )


def _number(values: dict[str, object], key: str) -> int:
    value = values.get(key)
    return int(value) if isinstance(value, int | float) else 0


def _float(values: dict[str, object], key: str) -> float:
    value = values.get(key)
    return float(value) if isinstance(value, int | float) else 0.0


def _model(session: RuntimeSession) -> str | None:
    last_usage = session.cost.get("last_usage")
    if isinstance(last_usage, dict):
        usage_model = last_usage.get("model")
        if isinstance(usage_model, str) and usage_model:
            return usage_model
    metadata_model = session.metadata.get("model")
    return metadata_model if isinstance(metadata_model, str) and metadata_model else None
