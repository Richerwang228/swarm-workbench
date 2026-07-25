"""Compact node — 4-layer 上下文压缩（inspired by Claude Code compaction）。"""

from __future__ import annotations

from packages.orchestrator.state import OrchestratorState

# 模型上下文上限：128K tokens（保守值）
_MODEL_LIMIT = 128_000
# 触发压缩的阈值：60%
_THRESHOLD = 0.6


async def compact_node(state: OrchestratorState) -> dict:
    """按需压缩 messages，防止上下文炸裂。

    Layer 1: snip  — 截断超长 tool result（>2000 字符）
    Layer 2: micro — 用廉价模型摘要旧轮次
    Layer 3: collapse — 合并连续 assistant 消息
    Layer 4: full  — 全量摘要（极端情况）
    """
    messages = state.get("messages", [])
    token_count = _estimate_tokens(messages)

    if token_count < _THRESHOLD * _MODEL_LIMIT:
        return {}  # 不需要压缩

    # Layer 1: snip tool results
    messages = _snip_tool_results(messages, max_chars=2000)
    token_count = _estimate_tokens(messages)

    # Layer 2: micro compact (摘要中间轮次，保留首尾)
    if token_count > _THRESHOLD * _MODEL_LIMIT:
        messages = await _micro_compact(messages, state)
        token_count = _estimate_tokens(messages)

    # Layer 3: collapse consecutive assistant turns
    if token_count > _THRESHOLD * _MODEL_LIMIT:
        messages = _collapse_consecutive(messages)
        token_count = _estimate_tokens(messages)

    # Layer 4: full summarize
    if token_count > _THRESHOLD * _MODEL_LIMIT:
        messages = await _full_summarize(messages, state)

    return {"messages": messages}


def _estimate_tokens(messages: list[dict]) -> int:
    """粗略估算 token 数：平均 1 token ≈ 3 字符（中英混合）。"""
    total = sum(len(msg.get("content") or "") for msg in messages)
    return total // 3


def _snip_tool_results(messages: list[dict], max_chars: int = 2000) -> list[dict]:
    """截断过长的 tool result，保留头尾。"""
    result = []
    for msg in messages:
        content = msg.get("content") or ""
        if msg.get("role") == "tool" and len(content) > max_chars:
            head = content[:500]
            tail = content[-200:]
            snipped = f"{head}\n\n...[{len(content) - 700} chars snipped]...\n\n{tail}"
            result.append({**msg, "content": snipped})
        else:
            result.append(msg)
    return result


async def _micro_compact(messages: list[dict], state: OrchestratorState) -> list[dict]:
    """保留首 2 条和末 4 条，摘要中间轮次。"""
    from packages.llm_gateway.router import call

    if len(messages) <= 6:
        return messages

    head = messages[:2]
    tail = messages[-4:]
    middle = messages[2:-4]

    middle_text = "\n".join(f"[{m['role']}]: {str(m.get('content', ''))[:300]}" for m in middle)

    try:
        resp = await call(
            model="worker",
            messages=[
                {
                    "role": "system",
                    "content": "请用中文摘要以下对话历史，保留关键决策和结果，100字以内。",
                },
                {"role": "user", "content": middle_text},
            ],
        )
        summary = resp.choices[0].message.content or "(摘要失败)"
    except Exception:
        summary = f"[已压缩 {len(middle)} 轮对话]"

    summary_msg = {"role": "system", "content": f"[历史摘要] {summary}"}
    return [*head, summary_msg, *tail]


def _collapse_consecutive(messages: list[dict]) -> list[dict]:
    """合并连续的同角色消息。"""
    if not messages:
        return messages

    collapsed: list[dict] = [messages[0]]
    for msg in messages[1:]:
        last = collapsed[-1]
        if msg.get("role") == last.get("role") and msg.get("role") == "assistant":
            merged_content = f"{last.get('content', '')}\n{msg.get('content', '')}"
            collapsed[-1] = {**last, "content": merged_content}
        else:
            collapsed.append(msg)
    return collapsed


async def _full_summarize(messages: list[dict], state: OrchestratorState) -> list[dict]:
    """极端情况：将全部历史压缩成一条摘要 system message。"""
    from packages.llm_gateway.router import call

    full_text = "\n".join(f"[{m['role']}]: {str(m.get('content', ''))[:500]}" for m in messages)

    try:
        resp = await call(
            model="worker",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "请用中文摘要以下完整对话历史，保留关键决策、文件路径、"
                        "代码片段和最终结论，200字以内。"
                    ),
                },
                {"role": "user", "content": full_text[:8000]},
            ],
        )
        summary = resp.choices[0].message.content or "(全量摘要失败)"
    except Exception:
        summary = f"[已压缩 {len(messages)} 条历史消息]"

    # 只保留 system prompt 和摘要
    system_msgs = [m for m in messages if m.get("role") == "system"][:1]
    return [*system_msgs, {"role": "system", "content": f"[全量摘要] {summary}"}]
