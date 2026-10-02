#!/usr/bin/env bash
# Register this server with Claude Code, prompting for the OAuth client so the
# values never sit in a command line, shell history or chat.
#
# Run from a terminal:  bash scripts/register-server.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "Missing $PY -- create the venv first (see SETUP.md)." >&2; exit 1; }

# Find the Claude CLI: on PATH, else the newest copy bundled with the desktop app.
CLAUDE="$(command -v claude || true)"
if [ -z "$CLAUDE" ]; then
  CLAUDE="$(ls -1d "$HOME/Library/Application Support/Claude/claude-code"/*/*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1 || true)"
fi
[ -n "$CLAUDE" ] && [ -x "$CLAUDE" ] || { echo "Could not find the claude CLI." >&2; exit 1; }

read -r -p "OAuth client ID (ends in .apps.googleusercontent.com): " CLIENT_ID
read -r -s -p "OAuth client secret (input hidden): " CLIENT_SECRET
echo

case "$CLIENT_ID" in
  *.apps.googleusercontent.com) ;;
  *) echo "That does not look like a client ID (expected ...apps.googleusercontent.com). Nothing changed." >&2; exit 1 ;;
esac
if [ -z "$CLIENT_SECRET" ] || [[ "$CLIENT_SECRET" == PASTE_* ]]; then
  echo "Client secret is empty or still a placeholder. Nothing changed." >&2
  exit 1
fi

"$CLAUDE" mcp remove google-workspace -s user >/dev/null 2>&1 || true
"$CLAUDE" mcp add google-workspace -s user \
  -e "GWS_CLIENT_ID=$CLIENT_ID" -e "GWS_CLIENT_SECRET=$CLIENT_SECRET" \
  -- "$PY" "$ROOT/server.py"
unset CLIENT_ID CLIENT_SECRET
echo "Registered. Start a new Claude Code session to load it."
