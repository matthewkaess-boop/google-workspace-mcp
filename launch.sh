#!/bin/sh
# Launcher for the Claude Desktop extension (.mcpb). Finds Python 3.10+, builds a
# private virtualenv on first run (and again whenever requirements.txt changes),
# then starts the server. Everything diagnostic goes to stderr: stdout is the
# MCP channel and must stay clean.
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
STATE="${GWS_STATE_DIR:-$HOME/.claude/google-workspace-mcp}"

# An optional extension setting arrives as the literal text "${user_config...}"
# when left blank. Treat that as unset.
case "${GWS_ACCOUNTS_INDEX:-}" in ""|*'${'*) unset GWS_ACCOUNTS_INDEX ;; esac
: "${GWS_ACCOUNTS_INDEX:=$STATE/accounts_index.json}"
export GWS_ACCOUNTS_INDEX

find_python() {
  for c in "${GWS_PYTHON:-}" python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    [ -n "$c" ] || continue
    for p in "$c" "/opt/homebrew/bin/$c" "/usr/local/bin/$c" "$HOME/.pyenv/shims/$c"; do
      command -v "$p" >/dev/null 2>&1 || continue
      if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        command -v "$p"; return 0
      fi
    done
  done
  return 1
}

PY="$(find_python)" || {
  echo "google-workspace: Python 3.10+ not found. Install it (for example 'brew install python') or set GWS_PYTHON." >&2
  exit 1
}

STAMP="$(cksum < "$DIR/requirements.txt" | cut -d' ' -f1)"
VENV="${GWS_VENV_DIR:-$STATE/venv-mcpb-$STAMP}"
# Claude Desktop can start several copies at once (chat and Code sessions), so
# the build is serialized with a lock directory, and the venv only counts once
# the .ready marker exists. A half-built venv with bin/python in it is not ready.
READY="$VENV/.ready"
if [ ! -f "$READY" ]; then
  mkdir -p "$(dirname "$VENV")"
  LOCK="$VENV.lock"
  waited=0
  until [ -f "$READY" ] || mkdir "$LOCK" 2>/dev/null; do
    if [ "$waited" -ge 300 ]; then
      echo "google-workspace: gave up waiting for $LOCK (remove it if no install is running)" >&2
      exit 1
    fi
    sleep 1; waited=$((waited + 1))
  done
  # Another copy finished the build. Release the lock if we took it: with
  # .ready present nobody can be mid-install, since an install starts by
  # deleting the venv (marker included).
  if [ -f "$READY" ]; then
    rmdir "$LOCK" 2>/dev/null || true
  else
    trap 'rmdir "$LOCK" 2>/dev/null' EXIT
    echo "google-workspace: first run, installing dependencies into $VENV" >&2
    rm -rf "$VENV"
    "$PY" -m venv "$VENV" >&2
    if "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$DIR/requirements.txt" >&2; then
      touch "$READY"
    else
      rm -rf "$VENV"; echo "google-workspace: dependency install failed" >&2; exit 1
    fi
    rmdir "$LOCK" 2>/dev/null; trap - EXIT
  fi
fi

exec "$VENV/bin/python" "$DIR/server.py"
