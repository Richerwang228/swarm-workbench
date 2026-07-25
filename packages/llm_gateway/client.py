"""OpenAI-compatible streaming client."""

from __future__ import annotations

import os

import openai

_client: openai.AsyncOpenAI | None = None


def get_client() -> openai.AsyncOpenAI:
    """获取 OpenAI 兼容客户端（连 LiteLLM 或直连 provider）。"""
    global _client
    if _client is None:
        base_url = os.getenv("SWARM_API_BASE")
        api_key = os.getenv("SWARM_API_KEY")
        if not base_url or not api_key:
            raise RuntimeError("Live mode requires SWARM_API_BASE and SWARM_API_KEY.")
        _client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)
    return _client
