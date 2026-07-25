"""Task cancellation propagates to the live coroutine tree."""

from __future__ import annotations

import asyncio

import pytest

from apps.api.routes import tasks as task_routes
from apps.api.routes.tasks import TaskCreateRequest, cancel_task, create_task, get_task
from packages.eventbus._queue import reset_broker
from packages.eventbus.subscriber import subscribe
from packages.llm_gateway.router import reset_router


@pytest.fixture(autouse=True)
async def _clean_tasks():
    await task_routes.cancel_all_tasks()
    task_routes._tasks.clear()
    reset_broker()
    reset_router()
    yield
    await task_routes.cancel_all_tasks()
    task_routes._tasks.clear()
    reset_broker()
    reset_router()


@pytest.mark.asyncio
async def test_cancel_marks_task_and_emits_terminal_event(monkeypatch):
    started = asyncio.Event()

    async def long_running_task(*_args, **_kwargs):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(task_routes, "run_task", long_running_task)

    created = await create_task(
        TaskCreateRequest(
            prompt="Run a cancellable live swarm",
            mode="swarm",
            agent_count=20,
            max_subagents=4,
        )
    )
    await asyncio.wait_for(started.wait(), timeout=1)

    response = await cancel_task(created.task_id)
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    task = await get_task(created.task_id)
    events = [
        event
        async for event in subscribe(
            f"swarm.events.{created.task_id}.>",
            timeout=0.05,
        )
    ]

    assert response.status == "cancelling"
    assert task.status == "cancelled"
    assert events[-1].type == "task.cancelled"
    assert created.task_id not in task_routes._task_handles
