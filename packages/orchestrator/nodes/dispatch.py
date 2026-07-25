"""Dispatch node — 用 LangGraph Send API 动态 fan-out。"""

from __future__ import annotations

from langgraph.types import Send

from packages.orchestrator.state import OrchestratorState

ROLE_MODEL_MAP = {
    role: "worker"
    for role in (
        "planner",
        "pm",
        "frontend",
        "backend",
        "tester",
        "ops",
        "designer",
        "reducer",
        "summarizer",
    )
}


async def dispatch_node(state: OrchestratorState) -> list[Send]:
    """从 pending todo 中取任务，生成 Send 指令动态 fan-out 到 worker。"""
    import os

    max_concurrent = int(os.getenv("MAX_CONCURRENT_SUBAGENTS", "5"))
    pending = [t for t in state["todo"] if t["status"] == "pending" and not t["depends_on"]]
    wave = pending[:max_concurrent]

    return [
        Send(
            "worker",
            {
                "task_id": t["id"],
                "task": t["description"],
                "role": t["assigned_role"],
                "model": ROLE_MODEL_MAP.get(t["assigned_role"], "worker"),
                "parent_trace": state["trace_id"],
                "shared_blackboard_key": state["blackboard_key"],
                "tool_budget": 50,
            },
        )
        for t in wave
    ]
