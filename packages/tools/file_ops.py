"""File operations tool — read / write / edit / grep / glob。

在沙箱 worktree 路径下操作，路径不能逃逸到 / 以上。
"""

from __future__ import annotations

import glob as _glob
import os
import re
from pathlib import Path

from packages.tools.registry import register_tool

# 沙箱根目录（本地模式用 ./data/workspace）
_WORKSPACE_ROOT = Path(
    os.getenv(
        "WORKSPACE_ROOT",
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "workspace"),
    )
).resolve()


def _is_contained(path: Path) -> bool:
    return path == _WORKSPACE_ROOT or _WORKSPACE_ROOT in path.parents


def _safe_path(path: str) -> Path:
    """Resolve a path and reject traversal and existing symlink escapes."""
    candidate = (_WORKSPACE_ROOT / path.lstrip("/")).resolve(strict=False)
    if not _is_contained(candidate):
        raise ValueError(f"Path traversal blocked: {path!r}")
    return candidate


# ── file_read ────────────────────────────────────────────────────────────────


async def _file_read(path: str, offset: int = 0, limit: int = 500) -> str:
    safe = _safe_path(path)
    try:
        with safe.open(encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return f"Error: file not found: {path!r}"
    chunk = lines[offset : offset + limit]
    return "".join(f"{offset + i + 1}\t{line}" for i, line in enumerate(chunk))


register_tool(
    "file_read",
    {
        "name": "file_read",
        "description": "读取文件内容（支持分页）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对于 workspace 的文件路径"},
                "offset": {"type": "integer", "description": "起始行（0-indexed）", "default": 0},
                "limit": {"type": "integer", "description": "最多读取行数", "default": 500},
            },
            "required": ["path"],
        },
    },
    _file_read,
)


# ── file_write ───────────────────────────────────────────────────────────────


async def _file_write(path: str, content: str) -> str:
    safe = _safe_path(path)
    safe.parent.mkdir(parents=True, exist_ok=True)
    with safe.open("w", encoding="utf-8") as f:
        f.write(content)
    return f"Written {len(content)} chars to {path!r}"


register_tool(
    "file_write",
    {
        "name": "file_write",
        "description": "写入文件（覆盖）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对于 workspace 的文件路径"},
                "content": {"type": "string", "description": "文件内容"},
            },
            "required": ["path", "content"],
        },
    },
    _file_write,
)


# ── file_edit ────────────────────────────────────────────────────────────────


async def _file_edit(path: str, old_string: str, new_string: str) -> str:
    safe = _safe_path(path)
    try:
        with safe.open(encoding="utf-8") as f:
            original = f.read()
    except FileNotFoundError:
        return f"Error: file not found: {path!r}"

    if old_string not in original:
        return f"Error: old_string not found in {path!r}"

    count = original.count(old_string)
    if count > 1:
        return f"Error: old_string appears {count} times in {path!r}, must be unique"

    updated = original.replace(old_string, new_string, 1)
    with safe.open("w", encoding="utf-8") as f:
        f.write(updated)
    return f"Edited {path!r}: replaced 1 occurrence"


register_tool(
    "file_edit",
    {
        "name": "file_edit",
        "description": "编辑文件（精确字符串替换，old_string 必须唯一）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对于 workspace 的文件路径"},
                "old_string": {"type": "string", "description": "要替换的原始文本"},
                "new_string": {"type": "string", "description": "替换后的新文本"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    _file_edit,
)


# ── file_grep ────────────────────────────────────────────────────────────────


async def _file_grep(pattern: str, path: str = ".", max_results: int = 50) -> str:
    safe_dir = _safe_path(path)
    regex = re.compile(pattern)
    matches: list[str] = []

    for root, _dirs, files in os.walk(safe_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if regex.search(line):
                            rel = os.path.relpath(fpath, _WORKSPACE_ROOT)
                            matches.append(f"{rel}:{lineno}: {line.rstrip()}")
                            if len(matches) >= max_results:
                                return "\n".join(matches) + f"\n(stopped at {max_results} results)"
            except (OSError, PermissionError):
                continue

    return "\n".join(matches) if matches else "No matches found"


register_tool(
    "file_grep",
    {
        "name": "file_grep",
        "description": "在 workspace 中搜索文件内容（支持正则）",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "正则搜索模式"},
                "path": {"type": "string", "description": "搜索目录（相对路径）", "default": "."},
                "max_results": {"type": "integer", "description": "最多返回结果数", "default": 50},
            },
            "required": ["pattern"],
        },
    },
    _file_grep,
)


# ── file_glob ────────────────────────────────────────────────────────────────


async def _file_glob(pattern: str) -> str:
    safe_pattern = _safe_path(pattern)
    matches = _glob.glob(str(safe_pattern), recursive=True)
    contained = [Path(match).resolve() for match in matches]
    rel_matches = [
        os.path.relpath(match, _WORKSPACE_ROOT) for match in contained if _is_contained(match)
    ][:100]
    return "\n".join(rel_matches) if rel_matches else "No files matched"


register_tool(
    "file_glob",
    {
        "name": "file_glob",
        "description": "按 glob 模式查找文件",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern，如 **/*.py"}
            },
            "required": ["pattern"],
        },
    },
    _file_glob,
)
