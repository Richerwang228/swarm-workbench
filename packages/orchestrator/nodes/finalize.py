"""Hierarchical result reduction for single and large live swarms."""

from __future__ import annotations

import asyncio

from packages.orchestrator.state import OrchestratorState

_REDUCE_BATCH_SIZE = 10
_RESULT_CHARS = 4_000


async def finalize_node(state: OrchestratorState) -> dict:
    """Reduce up to 100 worker results without one oversized model context."""
    from packages.eventbus.publisher import emit_raw

    results = [
        {
            "agent_id": run["agent_id"],
            "role": run["role"],
            "result": run.get("result", "")[:_RESULT_CHARS],
        }
        for run in state.get("sub_agent_runs", [])
        if run["status"] == "done" and run.get("result")
    ]
    failed = [run for run in state.get("sub_agent_runs", []) if run["status"] == "failed"]

    if not results:
        final = "No agent completed successfully."
    elif len(results) == 1:
        final = results[0]["result"]
    else:
        chunks = [
            results[index : index + _REDUCE_BATCH_SIZE]
            for index in range(0, len(results), _REDUCE_BATCH_SIZE)
        ]
        partials = await asyncio.gather(
            *(_reduce_chunk(state, chunk, final=False) for chunk in chunks)
        )
        final = (
            partials[0]
            if len(partials) == 1
            else await _reduce_chunk(
                state,
                [
                    {"agent_id": f"group-{index + 1}", "role": "reducer", "result": result}
                    for index, result in enumerate(partials)
                ],
                final=True,
            )
        )

    if failed:
        final += f"\n\nCompleted with {len(failed)} failed agent(s)."

    await emit_raw(
        state["trace_id"],
        {
            "type": "agent.content.delta",
            "agent_id": "reducer",
            "content": final,
        },
    )
    return {"final_result": final}


async def _reduce_chunk(
    state: OrchestratorState,
    results: list[dict[str, str]],
    *,
    final: bool,
) -> str:
    from packages.llm_gateway.router import call

    body = "\n\n".join(
        f"[{item['agent_id']} · {item['role']}]\n{item['result']}" for item in results
    )
    instruction = (
        "Create the final answer for the user from the verified group summaries."
        if final
        else (
            "Compress these agent results. Preserve concrete findings, "
            "code references, and conflicts."
        )
    )
    try:
        response = await call(
            model=state.get("role_models", {}).get(
                "reducer",
                state.get("model_pref", "worker"),
            ),
            role="reducer",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the swarm reducer. Do not invent work that agents did not report. "
                        f"{instruction}"
                    ),
                },
                {"role": "user", "content": body},
            ],
            max_tokens=2_000,
        )
        content = response.choices[0].message.content or ""
        if content.strip():
            return content.strip()
    except Exception:
        pass
    return body
