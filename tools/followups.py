"""Write, check and queue every due follow-up without a model. Zero LLM tokens.

A follow-up is due 7 days (limits.yaml follow_up_after_days) after a first email that got no reply.
It is always the same question, in the same thread, naming the two workflows the first email named:
"which of these takes your team the most hours, X or Y?". Those two workflows are stored on the
first touch (pipeline.py add-touch --workflows), so this script can fill the template itself:

    pipeline: first touch sent, 7 days, no reply, no follow-up yet
      -> add the follow_up touch          (pipeline.py add_touch)
      -> fill templates/follow.<lang>.txt
      -> lint                             (lint_email.py, follow-up rules)
      -> Gmail draft in the same thread   (gmail_draft.py draft)
      -> ready                            (send.py ready; follow-ups never need approval)
    send.py run sends follow-ups first, before new first emails.

A touch without stored workflows is listed for a hand-written follow-up instead.

Usage:
    python tools/followups.py prepare            # do it
    python tools/followups.py prepare --dry-run  # list what is due and the text it would write
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from argparse import Namespace

import lint_email
import send
import tenant

TITLES = re.compile(r"^(dr|prof|drs|ir|mr|ing|mag|dipl)\.?$", re.I)


def due(p, today):
    gap = int(tenant.limits().get("follow_up_after_days", 7))
    for org in p.get("orgs", []):
        if org.get("status") != "active":
            continue
        touches = org.get("touches", [])
        for c in org.get("contacts", []):
            mine = [t for t in touches if t.get("contact") == c["id"]]
            first = next((t for t in mine if t.get("kind") in ("first", "chain")), None)
            if not first or first.get("status") != "sent":
                continue
            if any(t.get("kind") == "follow_up" for t in mine):
                continue
            if (today - send.as_date(first["sent"])).days >= gap:
                yield org, c, first


def greeting_name(full: str, lang: str) -> str:
    parts = [w for w in (full or "").split() if not TITLES.match(w)]
    if not parts:
        return "Hello" if lang == "en" else ""
    return parts[0] if lang == "en" else " ".join(parts)


def fill(org, contact, first) -> str:
    lang = org.get("lang", "en")
    tpl = (tenant.TEMPLATES / f"follow.{lang}.txt").read_text(encoding="utf-8")
    w1, w2 = first["workflows"]
    return tpl.format(name=greeting_name(contact.get("name", ""), lang), w1=w1, w2=w2,
                      sender=tenant.config().get("sender", {}).get("first_name", ""))


def prepare(a):
    import gmail_draft
    import pipeline as pl
    today = dt.date.today()
    p = tenant.load(tenant.PIPELINE, {})
    done, by_hand, failed = [], [], []
    for org, contact, first in list(due(p, today)):
        label = f"{org['id']} / {contact['id']}"
        if len(first.get("workflows") or []) != 2:
            by_hand.append(f"{label}: no stored workflows, write the follow-up by hand")
            continue
        body = fill(org, contact, first)
        errors, _, _ = lint_email.lint(body, followup=True, lang=org.get("lang"))
        if errors:
            failed.append(f"{label}: lint {'; '.join(errors)}")
            continue
        if a.dry_run:
            done.append(f"{label}: would write\n      {body.strip().splitlines()[0]}")
            continue
        try:
            pl.add_touch(Namespace(org=org["id"], contact=contact["id"], kind="follow_up", workflows=None))
            tid = f"{contact['id']}-fu"
            path = tenant.DIR / "drafts" / f"{tid}.txt"
            path.write_text(body, encoding="utf-8")
            gmail_draft.draft(Namespace(touch=tid))
            code = send.cmd_ready(Namespace(touch=tid))
            (done if code == 0 else failed).append(f"{label}: {tid} {'queued' if code == 0 else 'held, see above'}")
        except SystemExit as exc:
            failed.append(f"{label}: {exc}")
    print(f"\nFOLLOW-UPS {'(dry run) ' if a.dry_run else ''}{len(done)}")
    for line in done or ["-"]:
        print("  " + line)
    if by_hand:
        print(f"\nWRITE BY HAND {len(by_hand)}")
        for line in by_hand:
            print("  " + line)
    if failed:
        print(f"\nFAILED {len(failed)}")
        for line in failed:
            print("  " + line)
    return 1 if failed else 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.exit(prepare(a))


if __name__ == "__main__":
    main()
