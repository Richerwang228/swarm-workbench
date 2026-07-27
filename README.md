# Swarm Workbench

[简体中文](README.zh-CN.md)

[![CI](https://github.com/Richerwang228/swarm-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/Richerwang228/swarm-workbench/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Richerwang228/swarm-workbench/actions/workflows/codeql.yml/badge.svg)](https://github.com/Richerwang228/swarm-workbench/actions/workflows/codeql.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg)](pyproject.toml)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](apps/web/package.json)

**A local-first, multi-provider runtime for planning and observing up to 100
live AI agents—with user-controlled model routing and concurrency.**

![Swarm Workbench overview](docs/assets/swarm-workbench-overview.svg)

> [!IMPORTANT]
> This is a portfolio-grade reference implementation and public beta, not a
> hosted production service. Its runtime is contract-tested with 100 concurrent
> OpenAI-compatible requests. Real vendor throughput, cost, and rate limits
> depend on the user's account and are not claimed by that local test.

## Why this project

Multi-agent demos often show only the final answer. Swarm Workbench makes the
execution legible: task decomposition, role assignment, bounded concurrency,
todo state, tool activity, streaming output, and aggregation are visible through
one event contract.

The repository is intentionally narrow. It aims to be easy to run and inspect,
while documenting where prototype behavior ends and production engineering would
begin.

## What works today

- A no-key, no-network demo that completes an observable four-role workflow.
- A deterministic `SWARM 100 · SIMULATED` scheduler benchmark for CI and local
  capacity checks.
- A fixed-plan live DAG with up to 100 unique worker agents and optional exact
  agent counts.
- In-memory configuration for multiple providers and models, with nine
  user-controlled role-to-model bindings.
- Global, per-model, per-task, model-call, tool-call, step, and wall-clock
  limits; parent-task cancellation propagates to live agents.
- Hierarchical result reduction that keeps 100 worker outputs out of one
  oversized prompt.
- `single`, `swarm`, and heuristic `auto` orchestration paths for optional live
  providers.
- Bounded parallel dispatch with deterministic todo result merging.
- FastAPI task API and SSE with wildcard subscriptions and bounded replay.
- Next.js console with todo progress, agent cards, chat output, and activity feed.
- Provider routing through LiteLLM when the user supplies environment variables.
- Workspace-scoped file tools; host shell execution is disabled by default.
- Python unit/integration tests and frontend lint, typecheck, and production build.

The live contract suite starts a local OpenAI-compatible server, generates one
100-item plan, and verifies 100 streaming provider requests are simultaneously
in flight. This proves the runtime path—not third-party quota or model quality.
See [Live 100 evidence and boundaries](docs/LIVE_100.md).

See the evidence-based [capability status](docs/STATUS.md) before evaluating a
feature claim.

## Quickstart: no API key

Requirements: Python 3.12, Node.js 22, [uv](https://docs.astral.sh/uv/), and
[pnpm](https://pnpm.io/).

```bash
git clone https://github.com/Richerwang228/swarm-workbench.git
cd swarm-workbench

uv sync --locked
pnpm --dir apps/web install --frozen-lockfile
./start.sh --demo
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000), select **Load sample**,
and press **Send**. The demo makes no model request and does not execute host
tools.

## How it works

```mermaid
flowchart LR
    U["User / browser"] --> W["Next.js console"]
    W -->|POST task| A["FastAPI task API"]
    A --> O{"Task mode"}
    O -->|demo| D["Deterministic demo runner"]
    O -->|benchmark| B["Deterministic Swarm 100 benchmark"]
    O -->|single / swarm| G["LangGraph orchestrator"]
    G --> C["Global agent capacity + task budgets"]
    C --> L["LiteLLM multi-provider router"]
    G --> T["Opt-in tools"]
    D --> E["In-process event broker"]
    B --> E
    G --> E
    E -->|wildcard + replay SSE| W
```

Both execution paths emit task, todo, agent, tool, and content events. The UI
does not need to understand how an agent was implemented. Read
[Architecture](docs/ARCHITECTURE.md) for component responsibilities and runtime
sequence.

## Demo, benchmark, and live modes

| | Demo | Swarm 100 benchmark | Live providers |
|---|---|---|---|
| API key | None | None | User-supplied |
| Network | None | None | Provider requests; search may use network |
| Agent output | 4-role simulation | 100-agent simulation | Model-generated |
| Scale purpose | Product walkthrough | Scheduler evidence | Useful user work |
| Host shell | Never | Never | Off unless explicitly enabled |

To try live execution, open **Providers** in the header. Add one or more
providers/models, set the role routing matrix, and choose separate Agent and
concurrency limits. Inline API keys exist only in API process memory and are
never returned by `GET`.

Environment-only configuration remains available:

```bash
cp .env.example .env
# Set SWARM_DEMO_MODE=false and configure at least one provider.
./start.sh
```

Never commit `.env`. Provider requests can incur cost. Review
[the security model](docs/SECURITY_MODEL.md) before enabling tools.

## Configuration

| Variable | Default | Purpose |
|---|---:|---|
| `SWARM_DEMO_MODE` | `true` | Keep the no-key demo as the default path |
| `SWARM_MODEL` | — | LiteLLM provider-qualified model name |
| `SWARM_API_BASE` | — | OpenAI-compatible provider base URL |
| `SWARM_API_KEY` | — | Provider credential; never commit it |
| `SWARM_GLOBAL_AGENT_CAP` | `8` | Process-wide live/benchmark Agent limit, maximum 100 |
| `ALLOW_LOCAL_EXECUTION` | `false` | Explicit opt-in for host shell execution |
| `WORKSPACE_ROOT` | `data/workspace` | Canonical root for file and shell tools |
| `SWARM_CORS_ORIGINS` | local port 3000 | Comma-separated browser origins |

Provider placeholders are documented in [`.env.example`](.env.example).

## Development and verification

```bash
./scripts/verify.sh
```

This runs Python tests, Ruff, mypy, ESLint, TypeScript, and the Next.js
production build. Contribution expectations are in
[CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Agents can turn untrusted model output into tool calls. That is a real security
boundary, even for a local application.

- Host shell execution is off by default.
- Provider keys submitted in the UI are write-only and process-memory-only.
- Native provider types use their official LiteLLM endpoint; arbitrary Base
  URLs require the explicit OpenAI-compatible or local-provider path.
- Provider-panel remote custom endpoints require HTTPS; literal and currently
  resolved private addresses are rejected unless local advanced mode is
  explicitly enabled. This is not a request-time egress proxy.
- The API and web starter bind to loopback, CORS is local, and Host headers are
  restricted.
- File paths are resolved canonically and symlink escapes are rejected.
- Real secrets are ignored; only `.env.example` is tracked.
- The public demo does not use models, the network, or host tools.
- Do not put passwords, API keys, or personal secrets in prompts or tool input:
  local task/event history is observable until it is evicted from memory.
- CI runs CodeQL, dependency updates, and secret scanning.

This beta is not a hardened sandbox. Do not run untrusted live tasks with local
execution enabled. Read [SECURITY.md](SECURITY.md) and
[the full threat model](docs/SECURITY_MODEL.md).

## Known limitations

- Checkpoints, provider profiles, and event replay are process-local and are
  lost after restart.
- The 100-concurrent-request test uses a local OpenAI-compatible contract
  server. A contributor-owned real-provider canary is still required before
  making claims about any named vendor.
- USD cost enforcement is not available for unknown custom models; hard call,
  tool, step, concurrency, and time budgets are enforced instead.
- Public share links, browser automation, E2B sessions, MCP discovery, durable
  recovery, and isolated worktree merging are not implemented.
- The demo proves the product/event path, not model quality or benchmark gains.
- There is no authentication or multi-tenant isolation; bind to localhost only.

These are tracked in [Roadmap](docs/ROADMAP.md), not presented as completed
features.

## Repository map

```text
apps/
  api/             FastAPI task and SSE endpoints
  web/             Next.js observable agent console
packages/
  orchestrator/    Demo, benchmark, capacity, budgets, and LangGraph runtime
  llm_gateway/     Multi-provider profiles and LiteLLM role routing
  eventbus/        Wildcard topic delivery and bounded replay
  worker/          Model/tool loop and role prompts
  tools/           Supported workspace tools
tests/
  unit/            Component contracts and security boundaries
  integration/     Demo, graph, stream, and health paths
docs/              Architecture, status, security, roadmap, plans
```

## Project governance

- Bugs and proposals: [GitHub Issues](https://github.com/Richerwang228/swarm-workbench/issues)
- Usage questions: [SUPPORT.md](SUPPORT.md)
- Vulnerabilities: [SECURITY.md](SECURITY.md)
- Contributions: [CONTRIBUTING.md](CONTRIBUTING.md)
- Conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Acknowledgements

The design is informed by public work around LangGraph, LiteLLM, FastAPI,
AutoGen, CrewAI, CAMEL, MetaGPT, and other agent systems. Private research
checkouts are not included. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
