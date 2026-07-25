"""GET /api/stream/{task_id} — SSE 事件流。"""

from __future__ import annotations

from fastapi import APIRouter, Header, Request
from sse_starlette.sse import EventSourceResponse

from packages.eventbus.subscriber import subscribe

router = APIRouter()


@router.get("/{task_id}")
async def stream(task_id: str, request: Request, last_event_id: str = Header(None)):
    """SSE 多路复用：单连接接收所有 sub-agent 事件。"""

    async def event_generator():
        async for event in subscribe(f"swarm.events.{task_id}.>", start_from=last_event_id):
            if await request.is_disconnected():
                break
            yield {
                "id": event.id,
                "data": event.to_sse(),
            }

    return EventSourceResponse(event_generator())
