"""Event publisher — 发布事件到 event bus。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import shortuuid

from packages.eventbus._queue import get_queue


async def emit_raw(task_id: str, event: dict):
    """发布详细事件流（用户下钻时才订阅）。"""
    event_id = f"{task_id}.{shortuuid.uuid()}"
    enriched = {
        **event,
        "event_id": event_id,
        "task_id": task_id,
        "ts": datetime.now(UTC).isoformat(),
    }
    queue = get_queue(f"swarm.events.{task_id}.raw")
    await queue.put(json.dumps(enriched, ensure_ascii=False))


async def emit_summary(task_id: str, agent_id: str, status: str, last_action: str):
    """发布摘要事件（100ms throttle，前端 badge 默认订阅）。"""
    event_id = f"{task_id}.{shortuuid.uuid()}"
    enriched = {
        "event_id": event_id,
        "type": "agent.update",
        "task_id": task_id,
        "agent_id": agent_id,
        "status": status,
        "last_action": last_action[:80],
        "ts": datetime.now(UTC).isoformat(),
    }
    queue = get_queue(f"swarm.events.{task_id}.summary")
    await queue.put(json.dumps(enriched, ensure_ascii=False))
