"""In-process topic broker with wildcard subscriptions and bounded replay."""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

_QUEUE_SIZE = 10_000
_HISTORY_SIZE = 2_000


def _matches(pattern: str, subject: str) -> bool:
    """Match an exact subject or a NATS-style trailing ``>`` wildcard."""
    if pattern.endswith(">"):
        return subject.startswith(pattern[:-1])
    return pattern == subject


class PublishQueue(Protocol):
    async def put(self, item: str) -> None: ...

    def put_nowait(self, item: str) -> None: ...


@dataclass(slots=True)
class _Subscription:
    pattern: str
    queue: asyncio.Queue[str]


class _Broker:
    def __init__(self) -> None:
        self._subscriptions: list[_Subscription] = []
        self._history: deque[tuple[str, str]] = deque(maxlen=_HISTORY_SIZE)
        self._lock = asyncio.Lock()

    async def subscribe(self, pattern: str) -> tuple[asyncio.Queue[str], list[str]]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=_QUEUE_SIZE)
        async with self._lock:
            replay = [message for subject, message in self._history if _matches(pattern, subject)]
            self._subscriptions.append(_Subscription(pattern, queue))
        return queue, replay

    async def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subscriptions = [
                subscription
                for subscription in self._subscriptions
                if subscription.queue is not queue
            ]

    async def publish(self, subject: str, message: str) -> None:
        async with self._lock:
            self._history.append((subject, message))
            queues = [
                subscription.queue
                for subscription in self._subscriptions
                if _matches(subscription.pattern, subject)
            ]

        for queue in queues:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Keep live streams bounded: discard the oldest pending frame.
                with suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
                queue.put_nowait(message)

    def reset(self) -> None:
        self._subscriptions.clear()
        self._history.clear()


_broker = _Broker()


class _Topic:
    def __init__(self, subject: str) -> None:
        self._subject = subject
        self._replay_by_queue: dict[asyncio.Queue[str], list[str]] = {}

    async def subscribe(self) -> asyncio.Queue[str]:
        queue, replay = await _broker.subscribe(self._subject)
        self._replay_by_queue[queue] = replay
        for message in replay:
            queue.put_nowait(message)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._replay_by_queue.pop(queue, None)
        await _broker.unsubscribe(queue)

    async def publish(self, message: str) -> None:
        await _broker.publish(self._subject, message)


class _ProxyQueue:
    def __init__(self, subject: str) -> None:
        self._subject = subject

    async def put(self, item: str) -> None:
        await _broker.publish(self._subject, item)

    def put_nowait(self, item: str) -> None:
        asyncio.create_task(_broker.publish(self._subject, item))


def get_bus(subject: str) -> _Topic:
    return _Topic(subject)


def get_queue(subject: str) -> PublishQueue:
    return _ProxyQueue(subject)


async def open_subscription(pattern: str) -> tuple[asyncio.Queue[str], list[str]]:
    """Open a subscription without injecting replay into the live queue."""
    return await _broker.subscribe(pattern)


async def close_subscription(queue: asyncio.Queue[str]) -> None:
    await _broker.unsubscribe(queue)


def reset_broker() -> None:
    """Clear process-local state. Intended for tests and development reloads."""
    _broker.reset()
