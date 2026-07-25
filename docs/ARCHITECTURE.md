# Architecture

## Design goal

Make multi-agent execution observable without requiring a model key. The
runtime separates orchestration from presentation through a shared event
contract.

## Components

| Component | Responsibility | Boundary |
|---|---|---|
| Next.js console | Start tasks and render trace state | Never executes tools |
| FastAPI API | Validate requests and expose SSE | Localhost, no authentication |
| Demo runner | Emit a reproducible four-role trace | No model, network, or tools |
| LangGraph graph | Route, plan, fan out, reduce | Experimental live path |
| Worker loop | Model/tool iterations with a budget | Only registered tools |
| Event broker | Topic matching, replay, fan-out | In-memory and bounded |
| File/shell tools | Workspace operations | Canonical root; shell opt-in |

## Runtime sequence

1. The browser creates a task.
2. The API chooses deterministic demo or live orchestration.
3. The runner emits task, todo, agent, tool, and content events.
4. The event broker stores a bounded replay and delivers wildcard matches.
5. SSE reconnects from `Last-Event-ID`; the browser reduces events into UI
   state.
6. Parallel results merge monotonically before the task completes.

## Important invariants

- Concurrency is bounded by request and server limits.
- Todo status never regresses when parallel branches merge.
- Domain IDs and event replay IDs are separate.
- Unregistered adapters cannot be invoked by a model.
- Demo mode is deterministic and does not touch external systems.

See [STATUS.md](STATUS.md) for evidence and [SECURITY_MODEL.md](SECURITY_MODEL.md)
for trust boundaries.
