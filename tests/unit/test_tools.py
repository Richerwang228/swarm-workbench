"""Unit tests — tools (file_ops, bash, todo, web_search)。"""

from __future__ import annotations

import importlib

import pytest

# ── file_ops ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_file_write_and_read(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    # 重新导入以刷新 _WORKSPACE_ROOT
    import packages.tools.file_ops as fo

    importlib.reload(fo)

    import packages.tools.file_ops  # noqa: F401
    from packages.tools.registry import execute_tool

    result = await execute_tool("file_write", {"path": "hello.txt", "content": "hello world\n"})
    assert "Written" in result

    content = await execute_tool("file_read", {"path": "hello.txt"})
    assert "hello world" in content


@pytest.mark.asyncio
async def test_file_edit(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    import packages.tools.file_ops as fo

    importlib.reload(fo)

    target = tmp_path / "edit_me.txt"
    target.write_text("foo bar baz")

    from packages.tools.registry import execute_tool

    result = await execute_tool(
        "file_edit",
        {
            "path": "edit_me.txt",
            "old_string": "bar",
            "new_string": "QUX",
        },
    )
    assert "Edited" in result
    assert "QUX" in target.read_text()


@pytest.mark.asyncio
async def test_file_path_traversal_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    import packages.tools.file_ops as fo

    importlib.reload(fo)

    from packages.tools.registry import execute_tool

    result = await execute_tool("file_read", {"path": "../../etc/passwd"})
    assert "Error" in result or "blocked" in result.lower()


@pytest.mark.asyncio
async def test_file_symlink_escape_blocked(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "private.txt").write_text("do not expose")
    (workspace / "escape").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("WORKSPACE_ROOT", str(workspace))

    import packages.tools.file_ops as fo

    importlib.reload(fo)
    from packages.tools.registry import execute_tool

    result = await execute_tool("file_read", {"path": "escape/private.txt"})
    assert "blocked" in result.lower()


# ── todo ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_todo_create_and_update():
    from packages.tools.registry import execute_tool

    tid = "test-task-001"
    create_result = await execute_tool(
        "todo_create",
        {
            "description": "写单元测试",
            "role": "tester",
            "task_id": tid,
        },
    )
    assert "Created" in create_result

    # 提取 id from result string 比较麻烦，直接测 list
    list_result = await execute_tool("todo_list", {"task_id": tid})
    assert "写单元测试" in list_result


@pytest.mark.asyncio
async def test_todo_update_invalid_status():
    from packages.tools.registry import execute_tool

    result = await execute_tool(
        "todo_update",
        {
            "todo_id": "nonexistent",
            "status": "invalid_status",
        },
    )
    assert "Error" in result


# ── bash (local mode) ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bash_echo(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ALLOW_LOCAL_EXECUTION", "true")
    monkeypatch.delenv("SANDBOX_PROVIDER", raising=False)
    from packages.tools.registry import execute_tool

    result = await execute_tool("bash", {"command": "echo 'hello from bash'"})
    assert "hello from bash" in result


@pytest.mark.asyncio
async def test_bash_blocked_command(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ALLOW_LOCAL_EXECUTION", "true")
    from packages.tools.registry import execute_tool

    result = await execute_tool("bash", {"command": "rm -rf /"})
    assert "blocked" in result.lower()


@pytest.mark.asyncio
async def test_bash_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("ALLOW_LOCAL_EXECUTION", raising=False)
    monkeypatch.delenv("SANDBOX_PROVIDER", raising=False)
    from packages.tools.registry import execute_tool

    result = await execute_tool("bash", {"command": "echo should-not-run"})
    assert "disabled" in result.lower()
