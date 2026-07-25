"""Unit tests — eventbus publish/subscribe fan-out。"""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress

import pytest

from packages.eventbus._queue import get_bus, reset_broker
from packages.eventbus.publisher import emit_raw, emit_summary
from packages.eventbus.subscriber import subscribe


@pytest.fixture(autouse=True)
def _clean_broker():
    reset_broker()
    yield
    reset_broker()


@pytest.mark.asyncio
async def test_bus_publish_single_subscriber():
    bus = get_bus("test.single")
    q = await bus.subscribe()

    await bus.publish(json.dumps({"hello": "world"}))

    raw = await asyncio.wait_for(q.get(), timeout=1)
    data = json.loads(raw)
    assert data["hello"] == "world"

    await bus.unsubscribe(q)


@pytest.mark.asyncio
async def test_bus_fanout_two_subscribers():
    bus = get_bus("test.fanout")
    q1 = await bus.subscribe()
    q2 = await bus.subscribe()

    await bus.publish(json.dumps({"msg": "broadcast"}))

    d1 = json.loads(await asyncio.wait_for(q1.get(), timeout=1))
    d2 = json.loads(await asyncio.wait_for(q2.get(), timeout=1))

    assert d1["msg"] == "broadcast"
    assert d2["msg"] == "broadcast"

    await bus.unsubscribe(q1)
    await bus.unsubscribe(q2)


@pytest.mark.asyncio
async def test_emit_raw_and_subscribe():
    task_id = "unit-test-task"
    subject = f"swarm.events.{task_id}.raw"

    received: list[dict] = []

    async def _consume():
        async for event in subscribe(subject, timeout=1.0):
            received.append(event.data)

    # Start subscriber before emitting
    consumer = asyncio.create_task(_consume())
    await asyncio.sleep(0.05)  # allow subscription to register

    await emit_raw(task_id, {"type": "test.event", "value": 42})

    with suppress(TimeoutError):
        await asyncio.wait_for(consumer, timeout=2.0)

    assert any(r.get("value") == 42 for r in received)


@pytest.mark.asyncio
async def test_wildcard_subscription_receives_raw_and_summary_topics():
    task_id = "wildcard-task"
    stream = subscribe(f"swarm.events.{task_id}.>", timeout=0.1)

    await emit_raw(task_id, {"type": "task.started"})
    await emit_summary(task_id, "agent-1", "running", "planning")

    received = [event async for event in stream]

    assert [event.type for event in received] == ["task.started", "agent.update"]


@pytest.mark.asyncio
async def test_subscription_replays_events_published_before_connect():
    task_id = "replay-task"
    await emit_raw(task_id, {"type": "task.started"})
    await emit_raw(task_id, {"type": "task.completed"})

    received = [event async for event in subscribe(f"swarm.events.{task_id}.>", timeout=0.05)]

    assert [event.type for event in received] == ["task.started", "task.completed"]


@pytest.mark.asyncio
async def test_last_event_id_replays_only_newer_events():
    task_id = "resume-task"
    await emit_raw(task_id, {"type": "task.started"})
    first = [event async for event in subscribe(f"swarm.events.{task_id}.>", timeout=0.05)][0]
    await emit_raw(task_id, {"type": "task.completed"})

    resumed = [
        event
        async for event in subscribe(
            f"swarm.events.{task_id}.>",
            start_from=first.id,
            timeout=0.05,
        )
    ]

    assert [event.type for event in resumed] == ["task.completed"]


@pytest.mark.asyncio
async def test_event_envelope_does_not_overwrite_domain_id():
    task_id = "domain-id-task"
    await emit_raw(
        task_id,
        {
            "type": "todo.update",
            "id": "todo-123",
            "status": "pending",
        },
    )

    event = [item async for item in subscribe(f"swarm.events.{task_id}.>", timeout=0.05)][0]

    assert event.id.startswith(f"{task_id}.")
    assert event.data["id"] == "todo-123"
    assert event.data["event_id"] == event.id
