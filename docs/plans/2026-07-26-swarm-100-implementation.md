# Swarm 100 Observatory Implementation Plan

> Completed as the deterministic evidence layer. The later live-agent design
> supersedes the old non-benchmark concurrency cap. See
> [Live 100](../LIVE_100.md).

## 1. Process-wide capacity

- Add `packages/orchestrator/capacity.py`.
- Expose an async slot context manager and observable counters.
- Add reset/configuration helpers for tests.

## 2. Deterministic benchmark runtime

- Add `packages/orchestrator/benchmark.py`.
- Validate benchmark specifications.
- Generate stable logical agents and semantic results.
- Emit progress and a final report.
- Provide a CLI that prints report JSON.

## 3. API contract

- Add `benchmark` task mode and scale-only parameters.
- Keep benchmark and live claims visibly separate.
- Expose completed benchmark reports.

## 4. Scale interface

- Add benchmark fields to the API and Zustand contracts.
- Add `SWARM 100` mode.
- Render aggregate metrics and a dense status matrix.
- Bound detailed task rendering for large runs.

## 5. Evidence

- Add 100-agent, cross-run capacity, recovery, determinism, and API validation
  tests.
- Add a reproducible benchmark artifact.
- Update README, status, architecture, security, and changelog.
- Run the full local and GitHub release gates before tagging.
