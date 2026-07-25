"""Event subscriber — 订阅 event bus 并异步迭代事件。

支持 wildcard subject（如 swarm.events.{task_id}.> 匹配所有子主题）。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from packages.eventbus._queue import close_subscription, open_subscription
from packages.shared.events import SwarmEvent


async def subscribe(
    subject: str,
    start_from: str | None = None,
    timeout: float | None = None,
) -> AsyncGenerator[SwarmEvent, None]:
    """订阅指定 subject 的事件流，异步迭代 SwarmEvent。

    subject 支持通配符：
    - swarm.events.{task_id}.>  匹配 raw 和 summary
    - swarm.events.{task_id}.raw  只匹配 raw
    """
    queue, replay = await open_subscription(subject)

    def _after_last_event(messages: list[str]) -> list[str]:
        if not start_from:
            return messages
        for index, raw in enumerate(messages):
            try:
                data = json.loads(raw)
                if data.get("event_id", data.get("id")) == start_from:
                    return messages[index + 1 :]
            except json.JSONDecodeError:
                continue
        return messages

    pending = _after_last_event(replay)

    try:
        while True:
            try:
                if pending:
                    raw = pending.pop(0)
                elif timeout is not None:
                    raw = await asyncio.wait_for(queue.get(), timeout=timeout)
                else:
                    raw = await queue.get()
            except TimeoutError:
                return

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # 如果 start_from 指定了 event id，跳过 id <= start_from 的事件
            # 简化实现：直接跳过（生产环境可加持久化索引）
            event_id = data.get("event_id", data.get("id", ""))

            yield SwarmEvent(
                id=event_id,
                type=data.get("type", "unknown"),
                data=data,
            )
    finally:
        await close_subscription(queue)
