"""Config loader — 从 swarm.yaml 读取运行时配置。"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

_config: dict | None = None

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "swarm.yaml"


def load_config(path: str | Path | None = None) -> dict:
    """加载 swarm.yaml 配置。"""
    global _config
    if _config is not None:
        return _config

    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return _defaults()

    with open(config_path, encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config


def get_config() -> dict:
    """获取当前配置（懒加载）。"""
    return load_config()


def get_max_subagents() -> int:
    """获取最大并发 sub-agent 数。"""
    env_val = os.getenv("MAX_CONCURRENT_SUBAGENTS")
    if env_val:
        return int(env_val)
    return get_config().get("defaults", {}).get("max_subagents", 5)


def get_step_budget() -> int:
    """获取 step budget。"""
    return get_config().get("defaults", {}).get("step_budget", 50)


def get_daily_budget() -> float:
    """获取每日花费上限。"""
    return get_config().get("budget", {}).get("daily_max_usd", 3.0)


def get_role_config(role: str) -> dict:
    """获取角色配置。"""
    roles = get_config().get("roles", {})
    return roles.get(role, {"model": "worker", "system_prompt": ""})


def _defaults() -> dict:
    """默认配置（当 swarm.yaml 不存在时使用）。"""
    return {
        "version": 1,
        "defaults": {
            "model": "worker",
            "max_subagents": 5,
            "step_budget": 50,
        },
        "budget": {
            "daily_max_usd": 3.0,
            "per_task_max_usd": 0.5,
        },
    }
