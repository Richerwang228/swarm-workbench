"""POST /api/tasks — 启动 / 列出 / 查询 swarm task。"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Literal

import shortuuid
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from packages.orchestrator.graph import run_task
from packages.shared.schema import TaskInfo

router = APIRouter()

# 内存 task 注册表（本地单机模式）
_tasks: dict[str, TaskInfo] = {}


class TaskCreateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4_000)
    mode: Literal["demo", "auto", "single", "swarm"] = "demo"
    max_subagents: int = Field(default=4, ge=1, le=8)


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str


@router.post("", response_model=TaskCreateResponse)
async def create_task(req: TaskCreateRequest, bg: BackgroundTasks):
    """启动一个新 task，后台运行 orchestrator。"""
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
            if req.mode == "demo":
                from packages.orchestrator.demo import run_demo_task

                await run_demo_task(
                    task_id=task_id,
                    prompt=req.prompt,
                    max_subagents=req.max_subagents,
                )
            elif demo_default and not all(
                os.getenv(name) for name in ("SWARM_MODEL", "SWARM_API_BASE", "SWARM_API_KEY")
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
                )
            _tasks[task_id] = TaskInfo(**{**info.model_dump(), "status": "completed"})
        except Exception:
            _tasks[task_id] = TaskInfo(**{**info.model_dump(), "status": "failed"})

    bg.add_task(_run)
    return TaskCreateResponse(task_id=task_id, status="running")


@router.get("", response_model=list[TaskInfo])
async def list_tasks():
    """列出所有 tasks。"""
    return list(_tasks.values())


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
