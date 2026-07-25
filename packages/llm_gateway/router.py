"""Atomic multi-provider LiteLLM router with redacted runtime configuration."""

from __future__ import annotations

import os
from contextlib import suppress
from typing import Any, cast

from litellm import Router

from packages.llm_gateway.profiles import ProviderProfile, RuntimeProfiles, route_id

_router: Router | None = None
_profiles: RuntimeProfiles | None = None

_PROVIDER_PREFIX = {
    "openai_compatible": "openai",
    "openai": "openai",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "openrouter": "openrouter",
    "ollama": "ollama",
    "azure": "azure",
}


def _qualified_model(provider: ProviderProfile, model: str) -> str:
    prefix = _PROVIDER_PREFIX[provider.kind]
    if model.startswith(f"{prefix}/"):
        return model
    return f"{prefix}/{model}"


def _build_model_list(profiles: RuntimeProfiles) -> list[dict[str, Any]]:
    deployments: list[dict[str, Any]] = []
    for provider in profiles.providers:
        secret = provider.secret_value()
        if provider.kind != "ollama" and not secret:
            source = provider.api_key_env or "inline secret"
            raise ValueError(f"provider {provider.id!r} has no value for {source}")
        for model in provider.models:
            params: dict[str, Any] = {
                "model": _qualified_model(provider, model.model),
                "max_parallel_requests": model.max_parallel_requests,
            }
            if secret is not None:
                params["api_key"] = secret
            if provider.api_base is not None:
                params["api_base"] = provider.api_base
            if provider.api_version is not None:
                params["api_version"] = provider.api_version
            if model.rpm is not None:
                params["rpm"] = model.rpm
            if model.tpm is not None:
                params["tpm"] = model.tpm
            deployments.append(
                {
                    "model_name": route_id(provider.id, model.id),
                    "litellm_params": params,
                    "model_info": {
                        "provider_id": provider.id,
                        "model_profile_id": model.id,
                    },
                }
            )
    return deployments


def configure(profiles: RuntimeProfiles) -> dict[str, object]:
    """Validate and atomically install an in-memory provider configuration."""
    global _profiles, _router
    candidate = Router(
        model_list=_build_model_list(profiles),
        routing_strategy="simple-shuffle",
        enable_pre_call_checks=True,
        default_max_parallel_requests=profiles.global_max_parallel_requests,
        num_retries=profiles.max_retries,
        retry_after=1,
        timeout=profiles.request_timeout_seconds,
        allowed_fails=3,
        cooldown_time=15,
    )
    from packages.orchestrator.capacity import configure_capacity

    configure_capacity(profiles.global_max_parallel_requests)
    _profiles = profiles
    _router = candidate
    return profiles.public_view()


def current_profiles() -> RuntimeProfiles | None:
    return _profiles


def public_profiles() -> dict[str, object] | None:
    return _profiles.public_view() if _profiles is not None else None


def _load_legacy_router() -> Router:
    api_key = os.getenv("SWARM_API_KEY")
    model = os.getenv("SWARM_MODEL")
    if not api_key or not model:
        raise RuntimeError("No LLM providers configured. Add a provider or configure .env.")
    params: dict[str, Any] = {"model": model, "api_key": api_key}
    if api_base := os.getenv("SWARM_API_BASE"):
        params["api_base"] = api_base
    return Router(
        model_list=[{"model_name": "worker", "litellm_params": params}],
        enable_pre_call_checks=True,
        default_max_parallel_requests=8,
        num_retries=2,
        retry_after=1,
    )


def get_router() -> Router:
    """Return the configured router, falling back to legacy environment values."""
    global _router
    if _router is None:
        _router = _load_legacy_router()
    return _router


def resolve_model(model: str, role: str | None = None) -> str:
    """Resolve a trusted role or alias to a configured provider:model route."""
    if _profiles is None:
        return model
    if model in get_router().model_names:
        return model
    if role is not None and role in _profiles.role_models:
        return _profiles.role_models[cast(Any, role)]
    return _profiles.default_model


def model_supports_tools(model: str, role: str | None = None) -> bool:
    """Return declared tool capability for a configured route."""
    if _profiles is None:
        return True
    resolved = resolve_model(model, role)
    for provider in _profiles.providers:
        for profile in provider.models:
            if route_id(provider.id, profile.id) == resolved:
                return profile.supports_tools
    return False


async def call(
    model: str,
    messages: list[dict],
    *,
    role: str | None = None,
    **kwargs: Any,
) -> Any:
    """Call a configured model without exposing provider credentials downstream."""
    from packages.orchestrator.budget import current_budget

    if ledger := current_budget():
        await ledger.reserve_model_call()
    router = get_router()
    timeout = kwargs.pop(
        "timeout",
        _profiles.request_timeout_seconds if _profiles is not None else 300,
    )
    return await router.acompletion(
        model=resolve_model(model, role),
        messages=cast(Any, messages),
        timeout=timeout,
        **kwargs,
    )


async def prewarm() -> None:
    """Validate configuration shape without making a paid model request."""
    with suppress(Exception):
        _ = get_router().model_names


async def health() -> dict[str, object]:
    """Return redacted model-routing health."""
    try:
        router = get_router()
        models = router.model_names
        return {
            "status": "ok",
            "models_loaded": len(models),
            "models": models,
            "runtime_profiles": _profiles is not None,
        }
    except Exception as exc:
        return {"status": "error", "error_type": type(exc).__name__}


def reset_router() -> None:
    """Clear router state. Intended for tests and local reconfiguration."""
    global _profiles, _router
    _profiles = None
    _router = None
