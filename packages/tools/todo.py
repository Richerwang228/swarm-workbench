"""Todo tool — sub-agent 用来创建/更新 todo items。

Todo 存储在内存 store（本地模式），key = task_id。
"""

from __future__ import annotations

import asyncio

import shortuuid

from packages.tools.registry import register_tool

# 内存存储：task_id → list[TodoItem dict]
_store: dict[str, list[dict]] = {}
_lock = asyncio.Lock()


async def _todo_create(
    description: str, role: str = "pm", depends_on: list[str] | None = None, task_id: str = ""
) -> str:
    item = {
        "id": shortuuid.uuid()[:8],
        "description": description,
        "status": "pending",
        "assigned_role": role,
        "depends_on": depends_on or [],
        "result": None,
    }
    async with _lock:
        _store.setdefault(task_id, []).append(item)
    return f"Created todo {item['id']!r}: {description[:60]}"


register_tool(
    "todo_create",
    {
        "name": "todo_create",
        "description": "创建一个 todo 子任务",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "任务描述"},
                "role": {"type": "string", "description": "执行角色", "default": "pm"},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "依赖的 todo id",
                },
                "task_id": {"type": "string", "description": "父任务 id", "default": ""},
            },
            "required": ["description"],
        },
    },
    _todo_create,
)


async def _todo_update(
    todo_id: str, status: str, result: str | None = None, task_id: str = ""
) -> str:
    valid = ("pending", "running", "done", "failed")
    if status not in valid:
        return f"Error: invalid status {status!r}, must be one of {valid}"

    async with _lock:
        items = _store.get(task_id, [])
        for item in items:
            if item["id"] == todo_id:
                item["status"] = status
                if result is not None:
                    item["result"] = result
                return f"Updated todo {todo_id!r} → {status}"
    return f"Error: todo {todo_id!r} not found"


register_tool(
    "todo_update",
    {
        "name": "todo_update",
        "description": "更新 todo item 状态",
        "parameters": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "string", "description": "todo item 的 id"},
                "status": {"type": "string", "enum": ["pending", "running", "done", "failed"]},
                "result": {"type": "string", "description": "执行结果摘要"},
                "task_id": {"type": "string", "description": "父任务 id", "default": ""},
            },
            "required": ["todo_id", "status"],
        },
    },
    _todo_update,
)


async def _todo_list(task_id: str = "") -> str:
    async with _lock:
        items = _store.get(task_id, [])
    if not items:
        return "No todos"
    lines = []
    for t in items:
        symbol = {"done": "x", "running": "-", "failed": "!"}.get(t["status"], " ")
        lines.append(f"[{symbol}] {t['id']} ({t['assigned_role']}): {t['description'][:60]}")
    return "\n".join(lines)


register_tool(
    "todo_list",
    {
        "name": "todo_list",
        "description": "列出当前任务的所有 todo items",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "父任务 id", "default": ""},
            },
        },
    },
    _todo_list,
)


def get_todos(task_id: str) -> list[dict]:
    """外部访问接口：获取某个 task 的所有 todos。"""
    return list(_store.get(task_id, []))
