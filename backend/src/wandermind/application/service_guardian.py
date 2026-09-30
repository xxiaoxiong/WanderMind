from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from time import monotonic

import httpx
from pydantic import BaseModel

from wandermind.models.base import utc_now

logger = logging.getLogger(__name__)

EnsureWorker = Callable[[], Awaitable[bool]]
KeepaliveRequest = Callable[[str, float], Awaitable[None]]


class ServiceGuardianSnapshot(BaseModel):
    running: bool
    keepalive_enabled: bool
    last_check_at: datetime | None = None
    last_keepalive_success_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
    autopilot_restarts: int = 0


class ServiceGuardian:
    def __init__(
        self,
        ensure_worker: EnsureWorker,
        *,
        keepalive_url: str | None = None,
        check_interval_seconds: float = 30.0,
        keepalive_interval_seconds: float = 300.0,
        keepalive_timeout_seconds: float = 30.0,
        request_keepalive: KeepaliveRequest | None = None,
    ) -> None:
        self.ensure_worker = ensure_worker
        self.keepalive_url = keepalive_url
        self.check_interval_seconds = check_interval_seconds
        self.keepalive_interval_seconds = keepalive_interval_seconds
        self.keepalive_timeout_seconds = keepalive_timeout_seconds
        self.request_keepalive = request_keepalive or _request_keepalive
        self.last_check_at: datetime | None = None
        self.last_keepalive_success_at: datetime | None = None
        self._worker_error: str | None = None
        self._keepalive_error: str | None = None
        self._worker_failures = 0
        self._keepalive_failures = 0
        self.autopilot_restarts = 0
        self._next_keepalive_at: float | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._next_keepalive_at = monotonic() + self.keepalive_interval_seconds
        self._task = asyncio.create_task(self._loop(), name="wandermind-service-guardian")

    async def shutdown(self) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def run_once(self, *, force_keepalive: bool = False) -> None:
        self.last_check_at = utc_now()
        try:
            restarted = await self.ensure_worker()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._record_failure("autopilot", error)
            logger.exception("service guardian could not ensure autopilot worker")
        else:
            self._worker_error = None
            self._worker_failures = 0
            if restarted:
                self.autopilot_restarts += 1

        if self.keepalive_url is None:
            return
        now = monotonic()
        if not force_keepalive and (
            self._next_keepalive_at is None or now < self._next_keepalive_at
        ):
            return
        self._next_keepalive_at = now + self.keepalive_interval_seconds
        try:
            await self.request_keepalive(
                self.keepalive_url,
                self.keepalive_timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._record_failure("keepalive", error)
            logger.warning("service keepalive request failed: %s", error)
        else:
            self.last_keepalive_success_at = utc_now()
            self._keepalive_error = None
            self._keepalive_failures = 0

    def snapshot(self) -> ServiceGuardianSnapshot:
        return ServiceGuardianSnapshot(
            running=self.running,
            keepalive_enabled=self.keepalive_url is not None,
            last_check_at=self.last_check_at,
            last_keepalive_success_at=self.last_keepalive_success_at,
            last_error=self._worker_error or self._keepalive_error,
            consecutive_failures=max(self._worker_failures, self._keepalive_failures),
            autopilot_restarts=self.autopilot_restarts,
        )

    async def _loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.check_interval_seconds)

    def _record_failure(self, operation: str, error: Exception) -> None:
        message = f"{operation}: {type(error).__name__}: {str(error)[:500]}"
        if operation == "autopilot":
            self._worker_error = message
            self._worker_failures += 1
            return
        self._keepalive_error = message
        self._keepalive_failures += 1


async def _request_keepalive(url: str, timeout_seconds: float) -> None:
    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "WanderMind-ServiceGuardian/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
