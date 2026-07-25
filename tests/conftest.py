"""Test fixtures for the swarm backend."""

from __future__ import annotations

import pytest

# ── 环境变量 Mock ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """提供基础环境变量，防止测试依赖真实 API key。"""
    monkeypatch.setenv("SWARM_MODEL", "openai/test-model")
    monkeypatch.setenv("SWARM_API_BASE", "https://example.invalid/v1")
    monkeypatch.setenv("SWARM_API_KEY", "test-provider-key")
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("WORKSPACE_ROOT", "/tmp/swarm-test-workspace")


@pytest.fixture
def anyio_backend():
    return "asyncio"
