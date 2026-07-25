"""Unit tests — stream_parser 解析 reasoning / content / tool_calls。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from packages.llm_gateway.stream_parser import parse_stream


def _make_chunk(content=None, reasoning=None, tool_calls=None, finish_reason=None):
    """构造 Mock LLM chunk。"""
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = tool_calls

    # 支持 reasoning_content / thinking 两种字段名
    delta.reasoning_content = reasoning
    delta.thinking = None

    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta = delta
    chunk.choices[0].finish_reason = finish_reason
    return chunk


async def _stream_from_chunks(chunks):
    for c in chunks:
        yield c


@pytest.mark.asyncio
async def test_parse_content_delta():
    chunks = [
        _make_chunk(content="Hello "),
        _make_chunk(content="World"),
    ]
    events = []
    async for ev in parse_stream(_stream_from_chunks(chunks)):
        events.append(ev)

    content_events = [e for e in events if e["type"] == "agent.content.delta"]
    assert len(content_events) == 2
    assert content_events[0]["content"] == "Hello "
    assert content_events[1]["content"] == "World"


@pytest.mark.asyncio
async def test_parse_reasoning_delta():
    chunks = [_make_chunk(reasoning="I am thinking...")]
    events = []
    async for ev in parse_stream(_stream_from_chunks(chunks)):
        events.append(ev)

    reasoning_events = [e for e in events if e["type"] == "agent.reasoning.delta"]
    assert len(reasoning_events) == 1
    assert "thinking" in reasoning_events[0]["content"]


@pytest.mark.asyncio
async def test_parse_tool_calls():
    tc = MagicMock()
    tc.index = 0
    tc.id = "call_abc"
    tc.function = MagicMock()
    tc.function.name = "bash"
    tc.function.arguments = '{"command": "ls"}'

    chunk_with_tools = _make_chunk(tool_calls=[tc], finish_reason="tool_calls")

    events = []
    async for ev in parse_stream(_stream_from_chunks([chunk_with_tools])):
        events.append(ev)

    tool_events = [e for e in events if e["type"] == "agent.tool.calls"]
    assert len(tool_events) == 1
    assert tool_events[0]["tool_calls"][0]["function"]["name"] == "bash"
