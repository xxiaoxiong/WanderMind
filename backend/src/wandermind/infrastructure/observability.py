from __future__ import annotations

import logging
import sys
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any
from uuid import uuid4

import structlog
from fastapi import Request, Response
from prometheus_client import Counter, Histogram

from wandermind.infrastructure.security import redact_secrets
from wandermind.models import Candidate, WanderSession

REQUEST_COUNT = Counter(
    "wandermind_http_requests_total",
    "HTTP requests handled by WanderMind",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "wandermind_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)
WANDER_RUNS = Counter(
    "wandermind_wander_runs_total",
    "Wander sessions by outcome",
    ["outcome"],
)
RUNTIME_CALLS = Counter(
    "wandermind_runtime_calls_total",
    "Runtime calls by purpose and outcome",
    ["purpose", "outcome"],
)
WANDER_DURATION = Histogram(
    "wandermind_wander_duration_seconds",
    "Wander session duration",
    ["outcome"],
)
WANDER_STEP_COUNT = Histogram(
    "wandermind_wander_step_count",
    "Trace steps per Wander session",
)
PATCH_SWITCH_COUNT = Histogram(
    "wandermind_patch_switch_count",
    "Patch switches per Wander session",
)
CANDIDATE_COUNT = Histogram(
    "wandermind_candidate_count",
    "Candidates generated per Wander session",
)
SCORE_DISTRIBUTION = Histogram(
    "wandermind_wonder_score",
    "Candidate score distribution",
    buckets=(0.0, 0.25, 0.4, 0.58, 0.65, 0.8, 1.0),
)
WONDER_COUNT = Histogram(
    "wandermind_wonder_count",
    "Wonders surfaced per Wander session",
)


def configure_logging(level: str) -> None:
    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_log_event,
        structlog.processors.JSONRenderer(),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _redact_log_event(
    _logger: object,
    _method_name: str,
    event_dict: dict[str, object],
) -> dict[str, object]:
    redacted = redact_secrets(event_dict)
    assert isinstance(redacted, dict)
    return redacted


def record_wander_run(
    session: WanderSession,
    candidates: list[Candidate],
    wonders: Sequence[object],
) -> None:
    outcome = session.status.value
    duration = 0.0
    if session.started_at is not None and session.ended_at is not None:
        duration = max(0.0, (session.ended_at - session.started_at).total_seconds())
    WANDER_RUNS.labels(outcome).inc()
    WANDER_DURATION.labels(outcome).observe(duration)
    WANDER_STEP_COUNT.observe(len(session.trace.steps))
    PATCH_SWITCH_COUNT.observe(int(session.metadata.get("patch_switches", 0)))
    CANDIDATE_COUNT.observe(len(candidates))
    WONDER_COUNT.observe(len(wonders))
    for candidate in candidates:
        if candidate.scores is not None:
            SCORE_DISTRIBUTION.observe(candidate.scores.total)
    structlog.get_logger("wander").info(
        "wander_completed",
        session_id=str(session.id),
        seed_id=str(session.seed_id),
        outcome=outcome,
        stop_reason=session.trace.stop_reason,
        duration_seconds=duration,
        step_count=len(session.trace.steps),
        patch_switches=int(session.metadata.get("patch_switches", 0)),
        candidate_count=len(candidates),
        wonder_count=len(wonders),
    )


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid4()))
    started = time.perf_counter()
    logger = structlog.get_logger("http")
    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - started
        REQUEST_COUNT.labels(request.method, request.url.path, "500").inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(duration)
        logger.exception(
            "request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_seconds=duration,
        )
        raise
    duration = time.perf_counter() - started
    REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(duration)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=duration,
    )
    return response
