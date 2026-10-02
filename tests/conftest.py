"""Keep every test off the real home directory: audit log and allowed folders."""
import pytest

import audit


@pytest.fixture(autouse=True)
def _isolated_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "LOG_PATH", tmp_path / "audit.log")
    monkeypatch.setenv("GWS_ALLOWED_DIRS", str(tmp_path))
    monkeypatch.delenv("GWS_DEFAULT_ACCOUNT", raising=False)
    monkeypatch.delenv("GWS_ALLOW_OWNER_TRANSFER", raising=False)
