"""Mocked-provider integration tests for the live orchestration graph."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from packages.eventbus._queue import reset_broker
from packages.eventbus.subscriber import subscribe
from packages.orchestrator import graph as graph_module
from packages.orchestrator.graph import build_graph, run_task
from packages.worker.agent_loop import _build_tool_schemas


@pytest.fixture(autouse=True)
def _reset_runtime():
    reset_broker()
    graph_module._graph = None
    yield
    reset_broker()
    graph_module._graph = None


def _response(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


async def _fake_worker(*, task: str, agent_id: str | None = None, **_kwargs):
    yield {
        "type": "agent.done",
        "agent_id": agent_id,
        "content": f"completed:{task}",
    }


def test_graph_compiles_with_application_owned_checkpointer():
    compiled = build_graph()
    assert compiled is not None


def test_worker_registers_only_supported_beta_tools():
    names = {schema["function"]["name"] for schema in _build_tool_schemas()}

    assert {"bash", "file_read", "file_write", "file_edit", "todo_create"} <= names
    assert {"browser", "spawn_subagent", "python"}.isdisjoint(names)


@pytest.mark.asyncio
async def test_single_mode_passes_the_user_prompt_to_worker(monkeypatch):
    received: list[str] = []

    async def capture_worker(*, task: str, agent_id: str | None = None, **_kwargs):
        received.append(task)
        yield {
            "type": "agent.done",
            "agent_id": agent_id,
            "content": "single complete",
        }

    monkeypatch.setattr("packages.worker.runner.run_worker", capture_worker)

    await run_task("single-task", "Write the release report", mode="single")
    events = [event async for event in subscribe("swarm.events.single-task.>", timeout=0.05)]

    assert received == ["Write the release report"]
    assert [event.type for event in events][0] == "task.started"
    spawned = next(event for event in events if event.type == "agent.spawned")
    assert spawned.data["task"] == "Write the release report"
    assert events[-1].type == "task.completed"


@pytest.mark.asyncio
async def test_swarm_mode_merges_parallel_worker_results(monkeypatch):
    async def fake_call(*_args, **_kwargs):
        return _response(
            """[
              {"description": "Design API", "role": "backend"},
              {"description": "Verify UI", "role": "tester"}
            ]"""
        )

    monkeypatch.setattr("packages.llm_gateway.router.call", fake_call)
    monkeypatch.setattr("packages.worker.runner.run_worker", _fake_worker)

    await run_task("swarm-task", "Prepare two independent checks", mode="swarm")
    events = [event async for event in subscribe("swarm.events.swarm-task.>", timeout=0.05)]

    assert sum(event.type == "agent.spawned" for event in events) == 2
    assert (
        sum(event.type == "agent.update" and event.data["status"] == "done" for event in events)
        == 2
    )
    assert events[-1].type == "task.completed"
