"""POST /api/tasks — 启动 / 列出 / 查询 swarm task。"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Literal

import shortuuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from packages.eventbus.publisher import emit_raw
from packages.orchestrator.benchmark import (
    BenchmarkReport,
    BenchmarkSpec,
    get_benchmark_report,
    run_benchmark_task,
)
from packages.orchestrator.graph import run_task
from packages.shared.schema import TaskInfo

router = APIRouter()

# 内存 task 注册表（本地单机模式）
_tasks: dict[str, TaskInfo] = {}
_task_handles: dict[str, asyncio.Task[None]] = {}
_TASK_HISTORY_LIMIT = 32


class TaskCreateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4_000)
    mode: Literal["demo", "auto", "single", "swarm", "benchmark"] = "demo"
    max_subagents: int = Field(default=4, ge=1, le=100)
    agent_count: int = Field(default=4, ge=1, le=100)
    exact_agent_count: bool = False
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    work_ms: int = Field(default=80, ge=1, le=1_000)
    failure_rate: float = Field(default=0.1, ge=0, le=0.5)
    max_steps_per_agent: int = Field(default=6, ge=1, le=20)
    max_total_model_calls: int = Field(default=500, ge=1, le=2_000)
    max_total_tool_calls: int = Field(default=500, ge=0, le=5_000)
    timeout_seconds: int = Field(default=900, ge=30, le=3_600)

    @model_validator(mode="after")
    def validate_demo_limit(self) -> TaskCreateRequest:
        if self.mode == "demo" and self.max_subagents > 8:
            raise ValueError("demo mode supports at most 8 concurrent subagents")
        return self


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str


class TaskCancelResponse(BaseModel):
    task_id: str
    status: str


@router.post("", response_model=TaskCreateResponse)
async def create_task(req: TaskCreateRequest):
    """启动一个新 task，后台运行 orchestrator。"""
    _validate_runtime_limits(req)
    task_id = shortuuid.uuid()
    info = TaskInfo(
        task_id=task_id,
        prompt=req.prompt,
        mode=req.mode,
        status="running",
        created_at=datetime.now(UTC).isoformat(),
    )
    _tasks[task_id] = info

    async def _run():
        try:
            demo_default = os.getenv("SWARM_DEMO_MODE", "true").lower() == "true"
            if req.mode == "benchmark":
                await run_benchmark_task(
                    task_id=task_id,
                    prompt=req.prompt,
                    spec=BenchmarkSpec(
                        agent_count=req.agent_count,
                        max_concurrency=req.max_subagents,
                        seed=req.seed,
                        work_ms=req.work_ms,
                        failure_rate=req.failure_rate,
                    ),
                )
            elif req.mode == "demo":
                from packages.orchestrator.demo import run_demo_task

                await run_demo_task(
                    task_id=task_id,
                    prompt=req.prompt,
                    max_subagents=req.max_subagents,
                )
            elif (
                demo_default
                and not all(os.getenv(name) for name in ("SWARM_MODEL", "SWARM_API_KEY"))
                and _runtime_profiles_missing()
            ):
                raise RuntimeError(
                    "No live provider is configured. Use demo mode or configure a provider."
                )
            else:
                await run_task(
                    task_id=task_id,
                    prompt=req.prompt,
                    mode=req.mode,
                    max_subagents=req.max_subagents,
                    agent_count=req.agent_count,
                    exact_agent_count=req.exact_agent_count,
                    max_steps_per_agent=req.max_steps_per_agent,
                    max_total_model_calls=req.max_total_model_calls,
                    max_total_tool_calls=req.max_total_tool_calls,
                    timeout_seconds=req.timeout_seconds,
                )
            _tasks[task_id] = TaskInfo(**{**info.model_dump(), "status": "completed"})
        except asyncio.CancelledError:
            _tasks[task_id] = TaskInfo(**{**info.model_dump(), "status": "cancelled"})
            await emit_raw(task_id, {"type": "task.cancelled"})
        except Exception as exc:
            _tasks[task_id] = TaskInfo(**{**info.model_dump(), "status": "failed"})
            await emit_raw(
                task_id,
                {
                    "type": "task.error",
                    "error_type": type(exc).__name__,
                },
            )
        finally:
            _task_handles.pop(task_id, None)
            _prune_task_history()

    _task_handles[task_id] = asyncio.create_task(_run(), name=f"swarm-task:{task_id}")
    return TaskCreateResponse(task_id=task_id, status="running")


@router.get("", response_model=list[TaskInfo])
async def list_tasks():
    """列出所有 tasks。"""
    return list(_tasks.values())


@router.get("/{task_id}/benchmark-report", response_model=BenchmarkReport)
async def get_task_benchmark_report(task_id: str):
    """Return evidence for a completed deterministic scale run."""
    report = get_benchmark_report(task_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark report for task {task_id!r} not found",
        )
    return report


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(task_id: str) -> TaskCancelResponse:
    """Cancel a running task and propagate cancellation to its agent tree."""
    info = _tasks.get(task_id)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id!r} not found",
        )
    handle = _task_handles.get(task_id)
    if handle is None or handle.done():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task {task_id!r} is not running",
        )
    _tasks[task_id] = TaskInfo(**{**info.model_dump(), "status": "cancelling"})
    handle.cancel()
    return TaskCancelResponse(task_id=task_id, status="cancelling")


@router.get("/{task_id}", response_model=TaskInfo)
async def get_task(task_id: str):
    """获取单个 task 状态。"""
    info = _tasks.get(task_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id!r} not found",
        )
    return info


def _runtime_profiles_missing() -> bool:
    from packages.llm_gateway.router import current_profiles

    return current_profiles() is None


def _validate_runtime_limits(req: TaskCreateRequest) -> None:
    if req.mode not in {"auto", "single", "swarm"}:
        return
    from packages.llm_gateway.router import current_profiles

    profiles = current_profiles()
    if profiles is None:
        return
    if req.agent_count > profiles.per_task_max_agents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"agent_count exceeds configured per-task limit ({profiles.per_task_max_agents})"
            ),
        )
    if req.max_subagents > profiles.global_max_parallel_requests:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "max_subagents exceeds configured global request limit "
                f"({profiles.global_max_parallel_requests})"
            ),
        )


async def cancel_all_tasks() -> None:
    """Cancel and join live task handles during API shutdown."""
    handles = list(_task_handles.values())
    for handle in handles:
        handle.cancel()
    if handles:
        await asyncio.gather(*handles, return_exceptions=True)


def _prune_task_history() -> None:
    """Keep only a bounded number of completed local task prompts in memory."""
    while len(_tasks) > _TASK_HISTORY_LIMIT:
        removable = next(
            (
                task_id
                for task_id, info in _tasks.items()
                if info.status in {"completed", "failed", "cancelled"}
            ),
            None,
        )
        if removable is None:
            return
        _tasks.pop(removable, None)
