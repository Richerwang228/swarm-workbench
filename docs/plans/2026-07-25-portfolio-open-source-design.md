# Swarm Workbench Portfolio Open-Source Design

## Decision

Publish the project as **Swarm Workbench**, a portfolio-grade, local-first
multi-agent orchestration reference implementation.

It is not positioned as a production framework or as a clone of a commercial
product. The public beta must prove one narrow end-to-end path:

1. accept a task in the web console;
2. decompose it into role-based work;
3. execute a bounded concurrent wave;
4. stream task, todo, agent, and tool events;
5. aggregate the result;
6. render the complete trace in the UI.

## Options Considered

### Documentation-only release

This would be fast, but the current checkpointer, graph state, SSE wildcard,
browser event handling, and start script prevent the advertised flow from
working. A polished README around a broken quickstart would reduce portfolio
credibility.

### Complete the original long-term roadmap

Implementing E2B browser automation, worktree isolation, MCP, public sharing,
replay, desktop packaging, and dozens of speculative features before release
would create an unbounded project. It would delay the strongest existing asset:
the observable agent console.

### Narrow, executable public beta

This is the selected approach. It fixes the real orchestration and event
contracts, adds a deterministic no-key demo path, secures local tools, and
documents unfinished capabilities as roadmap items. It provides a reproducible
artifact that a reviewer can run in minutes.

## Runtime Architecture

- **Web console:** Next.js 16, React 19, Zustand.
- **API:** FastAPI REST plus SSE.
- **Orchestration:** a bounded role-based execution engine. The real-provider
  path keeps LangGraph integration behind a stable task service boundary.
- **Event transport:** an in-process topic bus with wildcard subscriptions and
  bounded replay, so a stream opened after task creation does not lose initial
  events.
- **Demo provider:** deterministic, no network and no API key. It exercises the
  same task and event contracts as the real-provider path and is explicitly
  labeled as simulated.
- **Real providers:** optional LiteLLM-backed adapters configured only through
  environment variables.
- **Tool boundary:** filesystem operations remain inside a resolved workspace
  root. Host shell execution is disabled by default and requires explicit
  opt-in.

## Public-Beta Scope

### Included

- No-key demo with visible concurrent role execution.
- Single and swarm task modes with validated input.
- Working wildcard/replay SSE path and matching browser event consumption.
- Automatic tool registration.
- Start script that launches API and web together.
- Unit and API integration tests, Ruff, mypy, web lint/typecheck/build.
- English primary README and Chinese README.
- Architecture, security model, roadmap, troubleshooting, and status docs.
- Apache-2.0 license, contribution/security/support policies, issue and PR
  templates, Dependabot, CodeQL, secret scanning, and CI.
- Real screenshots generated from the working demo.

### Explicitly not included

- Production-grade isolation or multi-tenant deployment.
- E2B browser sessions, MCP discovery, worktree merge automation.
- Public share hosting, durable event replay across process restarts.
- Claims about 100-agent scale, benchmark superiority, cost savings, or
  production readiness without reproducible evidence.

## Security Model

- No real `.env`, logs, databases, traces, reference repositories, or local
  dependency directories may enter Git.
- Public examples use unmistakable placeholders.
- Host command execution is off by default.
- Paths are validated with canonical path containment, not string prefixes.
- API modes, prompt length, and concurrency are validated.
- CORS defaults to local development origins.
- CI runs secret scanning and dependency/security checks with read-only token
  permissions.
- Security limitations are visible in both the README and `SECURITY.md`.

## Quality and Release Gate

The repository is publishable only when all of the following are true:

- a fresh demo starts without API keys;
- the browser shows todo, agent, activity, and final-result events;
- Python tests, Ruff, mypy, frontend lint/typecheck/build all pass;
- current tree and Git history secret scans have no unreviewed findings;
- no high/critical dependency finding is knowingly left undocumented;
- README claims map to tested behavior;
- ignored local artifacts are absent from the commit;
- the GitHub repository is public with topics, description, security features,
  a beta release, and a verified default branch.
