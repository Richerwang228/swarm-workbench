# Contributing

Thanks for helping improve Swarm Workbench. The project favors small,
evidence-backed changes over broad framework features.

## Setup

1. Install Python 3.12, Node.js 22, `uv`, and `pnpm`.
2. Run `uv sync --locked`.
3. Run `pnpm --dir apps/web install --frozen-lockfile`.
4. Start the no-key environment with `./start.sh --demo`.

## Development contract

- Open an issue before a large architectural change.
- Keep demo mode deterministic, offline, and free of secrets.
- Add or update tests for behavior changes.
- Do not expose an unfinished adapter through the public registry or UI.
- Run `./scripts/verify.sh` before opening a pull request.
- Use focused commits and explain user-visible tradeoffs in the PR.

## Pull requests

Include the problem, approach, verification evidence, screenshots for UI
changes, and any security impact. By contributing, you agree that your
contribution is licensed under Apache-2.0.
