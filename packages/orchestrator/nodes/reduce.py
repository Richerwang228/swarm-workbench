"""Reduce node — 聚合 sub-agent 结果，解锁依赖，更新 todo。"""

from __future__ import annotations

from packages.orchestrator.state import OrchestratorState


async def reduce_node(state: OrchestratorState) -> dict:
    """聚合本轮 worker 结果：
    1. 将 done 的任务 id 从其他任务的 depends_on 中移除
    2. 更新 current_step 计数
    """
    todo = state.get("todo", [])
    done_ids = {t["id"] for t in todo if t["status"] == "done"}

    # 解锁被依赖项解除的任务（去除已完成的依赖）
    updated_todo = [
        {**t, "depends_on": [d for d in t["depends_on"] if d not in done_ids]}
        if t["status"] == "pending"
        else t
        for t in todo
    ]

    return {
        "todo": updated_todo,
        "current_step": state.get("current_step", 0) + 1,
    }
