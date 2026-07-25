"""Stream parser — OpenAI 兼容增量装配（reasoning + content + tool_calls）。"""

from __future__ import annotations

from collections.abc import AsyncGenerator


async def parse_stream(stream, agent_id: str = "") -> AsyncGenerator[dict, None]:
    """解析 LLM 流式响应，分轨输出 reasoning / content / tool_calls。

    处理三种 reasoning 字段名：reasoning_content / thinking / (none)
    处理 fragmented tool_calls（中转站兼容性）
    """
    tool_call_buffers: dict[int, dict] = {}

    async for chunk in stream:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        # Reasoning content (多字段名兼容)
        reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "thinking", None)
        if reasoning:
            yield {"type": "agent.reasoning.delta", "content": reasoning, "agent_id": agent_id}

        # Main content
        if delta.content:
            yield {"type": "agent.content.delta", "content": delta.content, "agent_id": agent_id}

        # Tool calls (buffer fragmented chunks)
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_call_buffers:
                    tool_call_buffers[idx] = {
                        "id": tc.id or "",
                        "function": {"name": "", "arguments": ""},
                    }
                if tc.id:
                    tool_call_buffers[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_call_buffers[idx]["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_call_buffers[idx]["function"]["arguments"] += tc.function.arguments

        # Finish reason
        if chunk.choices[0].finish_reason == "tool_calls":
            yield {
                "type": "agent.tool.calls",
                "tool_calls": list(tool_call_buffers.values()),
                "agent_id": agent_id,
            }
            tool_call_buffers.clear()
