"""Plan and log the calls Manuel makes himself. Zero LLM tokens: it never dials and never fetches.

A call is not an email touch, so it does not live in pipeline.yaml: calls sit in
tenants/<t>/state/calls.yaml and send.py never reads them. `calls.py due` prints today's calls with the
organisation, the number printed in its dossier, and the dossier's opener, so Manuel can pick up the phone.

    python tools/calls.py add --org maaszicht --due 2026-11-27 [--script dossiers/maaszicht.md] [--phone N]
    python tools/calls.py list [--all]
    python tools/calls.py due [--date YYYY-MM-DD]
    python tools/calls.py log --org maaszicht --outcome no_answer|callback|call_booked|not_interested|wrong_person [--note "..."]

`log --outcome call_booked` records the outcome in the pipeline (`pipeline.py set --outcome call`).
`log --outcome not_interested` suppresses the domain the way an email opt-out does. A call record only
ever names an organisation, a date and an outcome; no staff names are stored here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from argparse import Namespace
from pathlib import Path

import tenant

CALLS = tenant.STATE / "calls.yaml"
OUTCOMES = ["no_answer", "callback", "call_booked", "not_interested", "wrong_person"]
# A number printed in the organisation's own dossier (Dutch landline or mobile, +31 or 0 form).
PHONE_RE = re.compile(r"(?:(?:\+|00)\s?31|0)[\s-]?\d{2,3}[\s-]?\d{2,3}[\s-]?\d{2,4}")
OPENER_HEAD = re.compile(r"(?i)^#*\s*(opener|opening|openingszin|first two sentences|intro)")


def load() -> list[dict]:
    return (tenant.load(CALLS, {}) or {}).get("calls") or []


def save(calls: list[dict]) -> None:
    tenant.save(CALLS, {"calls": calls})


def _org_row(org_id: str) -> dict:
    p = tenant.load(tenant.PIPELINE, {}) or {}
    return next((o for o in p.get("orgs", []) if o.get("id") == org_id), {})


def _dossier_text(script: str | None) -> str:
    if not script:
        return ""
    path = Path(script)
    if not path.is_absolute():
        path = tenant.DIR / path
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def phone_for(record: dict, text: str) -> str:
    """The number to dial: as given on add, else the first one printed in the dossier. Never guessed."""
    if record.get("phone"):
        return record["phone"]
    m = PHONE_RE.search(text or "")
    return m.group(0) if m else "no number in the dossier"


def opener_of(text: str) -> str:
    """The dossier's opener: the lines under an opener heading, else its first full paragraph."""
    lines = [x.strip() for x in (text or "").splitlines()]
    for i, line in enumerate(lines):
        if OPENER_HEAD.search(line):
            rest = " ".join(x for x in lines[i + 1:i + 5] if x and not x.startswith("#"))
            if rest:
                return rest[:400]
    for line in lines:
        if len(line) >= 60 and not line.startswith("#") and not line.startswith("|"):
            return line[:400]
    return "(no opener in the dossier)"


def add(a) -> None:
    try:
        due = dt.date.fromisoformat(a.due).isoformat()
    except ValueError:
        sys.exit(f"--due must be YYYY-MM-DD, not {a.due!r}")
    calls = load()
    if any((c.get("org"), c.get("status")) == (a.org, "planned") for c in calls):
        sys.exit(f"{a.org} already has a planned call; log it first")
    if a.script and not (tenant.DIR / a.script).exists() and not Path(a.script).exists():
        print(f"warn  no dossier at {a.script}; the call will print without an opener")
    calls.append({"org": a.org, "due": due, "script": a.script or "", "phone": a.phone or "",
                  "status": "planned", "outcome": "", "note": "", "made": ""})
    save(calls)
    org = _org_row(a.org)
    name = org.get("name") or a.org
    if not org:
        print(f"warn  {a.org} is not in the pipeline; a booked call cannot be recorded there")
    print(f"call planned: {name} on {due}")


