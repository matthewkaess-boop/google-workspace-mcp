"""Every account-scoped tool must advertise `account` as required in its schema,
so a model sees the requirement up front instead of learning it from a refusal."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402

ACCOUNT_MANAGEMENT = {"gws_account_add", "gws_account_list", "gws_account_remove"}


def _tools():
    return asyncio.run(server.mcp.list_tools())


def test_every_account_scoped_tool_requires_account():
    scoped = [t for t in _tools() if t.name not in ACCOUNT_MANAGEMENT]
    assert scoped
    for tool in scoped:
        assert "account" in tool.parameters["properties"], tool.name
        assert "account" in tool.parameters.get("required", []), tool.name
