"""Validated multi-provider and role-routing configuration.

Secrets may be supplied for the current process or referenced by environment
variable. Public representations never include secret values.
"""

from __future__ import annotations

import ipaddress
import os
import re
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

ProviderKind = Literal[
    "openai_compatible",
    "openai",
    "anthropic",
    "gemini",
    "openrouter",
    "ollama",
    "azure",
]

RoleName = Literal[
    "planner",
    "pm",
    "designer",
    "frontend",
    "backend",
    "tester",
    "ops",
    "reducer",
    "summarizer",
]

ROLE_NAMES: tuple[RoleName, ...] = (
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

Slug = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")]


class ModelProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: Slug
    model: str = Field(min_length=1, max_length=200)
    max_parallel_requests: int = Field(default=8, ge=1, le=100)
    rpm: int | None = Field(default=None, ge=1, le=1_000_000)
    tpm: int | None = Field(default=None, ge=1, le=100_000_000)
    supports_tools: bool = True


class ProviderProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: Slug
    label: str = Field(min_length=1, max_length=80)
    kind: ProviderKind = "openai_compatible"
    api_base: str | None = Field(default=None, max_length=2_048)
    api_key: SecretStr | None = Field(default=None, repr=False)
    api_key_env: str | None = Field(default=None, max_length=128)
    api_version: str | None = Field(default=None, max_length=64)
    allow_private_network: bool = False
    models: list[ModelProfile] = Field(min_length=1, max_length=32)

    @field_validator("api_key_env")
    @classmethod
    def validate_env_name(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", value):
            raise ValueError("api_key_env must be an uppercase environment variable name")
        return value

    @field_validator("api_base")
    @classmethod
    def validate_api_base(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("api_base must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ValueError("api_base must not contain credentials")
        if parsed.query or parsed.fragment:
            raise ValueError("api_base must not contain a query or fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_secret_and_network(self) -> ProviderProfile:
        if self.api_key is not None and self.api_key_env is not None:
            raise ValueError("provide api_key or api_key_env, not both")
        if self.kind not in {"ollama"} and self.api_key is None and self.api_key_env is None:
            raise ValueError("this provider requires api_key or api_key_env")
        if self.kind in {"openai", "anthropic", "gemini", "openrouter"} and self.api_base:
            raise ValueError(
                "native provider kinds use LiteLLM's official endpoint; "
                "use openai_compatible for a custom base URL"
            )
        if self.api_base:
            parsed = urlsplit(self.api_base)
            hostname = parsed.hostname or ""
            private_host = _is_literal_private_host(hostname)
            if parsed.scheme == "http" and not private_host:
                raise ValueError("remote api_base URLs must use HTTPS")
            if private_host and not self.allow_private_network and self.kind != "ollama":
                raise ValueError("private or loopback api_base requires allow_private_network=true")
        model_ids = [model.id for model in self.models]
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("model ids must be unique within a provider")
        return self

    def secret_value(self) -> str | None:
        if self.api_key is not None:
            return self.api_key.get_secret_value()
        if self.api_key_env is not None:
            return os.getenv(self.api_key_env)
        return None


class RuntimeProfiles(BaseModel):
    model_config = ConfigDict(frozen=True)

    providers: list[ProviderProfile] = Field(min_length=1, max_length=16)
    role_models: dict[RoleName, str]
    default_model: str
    global_max_parallel_requests: int = Field(default=8, ge=1, le=100)
    per_task_max_agents: int = Field(default=8, ge=1, le=100)
    request_timeout_seconds: int = Field(default=120, ge=5, le=600)
    max_retries: int = Field(default=2, ge=0, le=6)

    @model_validator(mode="after")
    def validate_routes(self) -> RuntimeProfiles:
        provider_ids = [provider.id for provider in self.providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider ids must be unique")

        routes = {
            route_id(provider.id, model.id)
            for provider in self.providers
            for model in provider.models
        }
        referenced = {self.default_model, *self.role_models.values()}
        missing_roles = sorted(set(ROLE_NAMES) - self.role_models.keys())
        if missing_roles:
            raise ValueError(f"missing role model routes: {', '.join(missing_roles)}")
        unknown = sorted(referenced - routes)
        if unknown:
            raise ValueError(f"unknown model routes: {', '.join(unknown)}")
        return self

    def public_view(self) -> dict[str, object]:
        payload = self.model_dump(exclude={"providers": {"__all__": {"api_key"}}})
        providers = payload["providers"]
        assert isinstance(providers, list)
        for index, provider in enumerate(self.providers):
            item = providers[index]
            assert isinstance(item, dict)
            item["has_api_key"] = provider.secret_value() is not None
        return payload


def route_id(provider_id: str, model_id: str) -> str:
    return f"{provider_id}:{model_id}"


def _is_literal_private_host(hostname: str) -> bool:
    if hostname.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )
