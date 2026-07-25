"""Provider configuration API does not disclose credentials."""

from __future__ import annotations

import httpx
import pytest

from apps.api.main import app
from packages.llm_gateway.router import reset_router
from packages.orchestrator.capacity import get_capacity, reset_capacity


@pytest.fixture(autouse=True)
def _reset_router():
    reset_router()
    reset_capacity()
    yield
    reset_router()
    reset_capacity()


def _payload(api_key: str = "sk-api-secret-value") -> dict:
    return {
        "providers": [
            {
                "id": "primary",
                "label": "Primary",
                "kind": "openai",
                "api_key": api_key,
                "models": [{"id": "fast", "model": "test-model"}],
            }
        ],
        "role_models": {
            role: "primary:fast"
            for role in (
                "planner",
                "pm",
                "designer",
                "frontend",
                "backend",
                "tester",
                "ops",
                "reducer",
                "summarizer",
            )
        },
        "default_model": "primary:fast",
        "global_max_parallel_requests": 8,
        "per_task_max_agents": 100,
    }


@pytest.mark.asyncio
async def test_provider_config_round_trip_is_redacted():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        configured = await client.put("/api/providers", json=_payload())
        fetched = await client.get("/api/providers")

    assert configured.status_code == 200
    assert fetched.status_code == 200
    for response in (configured, fetched):
        assert "sk-api-secret-value" not in response.text
        assert response.json()["profiles"]["providers"][0]["has_api_key"] is True


@pytest.mark.asyncio
async def test_validation_error_does_not_echo_api_key():
    payload = _payload("sk-must-never-be-echoed")
    payload["providers"][0]["api_base"] = "ftp://invalid.example"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/api/providers", json=payload)

    assert response.status_code == 422
    assert "sk-must-never-be-echoed" not in response.text
    assert all("input" not in error for error in response.json()["detail"])


@pytest.mark.asyncio
async def test_browser_cannot_select_a_process_environment_secret(monkeypatch):
    monkeypatch.setenv("UNRELATED_PROCESS_SECRET", "must-not-leave-the-process")
    payload = _payload()
    payload["providers"][0].pop("api_key")
    payload["providers"][0]["api_key_env"] = "UNRELATED_PROCESS_SECRET"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/api/providers", json=payload)

    assert response.status_code == 422
    assert "must-not-leave-the-process" not in response.text
    assert "api_key_env" in response.text


@pytest.mark.asyncio
async def test_provider_configuration_cannot_be_cleared_while_agents_hold_capacity():
    transport = httpx.ASGITransport(app=app)
    async with (
        get_capacity().slot(),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.delete("/api/providers")

    assert response.status_code == 409
