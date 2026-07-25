"""Pydantic models — 共享数据模型。"""

from __future__ import annotations

from pydantic import BaseModel


class TaskInfo(BaseModel):
    task_id: str
    prompt: str
    mode: str = "demo"
    status: str = "pending"
    created_at: str = ""
    current_step: int = 0
    step_budget: int = 50
    todo_count: int = 0
    todo_done: int = 0


class SubAgentInfo(BaseModel):
    agent_id: str
    role: str
    task: str
    status: str = "spawned"
    model: str = ""
    tool_calls: int = 0
    tokens_used: int = 0


class HealthStatus(BaseModel):
    llm: dict
    sandbox: dict
    status: str = "ok"
