"""Swarm API — FastAPI entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from apps.api.routes import providers, stream, tasks


def _cors_origins() -> list[str]:
    configured = os.getenv(
        "SWARM_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    # Construct the configured LiteLLM router without making a billable request.
    from packages.llm_gateway.router import prewarm

    await prewarm()
    yield
    await tasks.cancel_all_tasks()


app = FastAPI(
    title="Swarm API",
    version="0.2.0-beta.2",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Last-Event-ID"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost", "::1", "test", "testserver"],
)

app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(stream.router, prefix="/api/stream", tags=["stream"])
app.include_router(providers.router, prefix="/api/providers", tags=["providers"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return validation locations/messages without echoing submitted secrets."""
    del request
    errors = [
        {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


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
