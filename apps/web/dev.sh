#!/usr/bin/env bash
# Unset env vars that leak from CodePilot's own Next.js process
unset __NEXT_PRIVATE_STANDALONE_CONFIG
unset TURBOPACK
exec pnpm exec next dev "$@"
