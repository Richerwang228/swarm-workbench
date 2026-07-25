"""Process-wide capacity control for logical agent work."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CapacitySnapshot:
    limit: int
    active: int
    queued: int
    peak_active: int
    total_acquired: int


@dataclass(frozen=True, slots=True)
class SlotLease:
    queue_wait_ms: float
    active_at_start: int


class AgentCapacity:
    """A fair-enough process-local semaphore with observable counters."""

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("capacity limit must be positive")
        self.limit = limit
        self._semaphore = asyncio.Semaphore(limit)
        self._active = 0
        self._queued = 0
        self._peak_active = 0
        self._total_acquired = 0

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[SlotLease]:
        """Wait for a process slot and release it even on cancellation."""
        queued_at = time.monotonic_ns()
        acquired = False
        self._queued += 1
        try:
            await self._semaphore.acquire()
            acquired = True
            self._queued -= 1
            self._active += 1
            self._total_acquired += 1
            self._peak_active = max(self._peak_active, self._active)
            yield SlotLease(
                queue_wait_ms=(time.monotonic_ns() - queued_at) / 1_000_000,
                active_at_start=self._active,
            )
        finally:
            if acquired:
                self._active -= 1
                self._semaphore.release()
            else:
                self._queued -= 1

    def snapshot(self) -> CapacitySnapshot:
        return CapacitySnapshot(
            limit=self.limit,
            active=self._active,
            queued=self._queued,
            peak_active=self._peak_active,
            total_acquired=self._total_acquired,
        )


_capacity: AgentCapacity | None = None
_capacity_override: int | None = None


def get_capacity() -> AgentCapacity:
    """Return the application-wide capacity manager."""
    global _capacity
    requested = (
        _capacity_override
        if _capacity_override is not None
        else int(os.getenv("SWARM_GLOBAL_AGENT_CAP", "8"))
    )
    configured = max(1, min(requested, 100))
    if _capacity is None or (_capacity.limit != configured and _capacity.snapshot().active == 0):
        _capacity = AgentCapacity(configured)
    return _capacity


def reset_capacity(limit: int | None = None) -> AgentCapacity:
    """Reset counters and capacity. Intended for tests and clean startup."""
    global _capacity, _capacity_override
    _capacity_override = limit
    configured = limit if limit is not None else int(os.getenv("SWARM_GLOBAL_AGENT_CAP", "8"))
    _capacity = AgentCapacity(max(1, min(configured, 100)))
    return _capacity


def configure_capacity(limit: int) -> AgentCapacity:
    """Install a runtime limit when no live work is holding or waiting for slots."""
    global _capacity, _capacity_override
    if _capacity is not None:
        snapshot = _capacity.snapshot()
        if snapshot.active or snapshot.queued:
            raise RuntimeError("cannot change global capacity while agents are active or queued")
    _capacity_override = max(1, min(limit, 100))
    _capacity = AgentCapacity(_capacity_override)
    return _capacity
