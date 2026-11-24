"""The only way this kit sends. Zero LLM tokens.

Split in two so no model ever sends:
  - the drafting session calls `ready` on a drafted touch: every content and contact rule is checked,
    and the touch becomes `ready`, or `needs_approval` when tenant.yaml says Manuel must look first;
  - the scheduler runs `run` after the session: a plain loop that sends ready touches through the
    send window with a random gap between sends, re-checks every rule right before each send, and
    records the send in the pipeline, the send log and the registry in the same step.

Commands:
    python tools/send.py status
    python tools/send.py check --touch ID          reasons it would be held, changes nothing
    python tools/send.py ready --touch ID          drafted -> ready | needs_approval | held
    python tools/send.py approvals [--html]        what waits for Manuel, with the clean file to read;
                                                   --html also writes state/approvals.html to read them in
    python tools/send.py approve --touch ID [...]  Manuel's approval (never in the unattended run)
    python tools/send.py run [--dry-run] [--max N] the send loop (scheduler only)

Exit codes: 0 ok, 2 held, 1 error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import random
import re
import sys
import time

import lint_email
import registry
import tenant
from writer_lock import locked

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
SENT_LIKE = ("sent", "replied", "bounced", "opted_out", "no_reply")


# ---------- helpers ----------

def as_date(v):
    if v is None or isinstance(v, dt.date) and not isinstance(v, dt.datetime):
        return v
    return dt.date.fromisoformat(str(v)[:10])


def sent_rows():
    if not tenant.SENT_LOG.exists():
        return []
    return [ln.split("\t") for ln in tenant.SENT_LOG.read_text(encoding="utf-8").splitlines() if ln.strip()]


def daily_cap(today: dt.date) -> tuple[int, int]:
    """(cap, week number). Weeks count from the first real send, so the ramp never skips."""
    lim = tenant.limits()
    ramp = lim.get("ramp_per_week") or [10]
    rows = sent_rows()
    first = as_date(rows[0][0]) if rows else today
    week = max(0, (today - first).days // 7)
    return ramp[min(week, len(ramp) - 1)], week + 1


def find(pipeline, touch_id):
    for org in pipeline.get("orgs", []):
        for t in org.get("touches", []):
            if t["id"] == touch_id:
                return org, t
    return None, None


def config_todos() -> list[str]:
    cfg = tenant.config()
    out = []
    if str(cfg.get("sender", {}).get("address", "TODO")) == "TODO":
        out.append("tenant.yaml sender.address is TODO")
    if str(cfg.get("booking_link", "TODO")) == "TODO":
        out.append("tenant.yaml booking_link is TODO")
    return out


def needs_approval(org, t, pipeline) -> bool:
    if t.get("kind") == "follow_up" or t.get("approved"):
        return False
    rule = tenant.config().get("approval", {})
    if rule.get("tier1_first_emails") and int(org.get("tier", 2)) == 1:
        return True
    firsts_sent = sum(1 for o in pipeline.get("orgs", []) for x in o.get("touches", [])
                      if x.get("kind") in ("first", "chain") and x.get("status") in SENT_LIKE)
    return firsts_sent < int(rule.get("all_first_emails_until_sent", 0))


# ---------- the rules ----------

def content_and_contact_reasons(org, t, today) -> list[str]:
    """Everything that does not depend on the clock. Empty list = may go."""
    why = list(config_todos())
    lim = tenant.limits()
    if org is None or t is None:
        return why + ["touch not in the pipeline"]
    if org.get("status") != "active":
        why.append(f"organisation status is {org.get('status')}")
    if t.get("status") not in ("drafted", "ready", "needs_approval"):
        why.append(f"touch status is {t.get('status')}")
    if not t.get("draft_id"):
        why.append("no Gmail draft id: run gmail_draft.py draft --touch first")
    touches = org.get("touches", [])
    if any(x.get("status") in ("replied", "opted_out") for x in touches):
        why.append("someone at this organisation replied or opted out")

    contacts = tenant.load(tenant.CONTACTS, {}) or {}
    c = contacts.get(t.get("contact")) or {}
    addr = (c.get("email") or "").lower()
    if not addr or not c.get("source"):
        why.append("no address with a source in contacts.private.yaml")
    if not str(c.get("basis") or "").strip():
        why.append("no lawful basis for this contact in contacts.private.yaml (pipeline.py add-contact --basis)")
    supp = tenant.load(tenant.SUPPRESSION, {}) or {}
    if addr in (supp.get("addresses") or {}):
        why.append("address is on the suppression list")
    if org.get("domain") in (supp.get("domains") or {}) or tenant.domain_of(addr) in (supp.get("domains") or {}):
        why.append("organisation is on the suppression list")
    if any(x.get("status") == "bounced" and x.get("contact") == t.get("contact") for x in touches):
        why.append("this address bounced before")
    try:
        r = registry.blocked_reason(org.get("domain", ""), today)
        if r:
            why.append(r)
    except registry.RegistryError as exc:
        why.append(f"registry unreachable, failing closed: {exc}")

    others = [x for x in touches if x["id"] != t["id"] and x.get("status") in SENT_LIKE and x.get("sent")]
    if t.get("kind") in ("first", "chain"):
        people = {x.get("contact") for x in others} | {t.get("contact")}
        if len(people) > int(tenant.config().get("targets", {}).get("max_people_per_org", 2)):
            why.append("more people at this organisation than allowed")
        gap = int(lim.get("org_gap_days", 4))
        if any((today - as_date(x["sent"])).days < gap for x in others if x.get("contact") != t.get("contact")):
            why.append(f"another person here was written to less than {gap} days ago")
    if t.get("kind") == "follow_up":
        earlier = [x for x in others if x.get("kind") == "follow_up" and x.get("contact") == t.get("contact")]
        if len(earlier) >= int(lim.get("max_follow_ups_per_address", 1)):
            why.append("this address already had its follow-up")
        first = next((x for x in touches if x.get("contact") == t.get("contact") and x.get("kind") in ("first", "chain")), None)
        if not first or first.get("status") != "sent":
            why.append("the first email to this contact is not in status sent")
        elif (today - as_date(first["sent"])).days < int(lim.get("follow_up_after_days", 7)):
            why.append("follow-up is not due yet")

    body = tenant.DIR / (t.get("body") or "")
    if not t.get("body") or not body.exists():
        why.append(f"draft file {t.get('body')} not found")
    else:
        errors, _, _ = lint_email.lint(body.read_text(encoding="utf-8"),
                                       followup=t.get("kind") == "follow_up", lang=org.get("lang"))
        why += [f"lint: {e}" for e in errors]
    return why


def clock_reasons(org, today_rows, now: dt.datetime) -> list[str]:
    lim = tenant.limits()
    why = []
    if tenant.STOP.exists():
        why.append(f"STOP: {tenant.STOP.read_text(encoding='utf-8').strip() or 'state/STOP exists'}")
    if DAYS[now.weekday()] not in lim.get("send_weekdays", []):
        why.append("not a send day")
    start, end = lim.get("send_window", ["08:30", "16:30"])
    if not (start <= now.strftime("%H:%M") <= end):
        why.append(f"outside the send window {start}-{end}")
    if now.date() > as_date(lim.get("last_send_date", "2999-12-31")):
        why.append("after last_send_date")
    cap, _ = daily_cap(now.date())
    if len(today_rows) >= cap:
        why.append(f"daily cap {cap} reached")
    if org is not None and any(r[1] == org["id"] for r in today_rows):
        why.append("this organisation already got an email today")
    return why


def auto_pause_reason(pipeline) -> str | None:
    cfg = tenant.limits().get("auto_pause", {})
    touches = [t for o in pipeline.get("orgs", []) for t in o.get("touches", []) if t.get("sent")]
    touches.sort(key=lambda t: str(t["sent"]))
    last = touches[-100:]
    bounced = sum(1 for t in last if t.get("status") == "bounced")
    if len(last) >= int(cfg.get("min_sent", 40)) and bounced / len(last) > float(cfg.get("bounce_rate", 0.03)):
        return f"bounce rate {bounced}/{len(last)} over the last sends is above {cfg.get('bounce_rate')}"
    today = dt.date.today().isoformat()
    today_bounces = sum(1 for t in touches if t.get("status") == "bounced" and str(t.get("reply_seen", "")) == today)
    if today_bounces >= int(cfg.get("max_bounces_per_day", 3)):
        return f"{today_bounces} bounces recorded today"
    return None


# ---------- commands ----------

def cmd_status(_):
    now = dt.datetime.now()
    cap, week = daily_cap(now.date())
    rows = sent_rows()
    today = [r for r in rows if r[0].startswith(now.date().isoformat())]
    p = tenant.load(tenant.PIPELINE, {})
    counts = {}
    for o in p.get("orgs", []):
        for t in o.get("touches", []):
            counts[t.get("status")] = counts.get(t.get("status"), 0) + 1
    print(f"tenant {tenant.NAME}  week {week}  sent today {len(today)}/{cap}  sent total {len(rows)}")
    print("STOP:", tenant.STOP.read_text(encoding="utf-8").strip() if tenant.STOP.exists() else "no")
    print("touches:", ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: str(kv[0]))) or "none")
    for todo in config_todos():
        print("BLOCKS SENDING:", todo)


def cmd_check(a):
    p = tenant.load(tenant.PIPELINE, {})
    org, t = find(p, a.touch)
    now = dt.datetime.now()
    today_rows = [r for r in sent_rows() if r[0].startswith(now.date().isoformat())]
    why = content_and_contact_reasons(org, t, now.date()) + clock_reasons(org, today_rows, now)
    if t is not None and needs_approval(org, t, p):
        why.append("needs Manuel's approval")
    print("OK" if not why else "HELD: " + "; ".join(why))
    return 0 if not why else 2


def cmd_ready(a):
    with locked("claude"):
        p = tenant.load(tenant.PIPELINE, {})
        org, t = find(p, a.touch)
        why = content_and_contact_reasons(org, t, dt.date.today())
        if why:
            print(f"HELD {a.touch}: " + "; ".join(why))
            return 2
        t["status"] = "needs_approval" if needs_approval(org, t, p) else "ready"
        tenant.save(tenant.PIPELINE, p)
    print(f"{a.touch}: {t['status']}")
    return 0


APPROVALS_HTML = tenant.STATE / "approvals.html"
CARD_FACTS = ("WORKFLOW", "FUNDING", "PEOPLE", "EMAILS", "VERDICT")
URL = re.compile(r"https?://[^\s)\]>\"',]+")


def _linked(text: str) -> str:
    """Escape text; turn http(s) URLs into links (escaped too). Nothing else becomes markup."""
    out, pos = [], 0
    for m in URL.finditer(text or ""):
        url = m.group(0).rstrip(".;:")
        out.append(html.escape(text[pos:m.start()]))
        out.append(f'<a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">{html.escape(url)}</a>')
        pos = m.start() + len(url)
    out.append(html.escape((text or "")[pos:]))
    return "".join(out)


def card_facts(org) -> list[tuple[str, str]]:
    path = tenant.DIR / (org.get("card") or "")
    if not org.get("card") or not path.is_file():
        return []
    facts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, val = line.partition(":")
        if key.strip().upper() in CARD_FACTS and val.strip():
            facts.append((key.strip().upper(), val.strip()))
    return facts


def _clean_text(org, t) -> str:
    clean = tenant.DIR / (t.get("body") or "").replace(".txt", ".clean.txt")
    if clean.is_file():
        return clean.read_text(encoding="utf-8")
    body = tenant.DIR / (t.get("body") or "")
    if body.is_file():
        return lint_email.lint(body.read_text(encoding="utf-8"), followup=t.get("kind") == "follow_up",
                               lang=org.get("lang"))[2]
    return "(draft file not found)"


def _footer(org, contact, t) -> str:
    try:
        import gmail_draft
        return gmail_draft.build_footer(tenant.config(), org, contact, follow=t.get("kind") == "follow_up",
                                        lang=org.get("lang", "en"))
    except Exception as exc:  # the page must still render without the Google libraries
        return f"(footer not shown: {exc})"


def write_approvals_html(waiting) -> None:
    contacts = tenant.load(tenant.CONTACTS, {}) or {}
    e = html.escape
    sections = []
    for o, t in waiting:
        c = contacts.get(t.get("contact")) or {}
        facts = "".join(f"<dt>{e(k.title())}</dt><dd>{_linked(v)}</dd>" for k, v in card_facts(o)) \
            or "<dd>(no card)</dd>"
        sections.append(f"""<section id="{e(t['id'], quote=True)}">
