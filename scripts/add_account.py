#!/usr/bin/env python3
"""Connect (or reconnect) one Google account to the google-workspace server.

Why this exists: the sign-in normally opens your default browser, which may be
signed in to the wrong Google account. By default this script does NOT open a
browser. It prints the sign-in link; paste it into a browser that is signed in
to the account you want, finish the Google screens, and come back.

Usage:
    .venv/bin/python -u scripts/add_account.py          # print link only (default)
    .venv/bin/python -u scripts/add_account.py --open   # also open default browser

The OAuth client (GWS_CLIENT_ID / GWS_CLIENT_SECRET) is read from the
`google-workspace` server entry in ~/.claude.json, so nothing is typed here and
nothing secret is printed.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    if not os.environ.get("GWS_CLIENT_ID"):
        cfg = json.loads((Path.home() / ".claude.json").read_text())
        env = cfg.get("mcpServers", {}).get("google-workspace", {}).get("env", {})
        if not env:
            print("No google-workspace server found in ~/.claude.json. See README.md.", file=sys.stderr)
            return 1
        os.environ.update(env)
    if "--open" not in sys.argv:
        os.environ["BROWSER"] = "true"  # webbrowser runs `true <url>`: a no-op

    import accounts

    try:
        result = accounts.add_account()
    except Exception as exc:  # noqa: BLE001 - show a short, readable reason
        print(f"FAILED: {type(exc).__name__}: {str(exc)[:300]}", file=sys.stderr)
        return 1
    print(f"CONNECTED: {result['email']} ({len(result['scopes'])} permissions)")
    print("Accounts now:", ", ".join(accounts.list_accounts()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