def _fmt(c: dict) -> str:
    org = _org_row(c.get("org", ""))
    name = org.get("name") or c.get("org", "")
    due = c.get("due", "")
    overdue = c.get("status") == "planned" and due < dt.date.today().isoformat()
    tail = f"  {c.get('outcome')}" + (f"  {c.get('note')}" if c.get("note") else "")
    return f"{due}{' OVERDUE' if overdue else ''}  {c.get('org'):<24} {name[:32]:<32} {c.get('status')}{tail}"


def list_calls(a) -> None:
    calls = load()
    if not a.all:
        calls = [c for c in calls if c.get("status") == "planned"]
    if not calls:
        print("no calls" + ("" if a.all else " planned"))
        return
    for c in sorted(calls, key=lambda x: (x.get("due", ""), x.get("org", ""))):
        print(_fmt(c))


def due(a) -> None:
    today = a.date
    calls = [c for c in load() if c.get("status") == "planned" and c.get("due", "9999") <= today.isoformat()]
    if not calls:
        print(f"no calls due on {today.isoformat()}")
        return
    for c in sorted(calls, key=lambda x: (x.get("due", ""), x.get("org", ""))):
        text = _dossier_text(c.get("script"))
        org = _org_row(c.get("org", ""))
        print(f"{c.get('org')}  ({org.get('name') or c.get('org')})  due {c.get('due')}")
        print(f"  number: {phone_for(c, text)}")
        print(f"  dossier: {c.get('script') or '-'}")
        print(f"  opener: {opener_of(text)}")


def _suppress_call(org_id: str) -> None:
    """Same effect as an email opt-out: the domain is never contacted again for this tenant."""
    org = _org_row(org_id)
    domain = tenant.domain_of(org.get("domain", ""))
    data = tenant.load(tenant.SUPPRESSION, {}) or {}
    if domain:
        data.setdefault("domains", {})[domain] = f"not interested on the phone {dt.date.today().isoformat()}"
        tenant.save(tenant.SUPPRESSION, data)
    if org:
        from writer_lock import locked
        with locked("claude"):
            p = tenant.load(tenant.PIPELINE, {})
            row = next((o for o in p.get("orgs", []) if o.get("id") == org_id), None)
            if row:
                row["status"] = "opted_out"
                tenant.save(tenant.PIPELINE, p)
        try:
            import registry
            registry.claim(org["domain"], org.get("name", org_id), "opted_out")
        except Exception as exc:  # noqa: BLE001 - the suppression above already holds
            print(f"warn  registry not updated: {exc}")


def log(a) -> None:
    calls = load()
    open_calls = [c for c in calls if c.get("org") == a.org and c.get("status") == "planned"]
    if not open_calls:
        sys.exit(f"no planned call for {a.org}; add it first")
    rec = sorted(open_calls, key=lambda x: x.get("due", ""))[0]
    rec.update(status="done", outcome=a.outcome, note=a.note or "", made=dt.date.today().isoformat())
    save(calls)
    if a.outcome == "call_booked":
        org = _org_row(a.org)
        if org:
            import pipeline
            try:
                pipeline.set_org(Namespace(org=a.org, status=None, outcome="call"))
            except SystemExit as exc:  # the call is logged either way
                print(f"warn  pipeline not updated: {exc}")
    elif a.outcome == "not_interested":
        _suppress_call(a.org)
    print(f"{a.org}: {a.outcome}" + (f" ({a.note})" if a.note else ""))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ad = sub.add_parser("add")
    ad.add_argument("--org", required=True)
    ad.add_argument("--due", required=True, help="YYYY-MM-DD")
    ad.add_argument("--script", help="dossier path, for its opener and printed number")
    ad.add_argument("--phone", help="only a number printed on the organisation's own page")
    li = sub.add_parser("list")
    li.add_argument("--all", action="store_true", help="include calls already made")
    du = sub.add_parser("due")
    du.add_argument("--date", type=dt.date.fromisoformat, default=dt.date.today())
    lo = sub.add_parser("log")
    lo.add_argument("--org", required=True)
    lo.add_argument("--outcome", required=True, choices=OUTCOMES)
    lo.add_argument("--note")
    a = ap.parse_args()
    {"add": add, "list": list_calls, "due": due, "log": log}[a.cmd](a)


if __name__ == "__main__":
    main()
