# Changelog

Notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0-beta.2] - 2026-07-27

### Changed

- Rebuilt the console as an editorial task workspace: a product-led first
  screen, legible execution topology, responsive runtime view, and reduced
  control-room density.
- Replaced the stale console screenshot with a matching repository overview.
- Protected `main` on GitHub with required CI, CodeQL, and secret-scan checks;
  force pushes and deletion are blocked.

## [0.2.0-beta.1] - 2026-07-26

### Added

- Fixed-plan live DAGs with up to 100 user-requested worker Agents.
- A 100-simultaneous-request OpenAI-compatible contract test.
- Multi-provider, multi-model profiles and nine role-to-model bindings.
- Write-only process-memory provider configuration and a settings UI.
- Process/model capacity, task call/tool/step/time budgets, and cancellation.
- Hierarchical result reduction and high-density 100-Agent visualization.
- Deterministic Swarm 100 benchmark, recovery injection, and JSON report.

### Changed

- Planner now runs once and later waves drain the validated plan.
- Agent count and maximum concurrency are independent user controls.
- Event replay is bounded per task group instead of one global history.
- Shell timeout/cancellation terminates the whole child process group.
- Live provider errors are reported by type without echoing sensitive details.

### Removed

- Unused single-provider client and obsolete dispatch/compaction modules.

## [0.1.0-beta.1] - 2026-07-25

### Added

- Deterministic no-key demo with bounded parallel role execution.
- Wildcard and replay-capable in-process event broker.
- Observable task, todo, agent, tool, and content event flow.
- Mocked-provider graph integration tests and secure local tool defaults.
- Portfolio documentation, community files, and GitHub automation.

### Changed

- Repositioned the project as Swarm Workbench, a reference implementation.
- Replaced invalid checkpoint initialization with a supported in-memory saver.
- Made the start script launch and verify both API and web applications.

### Removed

- Unimplemented public share and interrupt endpoints from the public API.
- Unsupported production-readiness and 100-agent claims.
