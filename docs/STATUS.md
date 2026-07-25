# Capability Status

Status is based on tests and a local browser walkthrough, not aspirations.

| Capability | State | Evidence / limitation |
|---|---|---|
| No-key demo | Ready | API-to-SSE-to-UI path completes four roles |
| Swarm 100 scheduler benchmark | Ready | 100 logical simulated agents, deterministic trace and report |
| Live fixed-plan DAG | Beta | One validated plan, up to 100 unique worker agents |
| 100 concurrent provider requests | Contract-tested | Local OpenAI-compatible TCP server; not a named-vendor quota claim |
| Multi-provider configuration | Beta | Process-memory keys, up to 16 providers |
| Role-to-model routing | Beta | Nine roles resolve server-side to configured routes |
| Global/model capacity | Beta | 1-100 runtime cap plus LiteLLM deployment limits |
| Task budgets and cancellation | Beta | Calls, tools, steps, deadline, and parent cancellation |
| Event replay and wildcard delivery | Ready | Unit and integration tests |
| Parallel todo merge | Ready | Mock-provider graph integration test |
| File tools | Beta | Traversal and symlink escape tests |
| Host shell | Beta, opt-in | Disabled by default; local isolation only |
| Live provider orchestration | Experimental | 100-request OpenAI-compatible contract test; no commercial-provider canary in CI |
| Durable recovery | Planned | Checkpoint, provider profiles, and replay are process-local |
| Authentication / multi-tenancy | Not implemented | Localhost use only |
| Browser, MCP, E2B, nested agents | Planned | No public adapter is registered |
| Public share links | Planned | No authenticated multi-tenant sharing |

Release gate: all checks in `./scripts/verify.sh`, secret scan, and the browser
demo must pass for a tagged beta. The current automated coverage baseline is
60%; the current local gate measures above 70% across the Python API and packages.
