"""Where a tenant's files live. Every tool imports this instead of hard-coding paths. Zero LLM tokens.

One tenant = one sender organisation (180DC Delft & Rotterdam today; one.immo or another client
later). Everything specific to it sits in tenants/<name>/:

    tenant.yaml       who sends, booking link, footer, target filter, arms, approval rules
    limits.yaml       ramp, send window, gaps, caps
    ledger.yaml       the only claims an email may make about the sender ([claim:ID])
    pipeline.yaml     organisations, contacts (no addresses), touches
    templates/        email skeletons per arm and language
    state/            send log, run logs, reports, local registry fallback
    private/          gitignored: contacts.private.yaml, suppression.private.yaml, gmail_*.json

Pick the tenant with the env var OUTREACH_TENANT (default below). OUTREACH_ROOT overrides the repo
root, which the self-test uses to run against a throwaway copy.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

DEFAULT_TENANT = "180dc-delft-rotterdam"
ROOT = Path(os.environ.get("OUTREACH_ROOT") or Path(__file__).resolve().parents[1])
NAME = os.environ.get("OUTREACH_TENANT", DEFAULT_TENANT)
DIR = ROOT / "tenants" / NAME

TENANT_FILE = DIR / "tenant.yaml"
LIMITS = DIR / "limits.yaml"
LEDGER = DIR / "ledger.yaml"
PIPELINE = DIR / "pipeline.yaml"
TEMPLATES = DIR / "templates"
STATE = DIR / "state"
PRIVATE = DIR / "private"
CONTACTS = PRIVATE / "contacts.private.yaml"
SUPPRESSION = PRIVATE / "suppression.private.yaml"
SENT_LOG = STATE / "sent.log"
STOP = STATE / "STOP"
LOCK = STATE / "writer.lock"
REGISTRY_LOCAL = STATE / "registry.local.yaml"
REPORT = STATE / "daily-report.md"
WEEKLY = STATE / "weekly-review.md"
GMAIL_CREDS = PRIVATE / "gmail_credentials.json"
GMAIL_TOKEN = PRIVATE / "gmail_token.json"


def load(path: Path, default=None):
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return default if data is None else data


def save(path: Path, data) -> None:
    """Write YAML atomically: a crash mid-write never leaves half a pipeline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    os.replace(tmp, path)


def config() -> dict:
    return load(TENANT_FILE, {})


def limits() -> dict:
    return load(LIMITS, {})


def domain_of(address_or_url: str) -> str:
    """example.org from 'a@example.org', 'https://www.example.org/x' or 'example.org'."""
    s = (address_or_url or "").strip().lower()
    if "@" in s:
        s = s.split("@", 1)[1]
    s = s.split("://", 1)[-1].split("/", 1)[0]
    return s[4:] if s.startswith("www.") else s
