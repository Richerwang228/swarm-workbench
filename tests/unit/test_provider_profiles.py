"""Provider configuration security and role-routing contracts."""

from __future__ import annotations

from typing import Any, cast

import pytest
from pydantic import ValidationError

from packages.llm_gateway.profiles import RuntimeProfiles


def _payload() -> dict:
    return {
        "providers": [
            {
                "id": "primary",
                "label": "Primary",
                "kind": "openai_compatible",
                "api_base": "https://models.example/v1",
                "api_key": "sk-test-not-a-real-key",
                "models": [
                    {
                        "id": "coding",
                        "model": "example-coder",
                        "max_parallel_requests": 20,
                        "rpm": 600,
                    }
                ],
            }
        ],
        "role_models": {
            role: "primary:coding"
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
        "default_model": "primary:coding",
        "global_max_parallel_requests": 100,
        "per_task_max_agents": 100,
    }


def test_public_profiles_never_contain_inline_secret():
    profiles = RuntimeProfiles.model_validate(_payload())

    public = profiles.public_view()
    rendered = str(public)
    providers = cast(list[dict[str, Any]], public["providers"])

    assert "sk-test-not-a-real-key" not in rendered
    assert providers[0]["has_api_key"] is True
    assert "api_key" not in providers[0]


@pytest.mark.parametrize(
    ("api_base", "allow_private_network"),
    [
        ("http://models.example/v1", False),
        ("http://127.0.0.1:8000/v1", False),
        ("http://169.254.169.254/latest", False),
        ("ftp://models.example/v1", False),
        ("https://user:password@models.example/v1", False),
    ],
)
def test_unsafe_provider_endpoint_is_rejected(
    api_base: str,
    allow_private_network: bool,
):
    payload = _payload()
    payload["providers"][0]["api_base"] = api_base
    payload["providers"][0]["allow_private_network"] = allow_private_network

    with pytest.raises(ValidationError):
        RuntimeProfiles.model_validate(payload)


def test_explicit_local_provider_mode_is_supported():
    payload = _payload()
    payload["providers"][0].update(
        {
            "kind": "ollama",
            "api_base": "http://127.0.0.1:11434",
            "api_key": None,
            "allow_private_network": True,
        }
    )

    profiles = RuntimeProfiles.model_validate(payload)

    assert profiles.providers[0].kind == "ollama"


def test_role_route_must_reference_configured_model():
    payload = _payload()
    payload["role_models"]["backend"] = "missing:model"

    with pytest.raises(ValidationError, match="unknown model routes"):
        RuntimeProfiles.model_validate(payload)
