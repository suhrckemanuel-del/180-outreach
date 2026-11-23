"""What the daily run has to do today, in order. Read-only, zero LLM tokens.

Prints: replies waiting for Manuel, approvals waiting, follow-ups due, chain steps due,
organisations to close, and how many NEW first emails fit under today's cap after all of that.
Expires stale work: a planned or drafted touch older than 14 days is listed as STALE, not as due.

Usage:
    python tools/outreach_due.py
    python tools/outreach_due.py --date 2026-11-30
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

import send
import tenant

STALE_DAYS = 14


def plan(p, today):
    lim = tenant.limits()
    fu_gap = int(lim.get("follow_up_after_days", 7))
    chain_gap = int(lim.get("chain_gap_days", 4))
    out = {k: [] for k in ("REPLY", "APPROVE", "FOLLOW-UP", "CHAIN", "CLOSE", "STALE", "READY")}
    for org in p.get("orgs", []):
        touches = org.get("touches", [])
        if org.get("status") == "replied":
            for t in touches:
                if t.get("status") == "replied" and not t.get("answered"):
                    out["REPLY"].append(f"{org['name']}: thread {t.get('gmail_thread_id')} (read it with gmail_draft.py read)")
            continue
        if org.get("status") != "active":
            continue
        for t in touches:
            st = t.get("status")
            age = (today - send.as_date(t.get("drafted"))).days if t.get("drafted") else 0
            if st == "needs_approval":
                out["APPROVE"].append(f"{t['id']} ({org['name']})")
            elif st == "ready":
                out["READY"].append(t["id"])
            elif st in ("planned", "drafted") and age > STALE_DAYS:
                out["STALE"].append(f"{t['id']} ({st} {age}d): redo or drop")
        for c in org.get("contacts", []):
            mine = [t for t in touches if t.get("contact") == c["id"]]
            first = next((t for t in mine if t.get("kind") in ("first", "chain")), None)
            fu = next((t for t in mine if t.get("kind") == "follow_up"), None)
            if not first or first.get("status") != "sent":
                continue
            sent = send.as_date(first["sent"])
            if fu is None and (today - sent).days >= fu_gap:
                out["FOLLOW-UP"].append(f"{org['id']} / {c['id']}: first sent {sent}, write the question follow-up")
            if fu is not None and fu.get("status") == "sent" and (today - send.as_date(fu["sent"])).days >= chain_gap:
                people = {t.get("contact") for t in touches}
                maxp = int(tenant.config().get("targets", {}).get("max_people_per_org", 2))
                if len(people) < maxp:
                    out["CHAIN"].append(f"{org['id']}: follow-up to {c['id']} unanswered, write to a second person")
                elif (today - send.as_date(fu["sent"])).days >= fu_gap:
                    out["CLOSE"].append(f"{org['id']}: everyone written to, no reply. Close it")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", type=dt.date.fromisoformat, default=dt.date.today())
    a = ap.parse_args()
    p = tenant.load(tenant.PIPELINE, {})
    out = plan(p, a.date)
    cap, week = send.daily_cap(a.date)
    sent_today = sum(1 for r in send.sent_rows() if r[0].startswith(a.date.isoformat()))
    queued = len(out["READY"]) + len(out["APPROVE"]) + len(out["FOLLOW-UP"]) + len(out["CHAIN"])
    room = max(0, cap - sent_today - queued)
    print(f"{tenant.NAME} {a.date}  week {week}  cap {cap}  sent today {sent_today}  already queued {queued}")
    for key in ("REPLY", "APPROVE", "FOLLOW-UP", "CHAIN", "CLOSE", "STALE"):
        print(f"\n{key} ({len(out[key])})")
        for line in out[key] or ["-"]:
            print(f"  {line}")
    import pipeline as pl
    print(f"\nNEW FIRST EMAILS TO PREPARE TODAY: {room}  (next arm {pl.next_arm(p)})")


if __name__ == "__main__":
    main()
