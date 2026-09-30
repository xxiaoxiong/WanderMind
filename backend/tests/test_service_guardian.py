from __future__ import annotations

import asyncio

import pytest

from wandermind.application.service_guardian import ServiceGuardian


@pytest.mark.asyncio
async def test_guardian_restarts_worker_and_records_keepalive_success() -> None:
    restarts = 0
    requests: list[tuple[str, float]] = []

    async def ensure_worker() -> bool:
        nonlocal restarts
        restarts += 1
        return True

    async def request_keepalive(url: str, timeout_seconds: float) -> None:
        requests.append((url, timeout_seconds))

    guardian = ServiceGuardian(
        ensure_worker,
        keepalive_url="https://example.test/health",
        keepalive_interval_seconds=60,
        keepalive_timeout_seconds=12,
        request_keepalive=request_keepalive,
    )

    await guardian.run_once(force_keepalive=True)

    snapshot = guardian.snapshot()
    assert restarts == 1
    assert requests == [("https://example.test/health", 12)]
    assert snapshot.autopilot_restarts == 1
    assert snapshot.last_keepalive_success_at is not None
    assert snapshot.consecutive_failures == 0
    assert snapshot.last_error is None


@pytest.mark.asyncio
async def test_guardian_records_failures_without_stopping_future_checks() -> None:
    attempts = 0

    async def ensure_worker() -> bool:
        return False

    async def request_keepalive(_url: str, _timeout_seconds: float) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary network failure")

    guardian = ServiceGuardian(
        ensure_worker,
        keepalive_url="https://example.test/health",
        keepalive_interval_seconds=60,
        request_keepalive=request_keepalive,
    )

    await guardian.run_once(force_keepalive=True)
    failed = guardian.snapshot()
    await guardian.run_once(force_keepalive=True)
    recovered = guardian.snapshot()

    assert failed.consecutive_failures == 1
    assert failed.last_error is not None
    assert "temporary network failure" in failed.last_error
    assert recovered.consecutive_failures == 0
    assert recovered.last_error is None


@pytest.mark.asyncio
async def test_guardian_background_task_starts_and_stops_cleanly() -> None:
    checks = 0

    async def ensure_worker() -> bool:
        nonlocal checks
        checks += 1
        return False

    guardian = ServiceGuardian(
        ensure_worker,
        check_interval_seconds=0.01,
        keepalive_interval_seconds=60,
    )

    await guardian.start()
    await asyncio.sleep(0.03)
    assert guardian.running is True
    assert checks >= 1

    await guardian.shutdown()
    assert guardian.running is False


@pytest.mark.asyncio
async def test_keepalive_success_does_not_hide_worker_guard_failure() -> None:
    async def ensure_worker() -> bool:
        raise RuntimeError("worker cannot restart")

    async def request_keepalive(_url: str, _timeout_seconds: float) -> None:
        return None

    guardian = ServiceGuardian(
        ensure_worker,
        keepalive_url="https://example.test/health",
        keepalive_interval_seconds=60,
        request_keepalive=request_keepalive,
    )

    await guardian.run_once(force_keepalive=True)

    snapshot = guardian.snapshot()
    assert snapshot.last_keepalive_success_at is not None
    assert snapshot.consecutive_failures == 1
    assert snapshot.last_error is not None
    assert "worker cannot restart" in snapshot.last_error
