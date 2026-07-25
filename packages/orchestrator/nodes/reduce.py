"""Reduce node — 聚合 sub-agent 结果，解锁依赖，更新 todo。"""

from __future__ import annotations

from typing import cast

from packages.orchestrator.state import OrchestratorState, TodoItem


async def reduce_node(state: OrchestratorState) -> dict:
    """聚合本轮 worker 结果：
    1. 将 done 的任务 id 从其他任务的 depends_on 中移除
    2. 更新 current_step 计数
    """
    todo: list[TodoItem] = state.get("todo", [])
    done_ids = {t["id"] for t in todo if t["status"] == "done"}
    failed_ids = {t["id"] for t in todo if t["status"] in {"failed", "skipped"}}

    # Release successful dependencies, then propagate failed dependencies so a
    # DAG never finishes with invisible permanent pending work.
    updated_todo: list[TodoItem] = [
        cast(TodoItem, {**t, "depends_on": [d for d in t["depends_on"] if d not in done_ids]})
        if t["status"] == "pending"
        else t
        for t in todo
    ]
    changed = True
    while changed:
        changed = False
        next_todo: list[TodoItem] = []
        for item in updated_todo:
            if item["status"] == "pending" and any(dep in failed_ids for dep in item["depends_on"]):
                item = cast(
                    TodoItem,
                    {
                        **item,
                        "status": "skipped",
                        "result": "Skipped because a dependency failed",
                    },
                )
                failed_ids.add(item["id"])
                changed = True
            next_todo.append(item)
        updated_todo = next_todo

    return {
        "todo": updated_todo,
        "current_step": state.get("current_step", 0) + 1,
    }
