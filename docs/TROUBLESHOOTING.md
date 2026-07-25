# Troubleshooting

## Web dependencies are missing

Run `pnpm --dir apps/web install --frozen-lockfile`.

## Health reports `degraded`

This is expected in live mode when `SWARM_MODEL`, `SWARM_API_BASE`, or
`SWARM_API_KEY` is missing. Demo mode remains healthy without them.

## Port 3000 or 8000 is busy

Stop the process using the port before running `start.sh`. The beta start script
intentionally uses fixed localhost ports so the browser/API contract stays
predictable.

## Live model call fails

Confirm the provider-qualified `SWARM_MODEL`, OpenAI-compatible base URL, quota,
and billing with the provider. Never post the key in an issue.

## UI misses earlier events

Reconnect while the API process is still running. Replay is bounded and
process-local; restarting the API clears it.
