"""LangGraph StateGraph — planner → dispatch → worker → reduce → compact."""

from __future__ import annotations

import os

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from packages.orchestrator.checkpointer import get_checkpointer
from packages.orchestrator.nodes.compact import compact_node
from packages.orchestrator.nodes.planner import planner_node
from packages.orchestrator.nodes.reduce import reduce_node
from packages.orchestrator.nodes.route import route_node
from packages.orchestrator.state import OrchestratorState


def build_graph():
    """构建 LangGraph StateGraph。"""
    builder = StateGraph(OrchestratorState)

    builder.add_node("route", route_node)
    builder.add_node("planner", planner_node)
    builder.add_node("dispatch", _dispatch_node)
    builder.add_node("worker", _worker_node)
    builder.add_node("reduce", reduce_node)
    builder.add_node("compact", compact_node)

    builder.set_entry_point("route")
    builder.add_conditional_edges(
        "route", _after_route, {"single": "worker", "swarm": "planner", "clarify": END}
    )
    # planner 结束后 → dispatch fan-out
    builder.add_edge("planner", "dispatch")
    # dispatch 用 Send API 派发，返回 list[Send] → 并行运行 worker
    builder.add_conditional_edges("dispatch", _dispatch_fan_out, ["worker"])
    builder.add_edge("worker", "reduce")
    builder.add_conditional_edges(
        "reduce", _after_reduce, {"continue": "planner", "done": "compact"}
    )
    builder.add_edge("compact", END)

    checkpointer = get_checkpointer()
    return builder.compile(checkpointer=checkpointer)


async def _dispatch_node(state: OrchestratorState) -> OrchestratorState:
    """dispatch node 本身不修改 state，fan-out 通过 conditional edge 完成。"""
    return state


def _dispatch_fan_out(state: OrchestratorState) -> list[Send]:
    """从 pending todo 中取任务，Send 到 worker 并行执行。"""
    from packages.orchestrator.nodes.dispatch import ROLE_MODEL_MAP

    configured_max = int(os.getenv("MAX_CONCURRENT_SUBAGENTS", "5"))
    max_concurrent = max(1, min(state.get("max_subagents", configured_max), configured_max))
    pending = [t for t in state.get("todo", []) if t["status"] == "pending" and not t["depends_on"]]
    wave = pending[:max_concurrent]

    return [
        Send(
            "worker",
            {
                **state,
                "current_task_id": t["id"],
                "current_task": t["description"],
                "current_role": t["assigned_role"],
                "current_model": ROLE_MODEL_MAP.get(t["assigned_role"], "worker"),
            },
        )
        for t in wave
    ]


async def _worker_node(state: OrchestratorState) -> dict:
    """Worker node — 运行一个 sub-agent task，结果写回 state。"""
    from packages.eventbus.publisher import emit_raw, emit_summary
    from packages.worker.runner import run_worker

    task_id = state["trace_id"]
    current_task_id = str(state.get("current_task_id") or "single")
    task = str(state.get("current_task") or state["prompt"])
    role = state.get("current_role", "pm")
    model = state.get("current_model", "worker")
    agent_id = f"{current_task_id}:{role}"

    result_parts: list[str] = []

    await emit_raw(
        task_id,
        {
            "type": "agent.spawned",
            "agent_id": agent_id,
            "role": role,
            "task": task,
            "status": "running",
        },
    )
    if current_task_id != "single":
        await emit_raw(
            task_id,
            {
                "type": "todo.update",
                "id": current_task_id,
                "description": task,
                "status": "running",
                "role": role,
                "depends_on": [],
            },
        )
    await emit_summary(task_id, agent_id, "running", f"Started: {task[:60]}")

    async for event in run_worker(
        task_id=task_id,
        task=task,
        role=role,
        model=model,
        tool_budget=state.get("step_budget", 50),
        agent_id=agent_id,
    ):
        if event.get("type") == "agent.done":
            result_parts.append(event.get("content", ""))

    result = "\n".join(result_parts) or "(no output)"

    await emit_summary(task_id, agent_id, "done", result[:80])
    if current_task_id != "single":
        await emit_raw(
            task_id,
            {
                "type": "todo.update",
                "id": current_task_id,
                "description": task,
                "status": "done",
                "role": role,
                "depends_on": [],
            },
        )

    # 更新 todo list 中对应 item 的状态
    updated_todo = [
        {**t, "status": "done", "result": result} if t["id"] == current_task_id else t
        for t in state.get("todo", [])
    ]
    updated_runs = [
        *state.get("sub_agent_runs", []),
        {
            "agent_id": agent_id,
            "role": role,
            "task_id": current_task_id,
            "status": "done",
            "tool_calls": 0,
            "tokens_used": 0,
        },
    ]
    return {"todo": updated_todo, "sub_agent_runs": updated_runs}


def _after_route(state: OrchestratorState) -> str:
    mode = state.get("mode", "auto")
    if mode == "single":
        return "single"
    if mode == "swarm":
        return "swarm"
    return state.get("route_decision", "single")


def _after_reduce(state: OrchestratorState) -> str:
    pending = [t for t in state.get("todo", []) if t["status"] not in ("done", "failed")]
    if not pending:
        return "done"
    # 防止死循环：如果没有 depends_on=[] 的 pending 任务（全都在等依赖），也结束
    unblocked = [t for t in pending if not t.get("depends_on")]
    if not unblocked:
        return "done"
    return "continue"


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_task(
    task_id: str,
    prompt: str,
    mode: str = "auto",
    max_subagents: int = 5,
):
    """启动一个 swarm task（由 FastAPI background task 调用）。"""
    from packages.eventbus.publisher import emit_raw

    graph = get_graph()
    initial_state: OrchestratorState = {
        "trace_id": task_id,
        "prompt": prompt,
        "mode": mode,
        "messages": [],
        "todo": [],
        "sub_agent_runs": [],
        "blackboard_key": f"blackboard:{task_id}",
        "current_step": 0,
        "step_budget": 50,
        "model_pref": "worker",
        "max_subagents": max(1, min(max_subagents, 8)),
        "interrupted": False,
        "interrupt_message": None,
    }
    config = {"configurable": {"thread_id": task_id}}
    try:
        await emit_raw(task_id, {"type": "task.started", "task_id": task_id, "prompt": prompt})
        await graph.ainvoke(initial_state, config=config)
        await emit_raw(task_id, {"type": "task.completed", "task_id": task_id})
    except Exception as exc:
        await emit_raw(task_id, {"type": "task.error", "task_id": task_id, "error": str(exc)})
        raise
