# Roadmap

## Next

- Durable SQLite/Postgres task state and resumable event delivery.
- OS Keychain-backed credential references, rotation, and deletion UI.
- Provider-level latency, token, 429, cooldown, and fallback metrics.
- Cost reconciliation for models with trustworthy price metadata.
- A contributor-owned, manually approved real-provider canary at 10, 25, 50,
  and 100 Agents.
- Containerized tool isolation with resource and network policies.
- Per-Agent worktree isolation and an explicit merge/review gate.

## Later

- Authentication and tenant-scoped task storage.
- Audited browser and MCP adapters.
- Durable Flight Recorder trace export and replay.
- Authentication and tenant-scoped provider/task/event storage for hosted use.
- Nested-agent budgets and full provider fallback provenance.

Features move from roadmap to status only with tests, docs, and a working user
path. Dates are intentionally not promised.
