"""End-to-end tests for the deterministic public demo path."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.api.routes.tasks import TaskCreateRequest
from packages.eventbus._queue import reset_broker
from packages.eventbus.subscriber import subscribe
from packages.orchestrator.demo import run_demo_task


@pytest.fixture(autouse=True)
def _clean_broker():
    reset_broker()
    yield
    reset_broker()


@pytest.mark.asyncio
async def test_demo_emits_complete_observable_trace():
    task_id = "demo-integration"
    result = await run_demo_task(task_id, "Prepare a portfolio release", max_subagents=2)

    events = [event async for event in subscribe(f"swarm.events.{task_id}.>", timeout=0.05)]
    types = [event.type for event in events]

    assert types[0] == "task.started"
    assert types[-1] == "task.completed"
    assert types.count("agent.spawned") == 4
    assert types.count("agent.done") == 4
    assert types.count("todo.update") == 12
    assert "simulated locally" in result


@pytest.mark.asyncio
async def test_demo_respects_concurrency_limit():
    task_id = "demo-concurrency"
    await run_demo_task(task_id, "Check bounded execution", max_subagents=2)
    events = [event async for event in subscribe(f"swarm.events.{task_id}.>", timeout=0.05)]

    active = 0
    peak = 0
    for event in events:
        if event.type == "agent.spawned":
            active += 1
            peak = max(peak, active)
        elif event.type == "agent.done":
            active -= 1

    assert peak == 2
    assert active == 0


@pytest.mark.parametrize(
    ("payload", "invalid_field"),
    [
        ({"prompt": "x", "mode": "demo"}, "prompt"),
        ({"prompt": "valid prompt", "mode": "unknown"}, "mode"),
        ({"prompt": "valid prompt", "mode": "demo", "max_subagents": 0}, "max_subagents"),
        ({"prompt": "valid prompt", "mode": "demo", "max_subagents": 9}, "max_subagents"),
    ],
)
def test_task_request_rejects_unsafe_or_invalid_values(payload, invalid_field):
    with pytest.raises(ValidationError) as exc:
        TaskCreateRequest.model_validate(payload)

    assert invalid_field in str(exc.value)
