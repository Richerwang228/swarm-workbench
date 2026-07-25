"""Deterministic no-key demo that exercises the public task event contract."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import shortuuid

from packages.eventbus.publisher import emit_raw, emit_summary


@dataclass(frozen=True, slots=True)
class DemoWorkItem:
    role: str
    description: str
    tool: str
    result: str


def _demo_plan(prompt: str) -> list[DemoWorkItem]:
    subject = prompt.strip()[:80]
    return [
        DemoWorkItem(
            "pm",
            f"Define scope and success criteria for: {subject}",
            "plan_scope",
            "Scope, constraints, and acceptance criteria captured.",
        ),
        DemoWorkItem(
            "backend",
            "Design the orchestration and event contracts",
            "inspect_architecture",
            "Task, agent, todo, and streaming event boundaries verified.",
        ),
        DemoWorkItem(
            "frontend",
            "Prepare the observable console experience",
            "compose_interface",
            "Agent badges, activity, and result presentation prepared.",
        ),
        DemoWorkItem(
            "tester",
            "Review failure modes and release evidence",
            "verify_release",
            "Demo trace checked for completeness and safe defaults.",
        ),
    ]


async def run_demo_task(
    task_id: str,
    prompt: str,
    max_subagents: int = 4,
) -> str:
    """Run a bounded simulated swarm and emit the same events as live mode."""
    plan = _demo_plan(prompt)
    semaphore = asyncio.Semaphore(max(1, min(max_subagents, len(plan))))

    await emit_raw(
        task_id,
        {
            "type": "task.started",
            "prompt": prompt,
            "mode": "demo",
            "simulated": True,
        },
    )

    work: list[tuple[str, DemoWorkItem]] = []
    for item in plan:
        todo_id = shortuuid.uuid()[:8]
        work.append((todo_id, item))
        await emit_raw(
            task_id,
            {
                "type": "todo.update",
                "id": todo_id,
                "description": item.description,
                "status": "pending",
                "role": item.role,
                "depends_on": [],
            },
        )

    async def run_item(todo_id: str, item: DemoWorkItem) -> str:
        async with semaphore:
            agent_id = f"{item.role}-{todo_id}"
            await emit_raw(
                task_id,
                {
                    "type": "agent.spawned",
                    "agent_id": agent_id,
                    "role": item.role,
                    "task": item.description,
                    "status": "running",
                    "simulated": True,
                },
            )
            await emit_raw(
                task_id,
                {
                    "type": "todo.update",
                    "id": todo_id,
                    "description": item.description,
                    "status": "running",
                    "role": item.role,
                    "depends_on": [],
                },
            )
            await emit_summary(task_id, agent_id, "running", item.tool)
            await emit_raw(
                task_id,
                {
                    "type": "agent.tool.call.start",
                    "agent_id": agent_id,
                    "tool": item.tool,
                    "args": {"demo": True},
                },
            )

            # Staggered deterministic latency makes bounded concurrency visible.
            await asyncio.sleep(0.06 + (len(item.role) % 3) * 0.02)

            await emit_raw(
                task_id,
                {
                    "type": "agent.tool.result",
                    "agent_id": agent_id,
                    "tool": item.tool,
                    "result": item.result,
                },
            )
            await emit_raw(
                task_id,
                {
                    "type": "todo.update",
                    "id": todo_id,
                    "description": item.description,
                    "status": "done",
                    "role": item.role,
                    "depends_on": [],
                },
            )
            await emit_raw(
                task_id,
                {
                    "type": "agent.done",
                    "agent_id": agent_id,
                    "role": item.role,
                    "content": item.result,
                },
            )
            await emit_summary(task_id, agent_id, "done", item.result)
            return f"{item.role} — {item.result}"

    results = await asyncio.gather(*(run_item(todo_id, item) for todo_id, item in work))
    final = (
        "Demo swarm completed a bounded parallel pass.\n\n"
        + "\n".join(results)
        + "\n\nThis run was simulated locally; no model API or host tools were used."
    )
    await emit_raw(
        task_id,
        {
            "type": "agent.content.delta",
            "agent_id": "demo-reducer",
            "content": final,
        },
    )
    await emit_raw(
        task_id,
        {
            "type": "task.completed",
            "result": final,
            "simulated": True,
        },
    )
    return final