<h2>{e(o.get('name', ''))}</h2>
<p class="meta">touch <code>{e(t['id'])}</code> · tier {e(str(o.get('tier', '')))} · arm {e(str(t.get('arm', '')))} ·
{e(str(o.get('segment', '')))} · {e(str(o.get('city', '')))} · {e(str(o.get('lang', '')))}</p>
<p class="meta">to {e(c.get('email', '(no address)'))} ({e(c.get('name', '') or '')}), found on {_linked(c.get('source', ''))}</p>
<pre class="email">{e(_clean_text(o, t).rstrip())}

{e(_footer(o, c, t).rstrip())}</pre>
<h3>Card facts</h3>
<dl>{facts}</dl>
</section>""")
    ids = " ".join(t["id"] for _, t in waiting)
    stamp = dt.datetime.now().isoformat(timespec="minutes")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Approvals waiting</title>
<style>
:root {{ color-scheme: light dark; --bg: #fff; --fg: #1b1b1b; --muted: #5c5c5c; --line: #d8d8d8; --box: #f6f6f4; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #161616; --fg: #e8e8e8; --muted: #a0a0a0; --line: #3a3a3a; --box: #202020; }} }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, sans-serif; max-width: 52rem; margin: 0 auto; padding: 1rem; }}
section {{ border-top: 1px solid var(--line); padding: 1rem 0 1.5rem; }}
.meta {{ color: var(--muted); margin: .2rem 0; }}
pre {{ background: var(--box); padding: .8rem; white-space: pre-wrap; overflow-wrap: anywhere; font: 14px/1.5 ui-monospace, monospace; }}
dt {{ font-weight: 600; margin-top: .5rem; }} dd {{ margin: 0 0 0 1rem; overflow-wrap: anywhere; }}
a {{ color: inherit; }}
</style></head><body>
<h1>{len(waiting)} first emails waiting for approval</h1>
<p class="meta">Tenant {e(tenant.NAME)}, written {e(stamp)}. Approving stays a command, run by Manuel:</p>
<pre>python tools/send.py approve --touch {e(ids) if ids else 'ID [ID ...]'}</pre>
{''.join(sections) or '<p>Nothing is waiting.</p>'}
</body></html>
"""
    APPROVALS_HTML.parent.mkdir(parents=True, exist_ok=True)
    APPROVALS_HTML.write_text(page, encoding="utf-8")


