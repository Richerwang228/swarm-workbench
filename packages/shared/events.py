"""SSE event schema — SwarmEvent 是所有 SSE 事件的信封。"""

from __future__ import annotations

import json

from pydantic import BaseModel


class SwarmEvent(BaseModel):
    id: str
    type: str
    data: dict

    def to_sse(self) -> str:
        """序列化为 SSE data 字段（JSON 字符串）。"""
        return json.dumps(self.data, ensure_ascii=False)


# 常用事件类型常量
class EventType:
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_ERROR = "task.error"

    AGENT_SPAWNED = "agent.spawned"
    AGENT_UPDATE = "agent.update"
    AGENT_DONE = "agent.done"

    REASONING_DELTA = "agent.reasoning.delta"
    CONTENT_DELTA = "agent.content.delta"

    TOOL_CALL_START = "agent.tool.call.start"
    TOOL_RESULT = "agent.tool.result"
    TOOL_TIMEOUT = "agent.tool.timeout"
    TOOL_ERROR = "agent.tool.error"

    TODO_UPDATE = "todo.update"
    STEP_BUDGET_EXCEEDED = "agent.step_budget_exceeded"
