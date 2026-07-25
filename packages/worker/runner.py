"""Worker runner — 运行一个 sub-agent，流式 yield 事件。"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from packages.worker.agent_loop import agent_loop
from packages.worker.role_persona import build_worker_messages


async def run_worker(
    task_id: str,
    task: str,
    role: str,
    model: str,
    tool_budget: int = 50,
    agent_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """运行一个 sub-agent task，流式 yield 事件（同时 emit 到 event bus）。"""
    from packages.eventbus.publisher import emit_raw

    messages = build_worker_messages(role, task)

    async for event in agent_loop(
        messages=messages,
        model=model,
        role=role,
        tool_budget=tool_budget,
        agent_id=agent_id or f"{task_id}:{role}",
    ):
        await emit_raw(task_id, event)
        yield event
