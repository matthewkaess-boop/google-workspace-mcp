# google-workspace-mcp (hardened fork)

One MCP server that lets Claude work with **several Google accounts at once**
(Gmail, Drive, Docs, Sheets, Calendar). Every request names the account it is
for, so "search my production inbox" and "draft from my personal account" can
sit side by side in one conversation.

This is a hardened fork of
[adelaidasofia/google-workspace-mcp](https://github.com/adelaidasofia/google-workspace-mcp)
(MIT). The original README is kept in [docs/UPSTREAM-README.md](docs/UPSTREAM-README.md)
and the original setup guide is [SETUP.md](SETUP.md). Branch: `hardening`.

## How you use it

Always say which account you mean:

> Search **production@…** for unread mail from last week.
> Draft a reply from **secretary@…** to that thread, but don't send it.
> Find the budget spreadsheet in **accounts@…** Drive.

Claude passes that address as `account` on every tool call. **If an account is
missing, the call fails** and lists your connected accounts. It never guesses.
To see what is connected, ask Claude to run `gws_account_list`.

## What changed from upstream

| Change | Why |
|---|---|
| `account` is required on every call. No default account. | A forgotten argument must not send or share from the wrong mailbox. |
| Every write is recorded in `~/.claude/google-workspace-mcp/audit.log` with the account, recipients and target. | You can always check what was sent, shared or changed, and from where. |
| `send`, `reply` and `draft` return the account they used, and `dry_run` shows it before anything goes out. | Lets you (and Claude) confirm the account before sending. |
| Attachment downloads and Drive uploads are limited to `~/.claude/google-workspace-mcp/downloads` and `.../uploads`. Add folders with `GWS_ALLOWED_DIRS`. | A hostile email or document cannot steer Claude into overwriting system files or uploading private files. |
| Handing over Drive ownership is refused unless `GWS_ALLOW_OWNER_TRANSFER=1`. | Prevents a prompt-injected "make X the owner". |
| The install-ping telemetry hook was removed. | No traffic to anyone but Google. |
| Upstream's plugin `.mcp.json` was removed. | It launched the wrong Python and would shadow this registration. |

Sending mail is still possible. The safety net is Claude's normal tool-approval
prompt, which now shows the account and recipients. For anything important, ask
Claude to run `dry_run` first.

## Where things live

| Thing | Location |
|---|---|
| This project | `~/Claude/Projects/google-workspace-mcp` |
| Python environment | `.venv/` in the project (Python 3.11, Homebrew) |
| Server registration | `~/.claude.json`, entry `google-workspace` (user scope) |
| OAuth client ID and secret | In that registration's environment. **Never in this repo or in chat.** |
| Account sign-in tokens | macOS Keychain, service `google-workspace-mcp` |
| List of connected accounts | `accounts_index.json` in the project (git-ignored) |
| Audit log | `~/.claude/google-workspace-mcp/audit.log` |
| Google Cloud project | **My First Project**, under the personal Google account. Consent screen: External, status **Testing**. |

## Weekly reconnect (while the app is in Testing)

Google expires the sign-in for apps in **Testing** mode after about 7 days. When
a tool says an account's login has expired, reconnect just that account:

1. Open a terminal in the project folder, or ask Claude to run this for you:
   ```bash
   cd ~/Claude/Projects/google-workspace-mcp && .venv/bin/python -u scripts/add_account.py
   ```
2. It prints a long **sign-in link** and waits. It does not open a browser.
3. Copy the link into a browser window that is **signed in to the account you
   are reconnecting** (a different browser or profile per account is fine).
4. Pick the account, click **Advanced → Go to Google Workspace MCP** on the
   "Google hasn't verified this app" screen, and approve the permissions.
5. The terminal prints `CONNECTED: <address>`. Done. A restart is normally not needed; if Claude still reports the old error, start a new session.

The link only works while the script is waiting. If it times out, run it again.

To stop the weekly reconnects, publish the consent screen to **In production**
(Google Cloud console → Google Auth Platform → Audience → Publish app). It was
blocked by the Branding page when we tried. If you retry it, check the
**Verification centre** page for what is missing, and do not add a logo
(that forces Google verification).

## Add another account

1. In Google Cloud console → Google Auth Platform → **Audience → Test users**,
   add the new address and save.
2. Run `scripts/add_account.py` as above and sign in with that account.
3. Workspace domains that restrict third-party apps need the client ID trusted
   once: Admin console → Security → API controls → **Manage Third-Party App
   Access**. Personal Gmail needs nothing extra.

## Remove an account

Ask Claude to run `gws_account_remove` with the address. That deletes the local
token. To also cut Google's side, remove the app at
https://myaccount.google.com/permissions while signed in as that account.

## Check that it works

Run the automated tests:

```bash
cd ~/Claude/Projects/google-workspace-mcp && .venv/bin/python -m pytest -q
```

That runs the 118 automated tests (no Google access needed). For a live check,
ask Claude to search each account with `limit 3`, and to try a `dry_run` send.

## If something goes wrong

| Symptom | Likely cause and fix |
|---|---|
| "`account` is required on every call" | You or Claude did not name an account. Name one. |
| "Your Google login for … expired" | Weekly Testing-mode expiry. Run the reconnect steps above. |
| Google shows **Access blocked … has not completed verification** | That address is not in **Audience → Test users**. Add it. |
| Google shows the app is not allowed for a Workspace address | The domain restricts third-party apps. Trust the client ID in that domain's Admin console (see Add another account). |
| `google-workspace` shows **failed** in a new session | Run `ls .venv/bin/python` in the project. If missing, rebuild with `/opt/homebrew/bin/python3.11 -m venv .venv && .venv/bin/pip install -e . pytest`, then check the registration in `~/.claude.json`. |
| Keychain asks for permission repeatedly | Choose **Always Allow**. If it keeps asking, say so. A less secure file-token fallback exists but is not recommended. |
| Wrong credentials registered | Run `scripts/register-server.sh`. It asks for the client ID and secret with hidden input and replaces the registration. |

## Housekeeping

- This session setup also has the original single-account Gmail and Drive
  connectors installed. If Claude picks one of those by mistake, disable them
  once you are happy with this server.
- Do not commit `client_secret.json`, `tokens.json` or `accounts_index.json`.
  They are git-ignored.
- Upstream changes are not merged automatically. To pull them in, compare
  against `adelaidasofia/google-workspace-mcp` and re-run the tests.

## Status

Connected and tested read-only on all four accounts. Not yet exercised: real
sends, shares and uploads, and the audit log after a first real write.

License: MIT, same as upstream. Original work © Adelaida Diaz-Roa.
