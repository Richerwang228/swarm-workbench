"""Route node — 智能分级：判断任务该用单 agent 还是 swarm。"""

from __future__ import annotations

from packages.orchestrator.state import OrchestratorState


async def route_node(state: OrchestratorState) -> dict:
    """用最便宜的模型判断任务路由。"""
    mode = state.get("mode", "auto")
    if mode != "auto":
        return {"route_decision": mode}

    from packages.llm_gateway.router import call

    try:
        response = await call(
            model="worker",
            messages=[
                {"role": "system", "content": _ROUTE_SYSTEM},
                {"role": "user", "content": state["prompt"]},
            ],
        )
        content = (response.choices[0].message.content or "").strip().lower()
        for decision in ("single", "swarm", "clarify"):
            if decision in content:
                return {"route_decision": decision}
    except Exception:
        pass

    # Fail predictably when the inexpensive classifier is unavailable.
    prompt = state["prompt"]
    complex_markers = (" and ", "并且", "同时", "分别", "compare", "research")
    decision = (
        "swarm"
        if len(prompt) > 180 or any(m in prompt.lower() for m in complex_markers)
        else "single"
    )
    return {"route_decision": decision}


_ROUTE_SYSTEM = """判断以下任务应该用哪种模式处理：
- single: 简单任务，1 个 agent 即可
- swarm: 复杂并行任务，需要多个 sub-agent
- clarify: 意图不清，需要反问用户

只输出一个词：single / swarm / clarify"""
