"""Local-only runtime provider and role-model configuration."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from packages.llm_gateway.profiles import RuntimeProfiles
from packages.llm_gateway.router import (
    call,
    configure,
    get_router,
    public_profiles,
    reset_router,
    resolve_model,
)

router = APIRouter()


class ProviderTestRequest(BaseModel):
    model_route: str = Field(min_length=3, max_length=65)


class ProviderTestResponse(BaseModel):
    ok: bool
    model_route: str
    latency_ms: float


@router.get("")
async def get_provider_profiles() -> dict[str, object]:
    """Return provider metadata with all credentials removed."""
    profiles = public_profiles()
    return {"configured": profiles is not None, "profiles": profiles}


@router.put("")
async def put_provider_profiles(profiles: RuntimeProfiles) -> dict[str, object]:
    """Install provider credentials in this API process only."""
    # Environment names are process authority, not browser input. Accepting an
    # arbitrary name here could forward an unrelated process secret upstream.
    if any(provider.api_key_env is not None for provider in profiles.providers):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="api_key_env is only supported by trusted startup configuration",
        )
    try:
        await _validate_resolved_addresses(profiles)
        public = configure(profiles)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        # A concurrent task may temporarily hold the process-wide capacity.
        # Keep the response generic: provider libraries must never get a chance
        # to reflect connection parameters or credentials through this endpoint.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider configuration cannot be changed while work is running",
        ) from exc
    return {
        "configured": True,
        "profiles": public,
        "credential_persistence": "process-memory-only",
    }


@router.delete("")
async def delete_provider_profiles() -> dict[str, object]:
    """Forget all process-memory credentials and return to environment config."""
    from packages.orchestrator.capacity import get_capacity, reset_capacity

    snapshot = get_capacity().snapshot()
    if snapshot.active or snapshot.queued:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider configuration cannot be cleared while work is running",
        )

    reset_router()
    reset_capacity()
    return {"configured": False, "credential_persistence": "cleared"}


@router.post("/test", response_model=ProviderTestResponse)
async def test_provider_route(req: ProviderTestRequest) -> ProviderTestResponse:
    """Make a small, explicit provider request to verify a selected route."""
    if req.model_route not in get_router().model_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown model route",
        )
    started = time.monotonic_ns()
    try:
        await call(
            model=resolve_model(req.model_route),
            messages=[{"role": "user", "content": "Reply with OK."}],
            max_tokens=4,
            timeout=30,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider test failed: {type(exc).__name__}",
        ) from exc
    return ProviderTestResponse(
        ok=True,
        model_route=req.model_route,
        latency_ms=round((time.monotonic_ns() - started) / 1_000_000, 3),
    )


async def _validate_resolved_addresses(profiles: RuntimeProfiles) -> None:
    """Reject custom hostnames that currently resolve to non-public networks."""
    loop = asyncio.get_running_loop()
    for provider in profiles.providers:
        if provider.api_base is None or provider.allow_private_network:
            continue
        parsed = urlsplit(provider.api_base)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            addresses = await loop.getaddrinfo(
                parsed.hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise ValueError(f"provider {provider.id!r} hostname could not be resolved") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise ValueError(
                    f"provider {provider.id!r} resolves to a non-public address; "
                    "private-network mode must be explicitly enabled"
                )
