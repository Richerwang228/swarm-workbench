"""Planner node — 将用户 prompt 拆解为 todo list。"""

from __future__ import annotations

import json
import re

from packages.orchestrator.state import OrchestratorState, TodoItem


async def planner_node(state: OrchestratorState) -> dict:
    """调用 LLM 拆解任务为 todo items。

    The model produces one fixed plan. Later waves drain this plan without
    calling the planner again.
    """
    from packages.eventbus.publisher import emit_raw
    from packages.llm_gateway.router import call

    if state.get("planned"):
        return {}

    target = max(1, min(state.get("agent_count", 4), 100))
    exact = state.get("exact_agent_count", False)
    count_rule = (
        f"必须恰好输出 {target} 个有实际价值、互不重复的子任务。"
        if exact
        else f"最多输出 {target} 个子任务；只创建对完成任务真正有帮助的 Agent。"
    )

    messages = [
        {"role": "system", "content": _PLANNER_SYSTEM},
        {
            "role": "user",
            "content": (
                f"用户任务：{state['prompt']}\n\n"
                f"{count_rule}\n请一次性输出完整执行计划（JSON array）。"
            ),
        },
    ]

    response = await call(
        model=state.get("model_pref", "worker"),
        role="planner",
        messages=messages,
    )
    content = response.choices[0].message.content or ""
    todo_items = _parse_plan(content, max_items=target)
    if exact and len(todo_items) != target:
        raise ValueError(f"planner returned {len(todo_items)} tasks; exactly {target} required")

    updated_messages = (
        state.get("messages", []) + messages + [{"role": "assistant", "content": content}]
    )
    for item in todo_items:
        await emit_raw(
            state["trace_id"],
            {
                "type": "todo.update",
                "id": item["id"],
                "description": item["description"],
                "status": item["status"],
                "role": item["assigned_role"],
                "depends_on": item["depends_on"],
            },
        )
    return {"todo": todo_items, "messages": updated_messages, "planned": True}


def _parse_todo(content: str, existing: list[TodoItem]) -> list[TodoItem]:
    """从 LLM 输出中提取 JSON 数组并构建 TodoItem 列表。"""
    items = _parse_plan(content, max_items=100, fallback=True)
    existing_descriptions = {t["description"] for t in existing}
    filtered = [item for item in items if item["description"] not in existing_descriptions]
    return filtered or [_make_todo("执行任务", "pm")]


def _parse_plan(
    content: str,
    *,
    max_items: int,
    fallback: bool = False,
) -> list[TodoItem]:
    """Parse, validate, and assign stable server-owned IDs to one DAG plan."""

    # 先去掉 markdown code fence
    content = re.sub(r"```(?:json)?\s*", "", content).strip()

    # 找到最外层 '[' ... ']'（贪婪，处理嵌套）
    start = content.find("[")
    if start == -1:
        if fallback:
            return [_make_todo("执行任务", "pm")]
        raise ValueError("planner response does not contain a JSON array")

    depth = 0
    end = -1
    for i, ch in enumerate(content[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        if fallback:
            return [_make_todo("执行任务", "pm")]
        raise ValueError("planner response contains an unterminated JSON array")

    try:
        raw = json.loads(content[start:end])
    except json.JSONDecodeError as exc:
        if fallback:
            return [_make_todo("执行任务", "pm")]
        raise ValueError("planner response contains invalid JSON") from exc
    if not isinstance(raw, list) or not raw:
        raise ValueError("planner plan must be a non-empty array")
    if len(raw) > max_items:
        raise ValueError(f"planner returned more than the allowed {max_items} tasks")

    entries: list[tuple[str, str, str, list[str]]] = []
    seen_keys: set[str] = set()
    seen_descriptions: set[str] = set()
    for index, entry in enumerate(raw, 1):
        if not isinstance(entry, dict):
            raise ValueError("every planner item must be an object")
        desc = str(entry.get("description", "")).strip()
        if not desc:
            raise ValueError("every planner item requires a description")
        if len(desc) > 500:
            raise ValueError("planner item description exceeds 500 characters")
        if desc in seen_descriptions:
            raise ValueError("planner item descriptions must be unique")
        role = entry.get("role", entry.get("assigned_role", "pm"))
        if role not in {"pm", "designer", "frontend", "backend", "tester", "ops"}:
            role = "pm"
        key = str(entry.get("key") or f"task-{index:03d}")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", key):
            raise ValueError(f"invalid planner task key: {key!r}")
        if key in seen_keys:
            raise ValueError("planner task keys must be unique")
        raw_dependencies = entry.get("depends_on", [])
        if not isinstance(raw_dependencies, list):
            raise ValueError("depends_on must be an array of task keys")
        dependencies = [str(dependency) for dependency in raw_dependencies]
        seen_keys.add(key)
        seen_descriptions.add(desc)
        entries.append((key, desc, str(role), dependencies))

    key_to_id = {key: f"task-{index:03d}" for index, (key, *_rest) in enumerate(entries, 1)}
    items = [
        _make_todo(
            description,
            role,
            [key_to_id[dependency] for dependency in dependencies if dependency in key_to_id],
            task_id=key_to_id[key],
        )
        for key, description, role, dependencies in entries
    ]
    for key, _, _, dependencies in entries:
        unknown = sorted(set(dependencies) - key_to_id.keys())
        if unknown:
            raise ValueError(f"task {key!r} has unknown dependencies: {', '.join(unknown)}")
        if key in dependencies:
            raise ValueError(f"task {key!r} cannot depend on itself")
    _assert_acyclic(items)
    return items


def _make_todo(
    description: str,
    role: str = "pm",
    depends_on: list[str] | None = None,
    *,
    task_id: str = "task-001",
) -> TodoItem:
    return TodoItem(
        id=task_id,
        description=description,
        status="pending",
        assigned_role=role,
        depends_on=depends_on or [],
        result=None,
    )


def _assert_acyclic(items: list[TodoItem]) -> None:
    dependencies = {item["id"]: set(item["depends_on"]) for item in items}
    remaining = set(dependencies)
    while remaining:
        ready = {task_id for task_id in remaining if not (dependencies[task_id] & remaining)}
        if not ready:
            raise ValueError("planner task dependencies contain a cycle")
        remaining -= ready


_PLANNER_SYSTEM = """\
你是项目经理，负责一次性生成完整、可验证的多 Agent 执行 DAG。

规则：
1. 每个子任务必须可独立执行（或通过 depends_on 声明依赖）
2. key 必须唯一，depends_on 只能引用同一计划中的 key
3. role 只能取：pm / designer / frontend / backend / tester / ops
4. 没有依赖的任务会真正并行运行；不要制造无意义或重复任务
5. 只输出 JSON array，不要任何其他文字

输出格式：
[
  {"key": "api", "description": "设计 API", "role": "backend", "depends_on": []},
  {"key": "verify", "description": "验证 API", "role": "tester", "depends_on": ["api"]}
]
"""
