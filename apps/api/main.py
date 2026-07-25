"""Swarm API — FastAPI entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import stream, tasks


def _cors_origins() -> list[str]:
    configured = os.getenv(
        "SWARM_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    # Pre-warm LiteLLM router (1-token call to each healthy provider)
    from packages.llm_gateway.router import prewarm

    await prewarm()
    yield


app = FastAPI(
    title="Swarm API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Last-Event-ID"],
)

app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(stream.router, prefix="/api/stream", tags=["stream"])


@app.get("/api/health")
async def health_check():
    """System health check — shows status of all subsystems."""
    from packages.llm_gateway.router import health as llm_health

    llm = await llm_health()
    demo_mode = os.getenv("SWARM_DEMO_MODE", "true").lower() == "true"
    return {
        "mode": "demo" if demo_mode else "live",
        "llm": llm,
        "isolation": {
            "status": "local-only",
            "host_shell_enabled": os.getenv("ALLOW_LOCAL_EXECUTION", "false").lower() == "true",
        },
        "capabilities": {
            "demo": True,
            "live_providers": llm.get("status") == "ok",
            "local_shell": os.getenv("ALLOW_LOCAL_EXECUTION", "false").lower() == "true",
            "durable_checkpoints": False,
        },
        "status": "ok" if demo_mode or llm.get("status") == "ok" else "degraded",
    }
