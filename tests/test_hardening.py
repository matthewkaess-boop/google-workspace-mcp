"""Hardening guarantees: mandatory account, path confinement, owner-transfer
refusal, and write auditing that records the resolved account."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import accounts  # noqa: E402
import audit  # noqa: E402
import drive_tools  # noqa: E402
import gmail_tools  # noqa: E402
import guards  # noqa: E402


def _log() -> str:
    return audit.LOG_PATH.read_text() if audit.LOG_PATH.exists() else ""


# --- account is mandatory ---------------------------------------------------


@pytest.mark.parametrize("value", [None, "", "   "])
def test_resolve_rejects_missing_account(value, monkeypatch):
    monkeypatch.setenv("GWS_DEFAULT_ACCOUNT", "someone@example.com")
    monkeypatch.setattr(accounts, "list_accounts", lambda: ["a@x.com", "b@y.com"])
    with pytest.raises(accounts.AccountError) as exc:
        accounts._resolve(value)
    assert "a@x.com" in str(exc.value) and "required" in str(exc.value)


def test_resolve_normalizes_case_and_whitespace():
    assert accounts._resolve("  Me@Example.COM ") == "me@example.com"


def test_env_default_is_not_used_by_resolve(monkeypatch):
    monkeypatch.setenv("GWS_DEFAULT_ACCOUNT", "someone@example.com")
    with pytest.raises(accounts.AccountError):
        accounts._resolve(None)


def test_send_without_account_never_calls_google(monkeypatch):
    called = MagicMock()
    monkeypatch.setattr(gmail_tools, "service", called)
    with pytest.raises(accounts.AccountError):
        gmail_tools.send(["x@y.com"], "hi", "body")
    called.assert_not_called()


def test_dry_run_send_reports_resolved_account():
    out = gmail_tools.send(["x@y.com"], "hi", "body", account="Me@Example.com", dry_run=True)
    assert out["account"] == "me@example.com" and out["dry_run"] is True


def test_dry_run_send_without_account_is_rejected():
    with pytest.raises(accounts.AccountError):
        gmail_tools.send(["x@y.com"], "hi", "body", dry_run=True)


# --- send / reply are audited with account and recipients -------------------


def test_send_is_audited_with_account_and_recipients(monkeypatch):
    svc = MagicMock()
    svc.users().messages().send().execute.return_value = {"id": "m1", "threadId": "t1"}
    monkeypatch.setattr(gmail_tools, "service", lambda *a, **k: svc)
    out = gmail_tools.send(["to@y.com"], "Subj", "b", account="me@example.com", bcc=["bcc@y.com"])
    assert out["account"] == "me@example.com"
    line = _log()
    assert "gmail_send" in line and "account=me@example.com" in line
    assert "to@y.com" in line and "bcc@y.com" in line


# --- path confinement -------------------------------------------------------


def test_attachment_save_refuses_dest_outside_allowed_roots(monkeypatch, tmp_path):
    monkeypatch.setenv("GWS_ALLOWED_DIRS", str(tmp_path / "ok"))
    svc = MagicMock()
    svc.users().messages().attachments().get().execute.return_value = {"data": "QUJD"}
    monkeypatch.setattr(gmail_tools, "service", lambda *a, **k: svc)
    outside = tmp_path / "elsewhere"
    with pytest.raises(ValueError, match="outside the allowed folders"):
        gmail_tools.attachment_save("M", "A", filename="x", dest_dir=str(outside), account="me@example.com")
    assert not outside.exists()


def test_attachment_save_blocks_symlink_escape(monkeypatch, tmp_path):
    ok = tmp_path / "ok"
    ok.mkdir()
    target = tmp_path / "secret"
    target.mkdir()
    (ok / "link").symlink_to(target)
    monkeypatch.setenv("GWS_ALLOWED_DIRS", str(ok))
    svc = MagicMock()
    svc.users().messages().attachments().get().execute.return_value = {"data": "QUJD"}
    monkeypatch.setattr(gmail_tools, "service", lambda *a, **k: svc)
    with pytest.raises(ValueError):
        gmail_tools.attachment_save("M", "A", filename="x", dest_dir=str(ok / "link"), account="me@example.com")


def test_attachment_save_blocks_dotdot_traversal(monkeypatch, tmp_path):
    ok = tmp_path / "ok"
    ok.mkdir()
    monkeypatch.setenv("GWS_ALLOWED_DIRS", str(ok))
    with pytest.raises(ValueError):
        guards.require_within_roots(ok / ".." / "other", "dest_dir")


def test_upload_refuses_files_outside_allowed_roots(monkeypatch, tmp_path):
    monkeypatch.setenv("GWS_ALLOWED_DIRS", str(tmp_path / "ok"))
    svc = MagicMock()
    monkeypatch.setattr(drive_tools, "service", lambda *a, **k: svc)
    secret = tmp_path / "id_rsa"
    secret.write_text("PRIVATE KEY")
    with pytest.raises(ValueError, match="outside the allowed folders"):
        drive_tools.upload(str(secret), account="me@example.com")
    svc.files().create.assert_not_called()


# --- ownership transfer -----------------------------------------------------


def test_share_refuses_owner_role(monkeypatch):
    svc = MagicMock()
    monkeypatch.setattr(drive_tools, "service", lambda *a, **k: svc)
    with pytest.raises(ValueError, match="Ownership transfer is disabled"):
        drive_tools.share("F1", "stranger@evil.com", role="owner", account="me@example.com")
    svc.permissions().create.assert_not_called()


def test_permission_update_refuses_owner_role(monkeypatch):
    svc = MagicMock()
    monkeypatch.setattr(drive_tools, "service", lambda *a, **k: svc)
    with pytest.raises(ValueError):
        drive_tools.permission_update("F1", "P1", "owner", account="me@example.com")


def test_owner_role_allowed_only_with_explicit_env(monkeypatch):
    monkeypatch.setenv("GWS_ALLOW_OWNER_TRANSFER", "1")
    guards.refuse_owner_role("owner")  # does not raise


def test_share_is_audited(monkeypatch):
    svc = MagicMock()
    svc.permissions().create().execute.return_value = {"id": "p", "type": "user", "role": "reader"}
    monkeypatch.setattr(drive_tools, "service", lambda *a, **k: svc)
    drive_tools.share("F1", "a@b.com", role="reader", account="me@example.com")
    line = _log()
    assert "drive_share" in line and "account=me@example.com" in line and "a@b.com" in line


def test_share_without_account_fails_before_any_api_call(monkeypatch):
    svc = MagicMock()
    monkeypatch.setattr(drive_tools, "service", lambda *a, **k: svc)
    with pytest.raises(accounts.AccountError):
        drive_tools.share("F1", "a@b.com", role="reader")
    svc.permissions().create.assert_not_called()
