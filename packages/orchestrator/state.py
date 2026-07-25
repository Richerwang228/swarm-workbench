"""OrchestratorState — shared state TypedDict for the LangGraph graph."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class TodoItem(TypedDict):
    id: str
    description: str
    status: str  # pending / running / done / failed / skipped
    assigned_role: str
    depends_on: list[str]
    result: str | None


class SubAgentRun(TypedDict):
    agent_id: str
    role: str
    task_id: str
    status: str  # spawned / running / done / failed
    tool_calls: int
    tokens_used: int
    result: str


def merge_todos(left: list[TodoItem], right: list[TodoItem]) -> list[TodoItem]:
    """Merge parallel todo updates by id while preserving creation order."""
    merged = {item["id"]: item for item in left}
    order = [item["id"] for item in left]
    status_rank = {"pending": 0, "running": 1, "skipped": 2, "failed": 3, "done": 4}
    for item in right:
        if item["id"] not in merged:
            order.append(item["id"])
            merged[item["id"]] = item
            continue
        current = merged[item["id"]]
        if status_rank.get(item["status"], 0) >= status_rank.get(current["status"], 0):
            merged[item["id"]] = item
    return [merged[item_id] for item_id in order]


class OrchestratorState(TypedDict, total=False):
    trace_id: str
    prompt: str
    mode: str  # auto / single / swarm
    messages: list[dict]
    todo: Annotated[list[TodoItem], merge_todos]
    sub_agent_runs: Annotated[list[SubAgentRun], operator.add]
    blackboard_key: str
    current_step: int
    step_budget: int
    model_pref: str
    role_models: dict[str, str]
    agent_count: int
    exact_agent_count: bool
    planned: bool
    max_subagents: int
    interrupted: bool
    interrupt_message: str | None
    route_decision: str
    current_task_id: str
    current_task: str
    current_role: str
    current_model: str
    final_result: str
