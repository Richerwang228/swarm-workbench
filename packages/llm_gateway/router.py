"""LiteLLM router for one user-configured OpenAI-compatible provider."""

from __future__ import annotations

import os
from typing import Any, cast

from litellm import Router

_router: Router | None = None


def _load_model_list() -> list[dict]:
    """Load a generic provider without embedding vendor-specific assumptions."""
    api_key = os.getenv("SWARM_API_KEY")
    model = os.getenv("SWARM_MODEL")
    if not api_key or not model:
        return []

    params: dict[str, Any] = {"model": model, "api_key": api_key}
    if api_base := os.getenv("SWARM_API_BASE"):
        params["api_base"] = api_base
    return [{"model_name": "worker", "litellm_params": params}]


def get_router() -> Router:
    """获取或创建 LiteLLM Router 单例。"""
    global _router
    if _router is None:
        model_list = _load_model_list()
        if not model_list:
            raise RuntimeError("No LLM providers configured. Check .env file.")
        _router = Router(
            model_list=model_list,
            enable_pre_call_checks=True,
            num_retries=2,
        )
    return _router


async def call(model: str, messages: list[dict], **kwargs):
    """调用 LLM — 业务代码只指定模型名，路由自动处理。"""
    router = get_router()
    return await router.acompletion(
        model=model,
        messages=cast(Any, messages),
        timeout=kwargs.pop("timeout", 300),
        **kwargs,
    )


async def prewarm():
    """Validate provider configuration without making a paid model request."""
    try:
        router = get_router()
        # Just access the router to trigger lazy init
        _ = router.model_names
    except Exception:
        pass


async def health() -> dict:
    """LLM 子系统健康检查。"""
    try:
        router = get_router()
        models = router.model_names
        return {"status": "ok", "models_loaded": len(models), "models": models}
    except Exception as e:
        return {"status": "error", "error": str(e)}
