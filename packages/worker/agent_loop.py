"""Budgeted agent loop: LLM → tool → repeat until done."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator


async def agent_loop(
    messages: list[dict],
    model: str = "worker",
    role: str | None = None,
    tool_budget: int = 50,
    max_steps: int = 50,
    agent_id: str = "",
) -> AsyncGenerator[dict, None]:
    """核心 agent loop。

    每轮：
    1. 流式调用 LLM（reasoning + content + tool_calls 三轨分流）
    2. 收集完整 tool_calls
    3. 并行执行所有 tool calls（isConcurrencySafe 分桶）
    4. 将结果追加到 messages，继续下轮
    5. 无 tool_calls → done
    """
    import packages.tools  # noqa: F401
    from packages.llm_gateway.router import call, model_supports_tools
    from packages.llm_gateway.stream_parser import parse_stream

    # 构建 tool schema 列表（只在第一次调用时构建）
    tool_schemas = _build_tool_schemas(role) if model_supports_tools(model, role) else []

    steps = 0
    max_steps = min(max_steps, max(1, tool_budget))
    while steps < max_steps:
        # ── 1. 调用 LLM ───────────────────────────────────────────────
        request: dict = {
            "model": model,
            "role": role,
            "messages": messages,
            "stream": True,
        }
        if tool_schemas:
            request.update({"tools": tool_schemas, "tool_choice": "auto"})
        stream = await call(**request)

        content_parts: list[str] = []
        tool_calls: list[dict] = []

        async for event in parse_stream(stream, agent_id=agent_id):
            yield event
            if event["type"] == "agent.content.delta":
                content_parts.append(event["content"])
            elif event["type"] == "agent.tool.calls":
                tool_calls = event["tool_calls"]

        full_content = "".join(content_parts)

        # 将助手回复追加到 messages
        assistant_msg: dict = {"role": "assistant", "content": full_content}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages = [*messages, assistant_msg]

        # ── 2. 无 tool calls → 结束 ───────────────────────────────────
        if not tool_calls:
            yield {"type": "agent.done", "content": full_content, "agent_id": agent_id}
            break

        # ── 3. 执行 tool calls ────────────────────────────────────────
        tool_messages = await _execute_tool_calls(tool_calls, agent_id)
        for event in tool_messages["events"]:
            yield event
        messages = [*messages, *tool_messages["messages"]]

        steps += 1

    if steps >= max_steps:
        yield {"type": "agent.step_budget_exceeded", "agent_id": agent_id}


async def _execute_tool_calls(tool_calls: list[dict], agent_id: str) -> dict:
    """并行执行 tool calls，返回事件列表和 tool result messages。"""
    from packages.orchestrator.budget import current_budget
    from packages.tools.registry import execute_tool

    if len(tool_calls) > 8:
        raise ValueError("an agent may request at most 8 tools in one model turn")
    if ledger := current_budget():
        await ledger.reserve_tool_calls(len(tool_calls))

    events: list[dict] = []
    result_messages: list[dict] = []

    async def _run_one(tc: dict) -> tuple[tuple[dict, dict], dict]:
        name = tc["function"]["name"]
        raw_args = tc["function"]["arguments"]
        tool_call_id = tc["id"]

        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            args = {}
        if len(json.dumps(args, ensure_ascii=False)) > 20_000:
            args = {}

        start_event = {
            "type": "agent.tool.call.start",
            "tool": name,
            "args": args,
            "tool_call_id": tool_call_id,
            "agent_id": agent_id,
        }

        try:
            result = await asyncio.wait_for(execute_tool(name, args), timeout=120)
            result_str = (
                result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
            )
            done_event = {
                "type": "agent.tool.result",
                "tool": name,
                "tool_call_id": tool_call_id,
                "result": result_str[:4000],
                "agent_id": agent_id,
            }
        except TimeoutError:
            result_str = "Error: tool execution timed out"
            done_event = {
                "type": "agent.tool.timeout",
                "tool": name,
                "tool_call_id": tool_call_id,
                "agent_id": agent_id,
            }
        except Exception as exc:
            result_str = f"Error: {type(exc).__name__}"
            done_event = {
                "type": "agent.tool.error",
                "tool": name,
                "tool_call_id": tool_call_id,
                "error_type": type(exc).__name__,
                "agent_id": agent_id,
            }

        msg = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result_str[:8_000],
        }
        return (start_event, done_event), msg

    tasks = [asyncio.create_task(_run_one(tc)) for tc in tool_calls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, BaseException):
            continue
        (start_ev, done_ev), msg = res
        events.append(start_ev)
        events.append(done_ev)
        result_messages.append(msg)

    return {"events": events, "messages": result_messages}


def _build_tool_schemas(role: str | None = None) -> list[dict]:
    """将 registry 中的 schema 转换为 OpenAI tool_choice 格式。"""
    import packages.tools  # noqa: F401
    from packages.tools.registry import get_tool_schema, list_tools

    schemas = []
    allowed = _ROLE_TOOLS.get(role) if role else None
    for name in list_tools():
        if allowed is not None and name not in allowed:
            continue
        schema = get_tool_schema(name)
        if schema:
            schemas.append({"type": "function", "function": schema})
    return schemas


_READ_TOOLS = {"file_read", "file_grep", "file_glob", "web_search"}
_TODO_TOOLS = {"todo_create", "todo_update", "todo_list"}
_WRITE_TOOLS = {"file_write", "file_edit"}
_ROLE_TOOLS = {
    "pm": _READ_TOOLS | _TODO_TOOLS,
    "designer": _READ_TOOLS | _TODO_TOOLS,
    "frontend": _READ_TOOLS | _TODO_TOOLS | _WRITE_TOOLS | {"bash"},
    "backend": _READ_TOOLS | _TODO_TOOLS | _WRITE_TOOLS | {"bash"},
    "tester": _READ_TOOLS | _TODO_TOOLS | {"bash"},
    "ops": _READ_TOOLS | _TODO_TOOLS | _WRITE_TOOLS | {"bash"},
}
