# Swarm Workbench Portfolio Open-Source Implementation Plan

**Goal:** Turn the existing prototype into a secure, reproducible, portfolio-grade public beta and publish it to GitHub.

**Architecture:** Preserve the Next.js console and FastAPI boundary, repair the event and orchestration contracts, and add a deterministic no-key demo that uses the same public task/SSE contract as real providers. Keep risky host tools opt-in and move unfinished integrations into an explicit roadmap.

**Tech Stack:** Python 3.12, FastAPI, asyncio, LangGraph, LiteLLM, Pydantic, pytest, Ruff, mypy, Next.js 16, React 19, TypeScript, Zustand, GitHub Actions.

---

### Task 1: Establish reproducible project metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Modify: `.env.example`
- Create: `LICENSE`
- Create: `CHANGELOG.md`

**Steps:**
1. Add packaging metadata, typed development dependencies, and stable pytest paths.
2. Remove the broken CLI entry point unless a tested CLI is implemented.
3. Track `uv.lock`; ignore every real environment variant while preserving `.env.example`.
4. Add explicit demo and local-execution safety settings.
5. Generate and retain lockfiles.
6. Run `uv sync --locked` and a clean frontend install.

### Task 2: Repair event transport with tests first

**Files:**
- Test: `tests/unit/test_eventbus.py`
- Test: `tests/integration/test_stream_api.py`
- Modify: `packages/eventbus/_queue.py`
- Modify: `packages/eventbus/publisher.py`
- Modify: `packages/eventbus/subscriber.py`
- Modify: `packages/shared/events.py`
- Modify: `apps/api/routes/stream.py`
- Modify: `apps/web/lib/sse.ts`

**Steps:**
1. Add failing tests for wildcard delivery, bounded replay, and event ordering.
2. Implement wildcard topic matching and per-topic bounded history.
3. Remove the Pydantic `json()` override and use an explicit serialization method.
4. Make SSE frames compatible with the frontend message handler.
5. Verify the targeted tests, then the full Python suite and frontend typecheck.

### Task 3: Add a real no-key demo task loop

