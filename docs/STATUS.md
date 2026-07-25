# Capability Status

Status is based on tests and a local browser walkthrough, not aspirations.

| Capability | State | Evidence / limitation |
|---|---|---|
| No-key demo | Ready | API-to-SSE-to-UI path completes four roles |
| Event replay and wildcard delivery | Ready | Unit and integration tests |
| Parallel todo merge | Ready | Mock-provider graph integration test |
| File tools | Beta | Traversal and symlink escape tests |
| Host shell | Beta, opt-in | Disabled by default; local isolation only |
| Live provider orchestration | Experimental | Provider calls mocked in CI |
| Durable recovery | Planned | Checkpoint and replay are process-local |
| Authentication / multi-tenancy | Not implemented | Localhost use only |
| Browser, MCP, E2B, nested agents | Planned | No public adapter is registered |
| Cancellation and share links | Planned | Not exposed in API or UI |

Release gate: all checks in `./scripts/verify.sh`, secret scan, and the browser
demo must pass for a tagged beta. The current automated coverage baseline is
60%; the initial public release measures 65% across the Python API and packages.
