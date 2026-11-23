"""Google OAuth for one tenant's sending inbox. Zero LLM tokens.

The token lives in tenants/<name>/private/gmail_token.json, so each sending inbox has its own.
Scopes: gmail.compose (create and send drafts) and gmail.readonly (read replies).

The 7-day trap from the job kit: an OAuth app in "Testing" mode loses its refresh token after
7 days and the run fails silently. On a Google Workspace domain such as 180dc.org, create the
OAuth consent screen as "Internal" (only that domain's users), which has no 7-day expiry.
See docs/setup.md.
"""

from __future__ import annotations

import json
import sys

import tenant

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]
CREDS = tenant.GMAIL_CREDS
TOKEN = tenant.GMAIL_TOKEN


def token_info() -> dict:
    if not TOKEN.exists():
        return {}
    return json.loads(TOKEN.read_text(encoding="utf-8"))


def load_credentials(*, reauth=False, allow_browser=False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN.exists() and not reauth:
        creds = Credentials.from_authorized_user_file(str(TOKEN), GMAIL_SCOPES)
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:  # refresh token revoked or expired
                sys.exit(f"GMAIL_LOGIN_EXPIRED: {exc}. Run: python tools/gmail_draft.py auth")
            TOKEN.write_text(creds.to_json(), encoding="utf-8")
        else:
            creds = None
    if creds is None:
        if not allow_browser:
            sys.exit("GMAIL_LOGIN_EXPIRED: no usable token. Run: python tools/gmail_draft.py auth")
        if not CREDS.exists():
            sys.exit(f"Missing {CREDS}. See docs/setup.md.")
        TOKEN.parent.mkdir(parents=True, exist_ok=True)
        creds = InstalledAppFlow.from_client_secrets_file(str(CREDS), GMAIL_SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds
