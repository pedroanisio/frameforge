#!/usr/bin/env bash
# entrypoint.sh — launch the FrameGraph MCP server (default) or a passed command.
#
#   docker run ... frameforge                 # MCP server over stdio (default)
#   docker run ... frameforge mcp             # explicit: MCP server
#   docker run ... frameforge fonts           # list installed families and exit
#   docker run ... frameforge check           # run the repo's `make check` gate
#   docker run ... frameforge bash            # interactive shell
#   docker run ... frameforge python -m ...   # any command, run inside the venv
#
# Set FRAMEGRAPH_REFRESH_FONTS=1 to rebuild the fontconfig cache at start-up
# (only needed when you bind-mount extra fonts into /usr/share/fonts at runtime).
set -euo pipefail

if [ "${FRAMEGRAPH_REFRESH_FONTS:-0}" = "1" ]; then
  echo "framegraph: rebuilding font cache ..." >&2
  fc-cache -f >/dev/null 2>&1 || true
fi

# Use the prebuilt venv without re-resolving/syncing (no network at run-time).
run() { exec uv run --frozen --no-sync "$@"; }

cmd="${1:-mcp}"
case "${cmd}" in
  mcp|"")
    run python -m framegraph.mcp
    ;;
  fonts)
    exec fc-list : family | sort -u
    ;;
  check)
    shift || true
    exec make check
    ;;
  python|python3|pytest|make|framegraph-render)
    run "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
