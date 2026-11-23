"""Numbers for the Sunday review, by arm and by tier. Read-only, zero LLM tokens.

Counts first emails (first + chain) per organisation contact and what came back. "Positive" is an
organisation whose outcome is call, proposal or signed (set with pipeline.py set --outcome).
Read the arms only as a direction: at ~30-50 per arm, two replies either way is noise.

Usage:
    python tools/stats.py [--since 2026-11-23]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

import send
import tenant


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", type=dt.date.fromisoformat)
    a = ap.parse_args()
    p = tenant.load(tenant.PIPELINE, {})
    groups = {}
    for org in p.get("orgs", []):
        firsts = [t for t in org.get("touches", []) if t.get("kind") in ("first", "chain") and t.get("sent")]
        if a.since:
            firsts = [t for t in firsts if send.as_date(t["sent"]) >= a.since]
        for t in firsts:
            for key in (f"arm {t.get('arm', '?')}", f"tier {org.get('tier', '?')}", "all"):
                g = groups.setdefault(key, {"sent": 0, "replied": 0, "positive": 0, "opted_out": 0, "bounced": 0})
                g["sent"] += 1
                thread = [x for x in org["touches"] if x.get("gmail_thread_id") == t.get("gmail_thread_id")]
                if any(x.get("status") == "replied" for x in thread):
                    g["replied"] += 1
                if org.get("outcome") in ("call", "proposal", "signed") and any(x.get("status") == "replied" for x in thread):
                    g["positive"] += 1
                if any(x.get("status") == "opted_out" for x in thread):
                    g["opted_out"] += 1
                if t.get("status") == "bounced":
                    g["bounced"] += 1
    total = len(send.sent_rows())
    print(f"{tenant.NAME}: {total} emails sent in total (first + follow-ups)\n")
    print(f"{'group':8} {'sent':>5} {'replied':>8} {'positive':>9} {'opt-out':>8} {'bounced':>8}")
    for key in sorted(groups, key=lambda k: (k == "all", k)):
        g = groups[key]
        rate = f"{100 * g['replied'] / g['sent']:.0f}%" if g["sent"] else "-"
        print(f"{key:8} {g['sent']:5} {g['replied']:5} {rate:>4} {g['positive']:6} {g['opted_out']:8} {g['bounced']:8}")
    signed = sum(1 for o in p.get("orgs", []) if o.get("outcome") == "signed")
    calls = sum(1 for o in p.get("orgs", []) if o.get("outcome") in ("call", "proposal", "signed"))
    print(f"\ncalls or better: {calls}   signed: {signed}   goal: 2-3 signed by mid-January")


if __name__ == "__main__":
    main()
