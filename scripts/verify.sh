#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

uv run python -m pytest -q --cov=packages --cov=apps/api --cov-report=term-missing --cov-fail-under=60
uv run ruff format --check .
uv run ruff check .
uv run mypy packages apps/api tests

(
    cd apps/web
    ./node_modules/.bin/eslint .
    ./node_modules/.bin/tsc --noEmit --incremental false
    ./node_modules/.bin/next build
)
