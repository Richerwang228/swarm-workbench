"""Planner node — 将用户 prompt 拆解为 todo list。"""

from __future__ import annotations

import json
import re

import shortuuid

from packages.orchestrator.state import OrchestratorState, TodoItem


async def planner_node(state: OrchestratorState) -> dict:
    """调用 LLM 拆解任务为 todo items。

    Output is a flat JSON array for one bounded parallel wave.
    """
    from packages.eventbus.publisher import emit_raw
    from packages.llm_gateway.router import call

    existing_done = [t for t in state.get("todo", []) if t["status"] == "done"]
    done_summary = (
        "\n".join(f"- [done] {t['description']}" for t in existing_done) or "（无已完成任务）"
    )

    messages = [
        {"role": "system", "content": _PLANNER_SYSTEM},
        {
            "role": "user",
            "content": (
                f"用户任务：{state['prompt']}\n\n已完成任务：\n{done_summary}\n\n"
                "请输出下一波待执行的子任务列表（JSON array）。"
            ),
        },
    ]

    try:
        response = await call(
            model=state.get("model_pref", "worker"),
            messages=messages,
        )
        content = response.choices[0].message.content or ""
        todo_items = _parse_todo(content, state.get("todo", []))
    except Exception:
        # Fallback: 创建一个默认 pm 任务
        todo_items = [_make_todo("执行用户任务：" + state["prompt"][:120], "pm")]

    updated_messages = (
        state.get("messages", [])
        + messages
        + [{"role": "assistant", "content": content if "content" in dir() else ""}]
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
    return {"todo": [*state.get("todo", []), *todo_items], "messages": updated_messages}


def _parse_todo(content: str, existing: list[TodoItem]) -> list[TodoItem]:
    """从 LLM 输出中提取 JSON 数组并构建 TodoItem 列表。"""
    existing_descriptions = {t["description"] for t in existing}

    # 先去掉 markdown code fence
    content = re.sub(r"```(?:json)?\s*", "", content).strip()

    # 找到最外层 '[' ... ']'（贪婪，处理嵌套）
    start = content.find("[")
    if start == -1:
        return [_make_todo("执行任务", "pm")]

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
        return [_make_todo("执行任务", "pm")]

    try:
        raw = json.loads(content[start:end])
    except json.JSONDecodeError:
        return [_make_todo("执行任务", "pm")]

    items: list[TodoItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        desc = entry.get("description", "").strip()
        if not desc:
            continue
        role = entry.get("role", entry.get("assigned_role", "pm"))
        if role not in {"pm", "designer", "frontend", "backend", "tester", "ops"}:
            role = "pm"
        item = _make_todo(desc, role)
        if item["description"] not in existing_descriptions:
            items.append(item)

    return items or [_make_todo("执行任务", "pm")]


def _make_todo(
    description: str,
    role: str = "pm",
    depends_on: list[str] | None = None,
) -> TodoItem:
    return TodoItem(
        id=shortuuid.uuid()[:8],
        description=description,
        status="pending",
        assigned_role=role,
        depends_on=depends_on or [],
        result=None,
    )


_PLANNER_SYSTEM = """\
你是项目经理，负责将用户任务拆解为可并行执行的子任务列表。

规则：
1. 每个子任务必须可独立执行（或通过 depends_on 声明依赖）
2. 最多 8 个子任务，最少 1 个
3. role 只能取：pm / designer / frontend / backend / tester / ops
4. 每个任务必须能在同一并行波次中独立执行
5. 只输出 JSON array，不要任何其他文字

输出格式：
[
  {"description": "任务描述", "role": "backend"},
  {"description": "另一个任务", "role": "tester"}
]
"""