def cmd_approvals(a):
    p = tenant.load(tenant.PIPELINE, {})
    waiting = [(o, t) for o in p.get("orgs", []) for t in o.get("touches", []) if t.get("status") == "needs_approval"]
    for o, t in waiting:
        clean = (t.get("body") or "").replace(".txt", ".clean.txt")
        print(f"{t['id']:34} {o['name'][:30]:30} tier {o.get('tier')} arm {t.get('arm')}  read: tenants/{tenant.NAME}/{clean}")
    print(f"{len(waiting)} waiting. Approve with: python tools/send.py approve --touch ID [ID ...]")
    if getattr(a, "html", False):
        write_approvals_html(waiting)
        print(f"page: {APPROVALS_HTML}")


def cmd_approve(a):
    with locked("manuel"):
        p = tenant.load(tenant.PIPELINE, {})
        for tid in a.touch:
            org, t = find(p, tid)
            if t is None or t.get("status") != "needs_approval":
                print(f"skip {tid}: not waiting for approval")
                continue
            t["approved"] = True
            t["approved_on"] = dt.date.today().isoformat()
            t["status"] = "ready"
            print(f"approved {tid}")
        tenant.save(tenant.PIPELINE, p)


def next_ready(p):
    order = {"follow_up": 0, "chain": 1, "first": 2}
    cands = [(o, t) for o in p.get("orgs", []) for t in o.get("touches", []) if t.get("status") == "ready"]
    cands.sort(key=lambda ot: (order.get(ot[1].get("kind"), 3), int(ot[0].get("tier", 2)), str(ot[1].get("drafted"))))
    return cands


