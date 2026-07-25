"""Mock-provider proof for the real live-agent scheduling path."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from packages.eventbus._queue import reset_broker
from packages.eventbus.subscriber import subscribe
from packages.orchestrator import graph as graph_module
from packages.orchestrator.capacity import get_capacity, reset_capacity
from packages.orchestrator.graph import run_task

ROLES = ("pm", "designer", "frontend", "backend", "tester", "ops")


@pytest.fixture(autouse=True)
def _reset_runtime():
    reset_broker()
    reset_capacity(7)
    graph_module._graph = None
    yield
    reset_broker()
    reset_capacity()
    graph_module._graph = None


def _response(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.mark.asyncio
async def test_live_scheduler_runs_one_fixed_100_agent_plan_with_role_routes(monkeypatch):
    planner_calls = 0
    worker_routes: list[tuple[str, str]] = []
    active = 0
    peak = 0
    lock = asyncio.Lock()

    plan = [
        {
            "key": f"shard-{index:03d}",
            "description": f"Perform useful shard {index:03d}",
            "role": ROLES[(index - 1) % len(ROLES)],
            "depends_on": [],
        }
        for index in range(1, 101)
    ]

    async def fake_call(*_args, role: str | None = None, **_kwargs):
        nonlocal planner_calls
        if role == "planner":
            planner_calls += 1
            return _response(json.dumps(plan))
        return _response("Combined verified results")

    async def fake_worker(*, role: str, model: str, agent_id: str, **_kwargs):
        nonlocal active, peak
        worker_routes.append((role, model))
        async with lock:
            active += 1
            peak = max(peak, active)
        await asyncio.sleep(0.001)
        async with lock:
            active -= 1
        yield {
            "type": "agent.done",
            "agent_id": agent_id,
            "content": f"completed by {model}",
        }

    role_models = {role: f"provider:{role}" for role in ROLES}
    role_models.update(
        {
            "planner": "provider:planner",
            "reducer": "provider:reducer",
        }
    )
    profiles = SimpleNamespace(role_models=role_models, default_model="provider:default")

    monkeypatch.setattr("packages.llm_gateway.router.call", fake_call)
    monkeypatch.setattr("packages.llm_gateway.router.current_profiles", lambda: profiles)
    monkeypatch.setattr("packages.worker.runner.run_worker", fake_worker)

    await run_task(
        "live-100",
        "Run a fixed 100-agent research plan",
        mode="swarm",
        max_subagents=13,
        agent_count=100,
        exact_agent_count=True,
    )
    events = [event async for event in subscribe("swarm.events.live-100.>", timeout=0.05)]

    spawned = [event for event in events if event.type == "agent.spawned"]
    terminal = [
        event for event in events if event.type == "agent.update" and event.data["status"] == "done"
    ]

    assert planner_calls == 1
    assert len(spawned) == 100
    assert len({event.data["agent_id"] for event in spawned}) == 100
    assert len(terminal) == 100
    assert len(worker_routes) == 100
    assert all(model == role_models[role] for role, model in worker_routes)
    assert peak == 7
    assert get_capacity().snapshot().active == 0
    assert events[-1].type == "task.completed"
    assert events[-1].data["result"] == "Combined verified results"
