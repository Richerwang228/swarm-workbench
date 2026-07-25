"""End-to-end 100-agent contract test through a local OpenAI-compatible server."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import TracebackType

import pytest

from packages.eventbus._queue import reset_broker
from packages.llm_gateway.profiles import RuntimeProfiles
from packages.llm_gateway.router import configure, reset_router
from packages.orchestrator import graph as graph_module
from packages.orchestrator.capacity import reset_capacity
from packages.orchestrator.graph import run_task


class _ProviderState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.worker_requests = 0
        self.total_requests = 0
        self.all_workers_in_flight = threading.Event()

    def enter(self, *, streaming: bool) -> None:
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
            self.total_requests += 1
            if streaming:
                self.worker_requests += 1
                if self.active == 100:
                    self.all_workers_in_flight.set()

    def leave(self) -> None:
        with self.lock:
            self.active -= 1


class _ContractServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 256

    def __init__(self) -> None:
        self.state = _ProviderState()
        super().__init__(("127.0.0.1", 0), _OpenAIHandler)


class _OpenAIHandler(BaseHTTPRequestHandler):
    server: _ContractServer
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length))
        streaming = payload.get("stream") is True
        self.server.state.enter(streaming=streaming)
        try:
            if streaming:
                self.server.state.all_workers_in_flight.wait(timeout=3)
                self._write_stream()
            else:
                self._write_completion(self._non_stream_content(payload))
        finally:
            self.server.state.leave()

    def _non_stream_content(self, payload: dict) -> str:
        system = str(payload.get("messages", [{}])[0].get("content", ""))
        if "完整、可验证的多 Agent 执行 DAG" in system:
            return json.dumps(
                [
                    {
                        "key": f"agent-{index:03d}",
                        "description": f"Analyze independent shard {index:03d}",
                        "role": "tester" if index % 2 else "backend",
                        "depends_on": [],
                    }
                    for index in range(1, 101)
                ]
            )
        return "100 provider-backed agent results reduced successfully"

    def _write_completion(self, content: str) -> None:
        body = json.dumps(
            {
                "id": "contract-completion",
                "object": "chat.completion",
                "created": 1,
                "model": "fake-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Connection", "close")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_stream(self) -> None:
        frames = [
            {
                "id": "contract-stream",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "fake-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": "provider work complete"},
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "contract-stream",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "fake-model",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
        ]
        body = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        body += "data: [DONE]\n\n"
        encoded = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *_args: object) -> None:
        return


class _RunningProvider:
    def __init__(self) -> None:
        self.server = _ContractServer()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> _ContractServer:
        self.thread.start()
        return self.server

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


@pytest.fixture(autouse=True)
def _clean_runtime():
    reset_broker()
    reset_router()
    reset_capacity(100)
    graph_module._graph = None
    yield
    reset_broker()
    reset_router()
    reset_capacity()
    graph_module._graph = None


@pytest.mark.asyncio
async def test_100_live_agents_each_make_a_provider_request():
    with _RunningProvider() as server:
        port = server.server_address[1]
        configure(
            RuntimeProfiles.model_validate(
                {
                    "providers": [
                        {
                            "id": "local",
                            "label": "Local contract provider",
                            "kind": "openai_compatible",
                            "api_base": f"http://127.0.0.1:{port}/v1",
                            "api_key": "test-only-key",
                            "allow_private_network": True,
                            "models": [
                                {
                                    "id": "all",
                                    "model": "fake-model",
                                    "max_parallel_requests": 100,
                                }
                            ],
                        }
                    ],
                    "role_models": {
                        role: "local:all"
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
                    "default_model": "local:all",
                    "global_max_parallel_requests": 100,
                    "per_task_max_agents": 100,
                    "request_timeout_seconds": 30,
                    "max_retries": 0,
                }
            )
        )

        await run_task(
            "provider-live-100",
            "Analyze 100 independent shards",
            mode="swarm",
            max_subagents=100,
            agent_count=100,
            exact_agent_count=True,
        )

    assert server.state.worker_requests == 100
    assert server.state.peak == 100
    assert server.state.active == 0
    assert server.state.total_requests >= 102
