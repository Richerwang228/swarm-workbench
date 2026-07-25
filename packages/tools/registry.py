"""Tool 注册中心 — 统一管理所有工具的注册和调度。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolSpec:
    handler: Callable
    schema: dict
    max_concurrency: int
    side_effect: bool


_registry: dict[str, ToolSpec] = {}
_limits: dict[str, asyncio.Semaphore] = {}
_side_effect_limit: asyncio.Semaphore | None = None
_DEFAULT_CONCURRENCY = {
    "bash": 1,
    "file_write": 1,
    "file_edit": 1,
    "web_search": 8,
}


def register_tool(
    name: str,
    schema: dict,
    handler: Callable,
    *,
    max_concurrency: int | None = None,
    side_effect: bool = False,
):
    """注册一个工具。"""
    limit = max_concurrency or _DEFAULT_CONCURRENCY.get(name, 32)
    _registry[name] = ToolSpec(
        handler=handler,
        schema=schema,
        max_concurrency=max(1, min(limit, 100)),
        side_effect=side_effect or name in {"bash", "file_write", "file_edit"},
    )
    _limits.pop(name, None)


def get_tool_schema(name: str) -> dict | None:
    """获取工具 schema。"""
    spec = _registry.get(name)
    return spec.schema if spec is not None else None


def list_tools() -> list[str]:
    """列出所有已注册工具。"""
    return list(_registry.keys())


async def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
    """执行指定工具。ValueError / TypeError 转成错误字符串（不上抛）。"""
    spec = _registry.get(name)
    if spec is None:
        return f"Error: Unknown tool: {name}"
    semaphore = _limits.setdefault(name, asyncio.Semaphore(spec.max_concurrency))
    try:
        async with semaphore:
            if not spec.side_effect:
                return await spec.handler(**arguments)
            # Different mutating tools can still target the same workspace
            # path. Stay conservative until path locks/worktree isolation exist.
            global _side_effect_limit
            if _side_effect_limit is None:
                _side_effect_limit = asyncio.Semaphore(1)
            async with _side_effect_limit:
                return await spec.handler(**arguments)
    except (ValueError, TypeError) as exc:
        return f"Error: {exc}"