**Files:**
- Create: `packages/orchestrator/demo.py`
- Test: `tests/integration/test_demo_task.py`
- Modify: `apps/api/routes/tasks.py`
- Modify: `packages/shared/schema.py`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/lib/store.ts`
- Modify: `apps/web/components/PromptInput.tsx`
- Modify: `apps/web/app/page.tsx`

**Steps:**
1. Add API tests for request validation, task lifecycle, emitted todo/agent/tool events,
   concurrency bounds, stop behavior, and final aggregation.
2. Implement a deterministic concurrent demo runner with honest simulated labels.
3. Add a `demo` mode and a one-click sample task in the UI.
4. Surface API errors and clearly distinguish demo from live-provider execution.
5. Verify API integration tests and frontend lint/typecheck/build.

### Task 4: Repair the real-provider orchestration path

**Files:**
- Test: `tests/integration/test_orchestrator.py`
- Modify: `packages/orchestrator/state.py`
- Modify: `packages/orchestrator/graph.py`
- Modify: `packages/orchestrator/checkpointer.py`
- Modify: `packages/orchestrator/nodes/planner.py`
- Modify: `packages/orchestrator/nodes/route.py`
- Modify: `packages/tools/__init__.py`
- Modify: `packages/worker/agent_loop.py`

**Steps:**
1. Add mocked-provider tests for single input propagation, automatic route parsing,
   swarm fan-out, concurrent result merging, and tool schemas.
2. Replace the invalid checkpointer lifecycle with a supported application-owned
   saver or a documented in-memory default.
3. Model parallel worker outputs with deterministic reducers instead of competing
   full-state writes.
4. Emit todo and agent lifecycle events from the real path.
5. Import supported tools explicitly and exclude placeholder tools.
6. Verify graph tests and the full Python quality suite.

### Task 5: Enforce the local security boundary

**Files:**
- Test: `tests/unit/test_tools.py`
- Modify: `packages/tools/file_ops.py`
- Modify: `packages/tools/bash.py`
- Modify: `apps/api/main.py`
- Modify: `apps/api/routes/tasks.py`
- Create: `.gitleaks.toml`
- Create: `.pre-commit-config.yaml`

**Steps:**
1. Add failing tests for sibling-prefix traversal, symlink escape, disabled shell
   execution, prompt limits, invalid modes, and excessive concurrency.
2. Use canonical containment checks for all filesystem paths and glob results.
3. Disable local shell execution unless `ALLOW_LOCAL_EXECUTION=true`.
4. Validate API inputs and configure local CORS origins explicitly.
5. Run security-focused tests and secret scans.

### Task 6: Make startup and health checks truthful

**Files:**
- Test: `tests/integration/test_health.py`
- Modify: `start.sh`
- Modify: `apps/api/main.py`
- Modify: `apps/web/dev.sh`
- Create: `scripts/verify.sh`

**Steps:**
1. Make demo startup work without `.env`.
2. Launch API and web, wait for both health endpoints, and terminate both cleanly.
3. Report demo/live mode and capability status through `/api/health`.
4. Add one verification script covering backend and frontend gates.
5. Smoke-test startup from a clean environment.

### Task 7: Raise the static-quality baseline

**Files:**
- Modify: Python files reported by Ruff and mypy
- Modify: relevant tests

**Steps:**
1. Apply safe Ruff fixes and format the Python tree.
2. Resolve remaining lint issues without changing intended behavior.
3. Resolve mypy errors or narrow justified third-party ignores.
4. Run Python tests, Ruff format/check, and mypy until all pass.
5. Run frontend lint, typecheck, and production build.

### Task 8: Add portfolio-grade documentation and community files

**Files:**
- Replace: `README.md`
- Create: `README.zh-CN.md`
- Create: `CONTRIBUTING.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `SECURITY.md`
- Create: `SUPPORT.md`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/SECURITY_MODEL.md`
- Create: `docs/STATUS.md`
- Create: `docs/ROADMAP.md`
- Create: `docs/TROUBLESHOOTING.md`
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

**Steps:**
1. Write an English README in the order: value, real demo, quickstart, proof,
   architecture, configuration, security, testing, limitations, roadmap.
2. Add a faithful Chinese translation.
3. Document current capability status and known limitations with no unsupported claims.
4. Add contribution, conduct, security, support, and third-party attribution files.
5. Validate every internal link and command.

### Task 9: Add CI and repository security automation

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/codeql.yml`
- Create: `.github/workflows/secret-scan.yml`
- Create: `.github/workflows/scorecard.yml`
- Create: `.github/dependabot.yml`
- Create: `.github/release.yml`

**Steps:**
1. Use read-only default permissions and pin third-party Actions to commit SHAs.
2. Run Python and web quality gates on supported runtimes.
3. Add CodeQL, Gitleaks, dependency updates, and OpenSSF Scorecard.
4. Validate workflow syntax and action references.

### Task 10: Produce and verify the public demo artifact

**Files:**
- Create: `docs/assets/swarm-workbench-demo.png`
- Create: `docs/assets/social-preview.png`
- Optionally create: `docs/assets/swarm-workbench-demo.gif`

**Steps:**
1. Start the no-key demo.
2. Run the representative sample task.
3. Verify the browser shows task, todo, agents, activity, and final answer.
4. Capture a real, redacted screenshot and social preview.
5. Add the artifact to both READMEs and inspect rendered Markdown.

### Task 11: Perform the release audit

**Files:**
- Review all tracked files and generated artifacts.

**Steps:**
1. Run the complete verification script.
2. Run Gitleaks on the working tree and full Git history.
3. Run Python and JavaScript dependency audits and review licenses.
4. Confirm no ignored files, large binaries, local paths, credentials, logs, or
   reference repositories are staged.
5. Confirm README claims map to tests or visible behavior.

### Task 12: Publish the GitHub beta

**External target:**
- Create: `Richerwang228/swarm-workbench`

**Steps:**
1. Create coherent initial commits without fabricating historical development.
2. Create the public repository and push `main`.
3. Set description, topics, issues, security features, and safe merge settings.
4. Create a signed or annotated `v0.1.0-beta.1` tag and GitHub pre-release.
5. Wait for CI and security checks; fix any release-blocking failure.
6. Verify the public README, assets, license detection, community profile, release,
   and clone/quickstart instructions.
