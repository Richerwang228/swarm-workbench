"""Integration evidence for the deterministic Swarm 100 benchmark."""

from __future__ import annotations

import asyncio
from collections import Counter

import pytest

from packages.eventbus._queue import reset_broker
from packages.eventbus.subscriber import subscribe
from packages.orchestrator.benchmark import (
    BenchmarkSpec,
    clear_benchmark_reports,
    run_benchmark_task,
)
from packages.orchestrator.capacity import get_capacity, reset_capacity


@pytest.fixture(autouse=True)
def _reset_benchmark_runtime():
    reset_broker()
    clear_benchmark_reports()
    reset_capacity(8)
    yield
    reset_broker()
    clear_benchmark_reports()
    reset_capacity(8)


async def _replayed_events(task_id: str):
    return [
        event
        async for event in subscribe(
            f"swarm.events.{task_id}.>",
            timeout=0.02,
        )
    ]


@pytest.mark.asyncio
async def test_swarm_100_completes_with_bounded_peak_and_complete_trace():
    agent_count = 100
    concurrency_cap = 7
    reset_capacity(8)
    report = await run_benchmark_task(
        "benchmark-100",
        "Exercise one hundred deterministic logical agents",
        BenchmarkSpec(
            agent_count=agent_count,
            max_concurrency=concurrency_cap,
            seed=42,
            work_ms=2,
            failure_rate=0,
        ),
    )

    events = await _replayed_events("benchmark-100")
    event_counts = Counter(event.type for event in events)
    spawned_ids = {event.data["agent_id"] for event in events if event.type == "agent.spawned"}
    done_ids = {event.data["agent_id"] for event in events if event.type == "agent.done"}

    assert report.agent_count == agent_count
    assert report.completed == agent_count
    assert report.failed == 0
    assert report.event_agents == agent_count
    assert report.peak_active == concurrency_cap
    assert report.peak_active <= report.max_concurrency
    assert report.process_peak_active <= report.process_capacity
    assert len(spawned_ids) == agent_count
    assert done_ids == spawned_ids

    assert event_counts == {
        "task.started": 1,
        "benchmark.started": 1,
        "todo.update": 3 * agent_count,
        "agent.spawned": agent_count,
        "agent.update": 2 * agent_count,
        "agent.tool.call.start": agent_count,
        "agent.tool.result": agent_count,
        "agent.done": agent_count,
        "benchmark.progress": 1 + agent_count // 5,
        "benchmark.completed": 1,
        "agent.content.delta": 1,
        "task.completed": 1,
    }


@pytest.mark.asyncio
async def test_identical_seed_produces_identical_semantic_hash():
    spec = BenchmarkSpec(
        agent_count=100,
        max_concurrency=8,
        seed=20260726,
        work_ms=1,
        failure_rate=0.2,
    )

    first = await run_benchmark_task("determinism-a", "Same semantic workload", spec)
    second = await run_benchmark_task("determinism-b", "Same semantic workload", spec)

    assert first.semantic_sha256 == second.semantic_sha256
    assert first.recovered == second.recovered
    assert first.completed == second.completed == 100


@pytest.mark.asyncio
async def test_process_capacity_is_shared_across_parallel_runs(monkeypatch):
    process_cap = 3
    run_count = 4
    agents_per_run = 25
    monkeypatch.setenv("SWARM_GLOBAL_AGENT_CAP", str(process_cap))
    reset_capacity(process_cap)
    spec = BenchmarkSpec(
        agent_count=agents_per_run,
        max_concurrency=8,
        seed=7,
        work_ms=3,
        failure_rate=0,
    )

    reports = await asyncio.gather(
        *(
            run_benchmark_task(
                f"parallel-{index}",
                f"Parallel benchmark run {index}",
                spec,
            )
            for index in range(run_count)
        )
    )
    snapshot = get_capacity().snapshot()

    assert snapshot.peak_active == process_cap
    assert snapshot.peak_active <= snapshot.limit
    assert snapshot.active == 0
    assert snapshot.queued == 0
    assert snapshot.total_acquired == run_count * agents_per_run
    assert all(report.completed == agents_per_run for report in reports)
    assert all(report.process_peak_active <= process_cap for report in reports)


@pytest.mark.asyncio
async def test_injected_failures_recover_without_losing_terminal_events():
    agent_count = 100
    report = await run_benchmark_task(
        "benchmark-recovery",
        "Recover deterministic fail-once agents",
        BenchmarkSpec(
            agent_count=agent_count,
            max_concurrency=8,
            seed=99,
            work_ms=1,
            failure_rate=0.35,
        ),
    )
    events = await _replayed_events("benchmark-recovery")
    event_counts = Counter(event.type for event in events)
    recovered_done = [
        event for event in events if event.type == "agent.done" and event.data["recovered"]
    ]
    snapshot = get_capacity().snapshot()

    assert 0 < report.recovered < agent_count
    assert report.completed == agent_count
    assert report.failed == 0
    assert len(recovered_done) == report.recovered
    assert event_counts["agent.retry.scheduled"] == report.recovered
    assert event_counts["agent.tool.call.start"] == agent_count + report.recovered
    assert event_counts["agent.tool.result"] == agent_count
    assert event_counts["agent.done"] == agent_count
    assert snapshot.active == 0
    assert snapshot.queued == 0
