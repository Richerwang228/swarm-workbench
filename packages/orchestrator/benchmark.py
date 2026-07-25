"""Deterministic Swarm 100 benchmark and observable scale demonstration."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import random
import statistics
import time
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from packages.eventbus.publisher import emit_raw, emit_summary
from packages.orchestrator.capacity import get_capacity

ROLES = ("pm", "designer", "frontend", "backend", "tester", "ops")


class BenchmarkSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_count: int = Field(default=100, ge=1, le=100)
    max_concurrency: int = Field(default=8, ge=1, le=16)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    work_ms: int = Field(default=80, ge=1, le=1_000)
    failure_rate: float = Field(default=0.1, ge=0, le=0.5)


class BenchmarkReport(BaseModel):
    task_id: str
    simulated: bool = True
    agent_count: int
    completed: int
    failed: int
    recovered: int
    max_concurrency: int
    process_capacity: int
    peak_active: int
    process_peak_active: int
    elapsed_ms: float
    throughput_agents_s: float
    queue_wait_p50_ms: float
    queue_wait_p95_ms: float
    duration_p50_ms: float
    duration_p95_ms: float
    event_agents: int
    seed: int
    work_ms: int
    failure_rate: float
    semantic_sha256: str


@dataclass(frozen=True, slots=True)
class _AgentResult:
    agent_id: str
    role: str
    outcome: str
    recovered: bool
    attempts: int
    queue_wait_ms: float
    duration_ms: float

    def semantic(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "outcome": self.outcome,
            "recovered": self.recovered,
            "attempts": self.attempts,
        }


_reports: dict[str, BenchmarkReport] = {}


def get_benchmark_report(task_id: str) -> BenchmarkReport | None:
    return _reports.get(task_id)


def clear_benchmark_reports() -> None:
    _reports.clear()


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _agent_rng(seed: int, agent_id: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{agent_id}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


async def run_benchmark_task(
    task_id: str,
    prompt: str,
    spec: BenchmarkSpec | None = None,
) -> BenchmarkReport:
    """Run a deterministic logical-agent workload through bounded capacity."""
    spec = spec or BenchmarkSpec()
    process_capacity = get_capacity()
    local_slots = asyncio.Semaphore(spec.max_concurrency)
    run_started = time.monotonic_ns()
    active = 0
    peak_active = 0
    completed_count = 0
    recovered_count = 0
    counter_lock = asyncio.Lock()

    await emit_raw(
        task_id,
        {
            "type": "task.started",
            "prompt": prompt,
            "mode": "benchmark",
            "simulated": True,
        },
    )
    await emit_raw(
        task_id,
        {
            "type": "benchmark.started",
            "agent_count": spec.agent_count,
            "max_concurrency": spec.max_concurrency,
            "process_capacity": process_capacity.limit,
            "seed": spec.seed,
            "failure_rate": spec.failure_rate,
            "simulated": True,
        },
    )

    agents: list[tuple[str, str, str]] = []
    for index in range(1, spec.agent_count + 1):
        agent_id = f"agent-{index:03d}"
        role = ROLES[(index - 1) % len(ROLES)]
        todo_id = f"work-{index:03d}"
        agents.append((agent_id, role, todo_id))
        await emit_raw(
            task_id,
            {
                "type": "todo.update",
                "id": todo_id,
                "description": f"Scale workload shard {index:03d}",
                "status": "pending",
                "role": role,
                "depends_on": [],
            },
        )
        await emit_raw(
            task_id,
            {
                "type": "agent.spawned",
                "agent_id": agent_id,
                "role": role,
                "task": f"Process deterministic shard {index:03d}",
                "status": "spawned",
                "simulated": True,
            },
        )

    async def run_agent(agent_id: str, role: str, todo_id: str) -> _AgentResult:
        nonlocal active, peak_active, completed_count, recovered_count
        rng = _agent_rng(spec.seed, agent_id)
        fail_once = rng.random() < spec.failure_rate
        jitter_ms = rng.randint(0, max(1, spec.work_ms // 2))
        queued_at = time.monotonic_ns()

        async with local_slots, process_capacity.slot():
            queue_wait_ms = (time.monotonic_ns() - queued_at) / 1_000_000
            agent_started = time.monotonic_ns()
            async with counter_lock:
                active += 1
                peak_active = max(peak_active, active)
                current_active = active

            await emit_raw(
                task_id,
                {
                    "type": "todo.update",
                    "id": todo_id,
                    "description": todo_id.replace("-", " ").title(),
                    "status": "running",
                    "role": role,
                    "depends_on": [],
                },
            )
            await emit_summary(
                task_id,
                agent_id,
                "running",
                f"slot acquired · {current_active} active",
            )

            attempts = 2 if fail_once else 1
            for attempt in range(1, attempts + 1):
                await emit_raw(
                    task_id,
                    {
                        "type": "agent.tool.call.start",
                        "agent_id": agent_id,
                        "tool": "deterministic_workload",
                        "args": {"shard": todo_id, "attempt": attempt},
                    },
                )
                await asyncio.sleep((spec.work_ms + jitter_ms) / 1_000)
                if fail_once and attempt == 1:
                    await emit_raw(
                        task_id,
                        {
                            "type": "agent.retry.scheduled",
                            "agent_id": agent_id,
                            "attempt": attempt,
                            "next_attempt": 2,
                            "reason": "deterministic fail-once injection",
                        },
                    )
                    await emit_summary(task_id, agent_id, "running", "retrying after injection")
                    continue
                await emit_raw(
                    task_id,
                    {
                        "type": "agent.tool.result",
                        "agent_id": agent_id,
                        "tool": "deterministic_workload",
                        "result": f"{todo_id} verified on attempt {attempt}",
                    },
                )

            await emit_raw(
                task_id,
                {
                    "type": "todo.update",
                    "id": todo_id,
                    "description": todo_id.replace("-", " ").title(),
                    "status": "done",
                    "role": role,
                    "depends_on": [],
                },
            )
            await emit_raw(
                task_id,
                {
                    "type": "agent.done",
                    "agent_id": agent_id,
                    "role": role,
                    "content": f"{todo_id} completed",
                    "recovered": fail_once,
                    "attempts": attempts,
                },
            )
            await emit_summary(
                task_id,
                agent_id,
                "done",
                "recovered" if fail_once else "completed",
            )

            duration_ms = (time.monotonic_ns() - agent_started) / 1_000_000
            async with counter_lock:
                active -= 1
                completed_count += 1
                recovered_count += int(fail_once)
                current_completed = completed_count
                current_recovered = recovered_count

            if current_completed == 1 or current_completed % 5 == 0:
                snapshot = process_capacity.snapshot()
                await emit_raw(
                    task_id,
                    {
                        "type": "benchmark.progress",
                        "agent_count": spec.agent_count,
                        "completed": current_completed,
                        "active": active,
                        "queued": spec.agent_count - current_completed - active,
                        "recovered": current_recovered,
                        "peak_active": peak_active,
                        "process_active": snapshot.active,
                        "simulated": True,
                    },
                )

            return _AgentResult(
                agent_id=agent_id,
                role=role,
                outcome="completed",
                recovered=fail_once,
                attempts=attempts,
                queue_wait_ms=queue_wait_ms,
                duration_ms=duration_ms,
            )

    results = await asyncio.gather(*(run_agent(*agent) for agent in agents))
    elapsed_ms = (time.monotonic_ns() - run_started) / 1_000_000
    stable_results = sorted(
        (result.semantic() for result in results),
        key=lambda item: str(item["agent_id"]),
    )
    semantic_json = json.dumps(stable_results, sort_keys=True, separators=(",", ":"))
    process_snapshot = process_capacity.snapshot()
    queue_waits = [result.queue_wait_ms for result in results]
    durations = [result.duration_ms for result in results]

    report = BenchmarkReport(
        task_id=task_id,
        agent_count=spec.agent_count,
        completed=len(results),
        failed=0,
        recovered=sum(result.recovered for result in results),
        max_concurrency=spec.max_concurrency,
        process_capacity=process_capacity.limit,
        peak_active=peak_active,
        process_peak_active=process_snapshot.peak_active,
        elapsed_ms=round(elapsed_ms, 3),
        throughput_agents_s=round(len(results) / max(elapsed_ms / 1_000, 0.001), 3),
        queue_wait_p50_ms=round(statistics.median(queue_waits), 3),
        queue_wait_p95_ms=round(_percentile(queue_waits, 0.95), 3),
        duration_p50_ms=round(statistics.median(durations), 3),
        duration_p95_ms=round(_percentile(durations, 0.95), 3),
        event_agents=len(results),
        seed=spec.seed,
        work_ms=spec.work_ms,
        failure_rate=spec.failure_rate,
        semantic_sha256=hashlib.sha256(semantic_json.encode()).hexdigest(),
    )
    _reports[task_id] = report

    await emit_raw(task_id, {"type": "benchmark.completed", **report.model_dump()})
    final = (
        f"Swarm 100 simulated benchmark completed {report.completed}/{report.agent_count} "
        f"logical agents with peak concurrency {report.peak_active}. "
        f"{report.recovered} deterministic failures recovered. "
        f"Semantic trace: {report.semantic_sha256[:12]}."
    )
    await emit_raw(
        task_id,
        {
            "type": "agent.content.delta",
            "agent_id": "benchmark-reducer",
            "content": final,
        },
    )
    await emit_raw(
        task_id,
        {
            "type": "task.completed",
            "result": final,
            "simulated": True,
        },
    )
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deterministic Swarm 100 benchmark.")
    parser.add_argument("--agents", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--work-ms", type=int, default=20)
    parser.add_argument("--failure-rate", type=float, default=0.1)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    spec = BenchmarkSpec(
        agent_count=args.agents,
        max_concurrency=args.concurrency,
        seed=args.seed,
        work_ms=args.work_ms,
        failure_rate=args.failure_rate,
    )
    report = asyncio.run(run_benchmark_task("benchmark-cli", "CLI scale benchmark", spec))
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
