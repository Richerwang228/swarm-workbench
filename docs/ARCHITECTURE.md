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
| Benchmark runner | Exercise 100 logical Agents deterministically | Explicitly simulated |
| LangGraph graph | Route, plan, fan out, reduce | Experimental live path |
| Capacity and budget | Bound Agents, calls, tools, steps, and time | Process/task scoped |
| Provider profiles | Validate providers, secrets, models, and role bindings | Keys are write-only |
| LiteLLM Router | Multi-provider calls, deployment limits, retry/cooldown | Embedded OSS dependency |
| Worker loop | Model/tool iterations with a budget | Only registered tools |
| Event broker | Topic matching, replay, fan-out | In-memory and bounded |
| File/shell tools | Workspace operations | Canonical root; shell opt-in |

## Runtime sequence

1. The browser creates a task.
2. The API chooses demo, benchmark, or live orchestration.
3. Live mode asks the configured planner model for one bounded DAG. The server
   validates IDs, roles, dependencies, count, and cycles.
4. Ready tasks fan out in waves. Every worker acquires process capacity, and
   LiteLLM applies the selected model's deployment limit.
5. Worker results merge monotonically. Failed dependencies remain blocked.
6. Results are reduced in batches of ten and then into a final response.
7. The runner emits task, todo, agent, tool, provider-route, and content events.
8. The event broker stores task-scoped bounded replay and delivers wildcard matches.
9. SSE reconnects from `Last-Event-ID`; the browser reduces events into UI
   state.

## Important invariants

- Concurrency is bounded by request and server limits.
- Agent count and maximum concurrency are separate values.
- The planner runs once per live swarm; later waves drain the same fixed plan.
- Models are selected by server-owned role bindings, never by untrusted Base
  URLs emitted from a model.
- Todo status never regresses when parallel branches merge.
- Domain IDs and event replay IDs are separate.
- Unregistered adapters cannot be invoked by a model.
- Demo mode is deterministic and does not touch external systems.

See [STATUS.md](STATUS.md) for evidence and [SECURITY_MODEL.md](SECURITY_MODEL.md)
for trust boundaries.
