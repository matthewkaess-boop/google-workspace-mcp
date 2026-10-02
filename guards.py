"""Path and permission guardrails for tools that touch the local disk or sharing.

These exist because tool arguments are chosen by the model, and the model reads
untrusted content (email bodies, Drive docs). A prompt-injected instruction must
not be able to write an attachment over ~/.zshrc, upload ~/.ssh to Drive, or
hand file ownership to a stranger.

Allowed local roots default to the downloads and uploads folders under
~/.claude/google-workspace-mcp. Add more with GWS_ALLOWED_DIRS (os.pathsep
separated). Ownership transfer is refused unless GWS_ALLOW_OWNER_TRANSFER=1.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE = Path.home() / ".claude" / "google-workspace-mcp"
DOWNLOADS_DIR = BASE / "downloads"
UPLOADS_DIR = BASE / "uploads"

ALLOWED_DIRS_ENV = "GWS_ALLOWED_DIRS"
ALLOW_OWNER_ENV = "GWS_ALLOW_OWNER_TRANSFER"


def allowed_roots() -> list[Path]:
    roots = [DOWNLOADS_DIR, UPLOADS_DIR]
    for part in os.environ.get(ALLOWED_DIRS_ENV, "").split(os.pathsep):
        if part.strip():
            roots.append(Path(part.strip()).expanduser())
    return roots


def require_within_roots(path: str | os.PathLike, what: str) -> Path:
    """Resolve `path` (following symlinks) and require it to sit under an allowed root."""
    resolved = Path(path).expanduser().resolve()
    for root in allowed_roots():
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue
    allowed = ", ".join(str(r) for r in allowed_roots())
    raise ValueError(
        f"{what} {str(resolved)!r} is outside the allowed folders ({allowed}). "
        f"Move the file there, or add its folder to {ALLOWED_DIRS_ENV}."
    )


def refuse_owner_role(role: str) -> None:
    if role == "owner" and os.environ.get(ALLOW_OWNER_ENV) != "1":
        raise ValueError(
            "Ownership transfer is disabled. Set "
            f"{ALLOW_OWNER_ENV}=1 in the server environment to allow it."
        )