def cmd_run(a):
    import gmail_draft
    lim = tenant.limits()
    lo, hi = lim.get("gap_seconds", [180, 480])
    sent_now, skipped = [], set()
    while True:
        now = dt.datetime.now()
        rows = sent_rows()
        today_rows = [r for r in rows if r[0].startswith(now.date().isoformat())]
        p = tenant.load(tenant.PIPELINE, {})
        pause = auto_pause_reason(p)
        if pause:
            tenant.STOP.write_text(f"auto-pause {now.isoformat(timespec='minutes')}: {pause}\n", encoding="utf-8")
            print("AUTO-PAUSE:", pause)
            break
        global_why = clock_reasons(None, today_rows, now)
        if global_why:
            print("stop:", "; ".join(global_why))
            break
        if a.max is not None and len(sent_now) >= a.max:
            break
        if a.dry_run and len(today_rows) + len(sent_now) >= daily_cap(now.date())[0]:
            print("daily cap reached (dry run)")
            break
        cands = [ot for ot in next_ready(p) if ot[1]["id"] not in skipped]
        if not cands:
            print("nothing ready")
            break
        org, t = cands[0]
        why = content_and_contact_reasons(org, t, now.date()) + clock_reasons(org, today_rows, now)
        if needs_approval(org, t, p):
            why.append("needs Manuel's approval")
        if why:
            print(f"held {t['id']}: " + "; ".join(why))
            skipped.add(t["id"])
            continue

        # random gap since the last send, never a burst
        if rows:
            last = dt.datetime.fromisoformat(rows[-1][0])
            wait = random.uniform(lo, hi) - (now - last).total_seconds()
            if wait > 0 and not a.dry_run:
                end = dt.datetime.combine(now.date(), dt.time.fromisoformat(lim["send_window"][1]))
                if now + dt.timedelta(seconds=wait) > end:
                    print("send window ends before the next gap")
                    break
                time.sleep(wait)
        if a.dry_run:
            print(f"would send {t['id']} ({org['name']}, {t.get('kind')}, arm {t.get('arm')})")
            skipped.add(t["id"])
            sent_now.append(t["id"])
            continue

        try:
            res = gmail_draft.send_draft(t["draft_id"])
        except BaseException as exc:  # includes SystemExit from a dead login
            print(f"SEND FAILED {t['id']}: {exc}")
            tenant.STOP.write_text(f"send failed {dt.datetime.now().isoformat(timespec='minutes')}: {exc}\n",
                                   encoding="utf-8")
            break
        stamp = dt.datetime.now().isoformat(timespec="seconds")
        with locked("sender"):
            p = tenant.load(tenant.PIPELINE, {})
            org, t = find(p, t["id"])
            t.update(status="sent", sent=stamp, gmail_thread_id=res["thread_id"], message_id=res["message_id"])
            tenant.save(tenant.PIPELINE, p)
            tenant.SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
            with tenant.SENT_LOG.open("a", encoding="utf-8") as fh:
                fh.write("\t".join([stamp, org["id"], t["id"], t.get("kind", ""), t.get("arm", ""),
                                    str(org.get("tier", "")), t["draft_id"]]) + "\n")
        try:
            registry.claim(org["domain"], org["name"], "contacted")
        except registry.RegistryError as exc:
            print(f"warn  registry not updated for {org['id']}: {exc}")
        sent_now.append(t["id"])
        print(f"SENT {stamp} {t['id']} ({org['name']})")

    print(f"run done: {len(sent_now)} {'would be ' if a.dry_run else ''}sent")
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    for name in ("check", "ready"):
        s = sub.add_parser(name)
        s.add_argument("--touch", required=True)
    apv = sub.add_parser("approvals")
    apv.add_argument("--html", action="store_true", help="also write state/approvals.html")
    ap_ = sub.add_parser("approve")
    ap_.add_argument("--touch", nargs="+", required=True)
    r = sub.add_parser("run")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--max", type=int)
    a = ap.parse_args()
    fn = {"status": cmd_status, "check": cmd_check, "ready": cmd_ready, "approvals": cmd_approvals,
          "approve": cmd_approve, "run": cmd_run}[a.cmd]
    sys.exit(fn(a) or 0)


if __name__ == "__main__":
    main()
