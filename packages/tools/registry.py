"""Tool 注册中心 — 统一管理所有工具的注册和调度。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_registry: dict[str, Callable] = {}
_schemas: dict[str, dict] = {}


def register_tool(name: str, schema: dict, handler: Callable):
    """注册一个工具。"""
    _registry[name] = handler
    _schemas[name] = schema


def get_tool_schema(name: str) -> dict | None:
    """获取工具 schema。"""
    return _schemas.get(name)


def list_tools() -> list[str]:
    """列出所有已注册工具。"""
    return list(_registry.keys())


async def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
    """执行指定工具。ValueError / TypeError 转成错误字符串（不上抛）。"""
    handler = _registry.get(name)
    if handler is None:
        return f"Error: Unknown tool: {name}"
    try:
        return await handler(**arguments)
    except (ValueError, TypeError) as exc:
        return f"Error: {exc}"
