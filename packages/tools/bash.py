"""Opt-in local shell tool constrained to the configured workspace."""

from __future__ import annotations

import asyncio
import os
import signal
from contextlib import suppress
from pathlib import Path

from packages.tools.registry import register_tool

SCHEMA = {
    "name": "bash",
    "description": "在本地 workspace 中执行 shell 命令（必须显式启用）",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (max 120)",
                "default": 30,
            },
            "workdir": {
                "type": "string",
                "description": "Working directory (relative to workspace)",
                "default": ".",
            },
        },
        "required": ["command"],
    },
}

_WORKSPACE_ROOT = Path(
    os.getenv(
        "WORKSPACE_ROOT",
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "workspace"),
    )
).resolve()

# 禁止的危险命令前缀
_BLOCKED = ("rm -rf /", "mkfs", "dd if=", ":(){ :", "chmod -R 777 /", "sudo rm")


async def bash_handler(command: str, timeout: int = 30, workdir: str = ".") -> str:
    """执行 bash 命令。本地模式在 workspace 目录内运行。"""
    # 安全检查：阻止明显危险命令
    for blocked in _BLOCKED:
        if blocked in command:
            return f"Error: command blocked for safety: {blocked!r}"

    timeout = max(1, min(timeout, 120))

    if os.getenv("ALLOW_LOCAL_EXECUTION", "false").lower() != "true":
        return (
            "Error: local shell execution is disabled. "
            "Set ALLOW_LOCAL_EXECUTION=true only after reviewing SECURITY.md."
        )

    # 本地模式：在 workspace 中运行
    return await _bash_local(command, timeout, workdir)


async def _bash_local(command: str, timeout: int, workdir: str) -> str:
    """本地模式：在 workspace 子目录中执行命令。"""
    _WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    cwd = (_WORKSPACE_ROOT / workdir.lstrip("/")).resolve(strict=False)
    if cwd != _WORKSPACE_ROOT and _WORKSPACE_ROOT not in cwd.parents:
        return "Error: workdir path traversal blocked"

    cwd.mkdir(parents=True, exist_ok=True)
    clean_env = {
        "HOME": str(_WORKSPACE_ROOT),
        "LANG": os.getenv("LANG", "C.UTF-8"),
        "PATH": os.getenv("PATH", "/usr/bin:/bin"),
    }

    proc: asyncio.subprocess.Process | None = None
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env=clean_env,
            start_new_session=True,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode("utf-8", errors="replace") if stdout else ""
        return output[:8000] if len(output) > 8000 else output
    except TimeoutError:
        await _terminate_process_group(proc)
        return f"Error: command timed out after {timeout}s"
    except asyncio.CancelledError:
        await _terminate_process_group(proc)
        raise
    except Exception as exc:
        return f"Error: {exc}"


async def _terminate_process_group(proc: asyncio.subprocess.Process | None) -> None:
    """Terminate the shell and every child it started."""
    if proc is None or proc.returncode is not None:
        return
    with suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        await asyncio.wait_for(proc.wait(), timeout=0.5)
    except TimeoutError:
        with suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        await proc.wait()


register_tool("bash", SCHEMA, bash_handler)
