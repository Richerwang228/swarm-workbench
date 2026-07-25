#!/usr/bin/env bash
# Start the Swarm Workbench API and web console.
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

if [[ "${1:-}" == "--demo" || ! -f .env ]]; then
    export SWARM_DEMO_MODE=true
fi

if [[ ! -x apps/web/node_modules/.bin/next ]]; then
    echo "Web dependencies are missing."
    echo "Run: pnpm --dir apps/web install --frozen-lockfile"
    exit 1
fi

mkdir -p data/{tasks,workspaces,logs}

uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 &
PID_API=$!
(
    cd apps/web
    unset __NEXT_PRIVATE_STANDALONE_CONFIG TURBOPACK
    exec ./node_modules/.bin/next dev --hostname 127.0.0.1 --port 3000
) &
PID_WEB=$!

cleanup() {
    trap - EXIT INT TERM
    kill "$PID_API" "$PID_WEB" 2>/dev/null || true
    wait "$PID_API" "$PID_WEB" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _attempt in {1..40}; do
    if curl --fail --silent http://127.0.0.1:8000/api/health >/dev/null \
        && curl --fail --silent http://127.0.0.1:3000 >/dev/null; then
        echo ""
        echo "Swarm Workbench is ready."
        echo "Web:  http://127.0.0.1:3000"
        echo "API:  http://127.0.0.1:8000"
        echo "Docs: http://127.0.0.1:8000/docs"
        echo "Mode: ${SWARM_DEMO_MODE:-false}"
        wait
        exit 0
    fi
    sleep 0.25
done

echo "Startup timed out. Review the API and web logs above." >&2
exit 1
