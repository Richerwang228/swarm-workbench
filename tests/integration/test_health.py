"""Health endpoint capability reporting."""

from __future__ import annotations

import pytest

from apps.api.main import health_check


@pytest.mark.asyncio
async def test_demo_health_is_ready_without_live_provider(monkeypatch):
    monkeypatch.setenv("SWARM_DEMO_MODE", "true")
    monkeypatch.delenv("ALLOW_LOCAL_EXECUTION", raising=False)
    monkeypatch.setattr(
        "packages.llm_gateway.router.health",
        lambda: _async_value({"status": "error", "error": "not configured"}),
    )

    health = await health_check()

    assert health["status"] == "ok"
    assert health["mode"] == "demo"
    assert health["capabilities"]["demo"] is True
    assert health["capabilities"]["live_providers"] is False
    assert health["capabilities"]["local_shell"] is False


async def _async_value(value):
    return value
