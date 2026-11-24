"""Gmail for the outreach kit: drafts, reply reading and sync, report mail. Zero LLM tokens.

Every command works from the pipeline, not from free-typed flags: `draft --touch ID` finds the
address, the language, the thread and the footer itself, so a session cannot guess a subject, drop
the opt-out line or reply in the wrong thread.

Commands:
  auth                     one-time browser login for the tenant's inbox (docs/setup.md)
  auth-status [--check]    token present and working? --check exits 3 when the login is dead
  draft --touch ID         lint the touch's body, add the footer and the List-Unsubscribe header,
                           create (or replace) the Gmail draft
  read --thread ID         print a thread's messages as plain text (for answering replies)
  sync [--days N] [--apply]  classify new messages in every sent thread, plus bounces:
                           human | opt_out | bounce | auto, plus "unsubscribe" mails sent by a
                           recipient's mail client (a new message, not a reply in our thread).
                           --apply records them in the pipeline, the suppression list and the registry
  mail-self --body FILE    mail the daily report or weekly review to the sending inbox

Sending is not here. Only tools/send.py sends, through send_draft() below.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import re
import sys
from email.message import EmailMessage
from pathlib import Path

import google_auth
import lint_email
import registry
import tenant
from writer_lock import locked

HUMAN, OPT_OUT, BOUNCE, AUTO = "human", "opt_out", "bounce", "auto"
AUTO_SUBJECT = re.compile(
    r"automatic reply|auto(matic)?[- ]?reply|out of (the )?office|afwezig|automatisch antwoord|"
    r"abwesenheit|automatische antwort|vacation|holiday|vakantie|urlaub|delivery status|undeliverable|"
    r"niet bezorgd|unzustellbar", re.I)
OPT_OUT_PHRASE = re.compile(
    r"not interested|no interest|no thank|geen interesse|kein interesse|unsubscribe|uitschrijven|afmelden|"
    r"abmelden|remove (me|us)|take (me|us) off|do not (contact|email|write)|don't (contact|email|write)|"
    r"niet (meer )?(mailen|benaderen)|nicht mehr (kontaktieren|schreiben|anschreiben)", re.I)
OPT_OUT_SHORT = re.compile(r"^\s*(no|nee|nein|stop|nope)\b[\s.!,]*(thanks?|thank you|bedankt|danke)?[\s.!]*$", re.I)
# A reply (or a mail client's unsubscribe link, from our List-Unsubscribe header) whose subject or
# body is just "unsubscribe": an opt-out, like "no".
UNSUBSCRIBE_ONLY = re.compile(r"^\s*((re|aw|fw|fwd|antw)\s*:\s*)*(unsubscribe|uitschrijven|afmelden|abmelden)[\s.!]*$", re.I)
QUOTE_START = re.compile(r"\s(On|Op|Am|Le) .{5,80}(wrote|schreef|schrieb|a écrit)\s?:|-----Original|Von: |From: ", re.I)


def service(*, allow_browser=False):
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=google_auth.load_credentials(allow_browser=allow_browser),
                 cache_discovery=False)


def my_address(gm) -> str:
    return gm.users().getProfile(userId="me").execute()["emailAddress"].lower()


_SENDER_OK = False


def assert_sender(gm) -> str:
    """The Gmail login must be the tenant's sending inbox. A login made with the wrong account in the
    browser (a personal Gmail) would otherwise send from that account without any warning."""
    global _SENDER_OK
    me = my_address(gm)
    want = str(tenant.config().get("sender", {}).get("address", "TODO")).lower()
    if want == "todo":
        sys.exit(f"tenant.yaml sender.address is TODO (the Gmail login is {me})")
    if me != want:
        sys.exit(f"WRONG_ACCOUNT: the Gmail login is {me}, but tenant.yaml says {want}. "
                 "Run: python tools/gmail_draft.py auth and pick the 180DC account in the browser")
    _SENDER_OK = True
    return me


def header(message, name):
    for h in message.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ---------- pipeline lookups ----------

def find_touch(pipeline, touch_id):
    for org in pipeline.get("orgs", []):
        for t in org.get("touches", []):
            if t["id"] == touch_id:
                return org, t
    sys.exit(f"touch {touch_id} not in the pipeline")


def first_thread_for(org, contact_id):
    for t in org.get("touches", []):
        if t.get("contact") == contact_id and t.get("kind") in ("first", "chain") and t.get("gmail_thread_id"):
            return t["gmail_thread_id"]
    return None


def short_source(url: str) -> str:
    s = re.sub(r"^https?://(www\.)?", "", url or "").rstrip("/")
    return s or "your website"


# ---------- draft ----------

def build_footer(cfg, org, contact, *, follow: bool, lang: str) -> str:
    key = f"{'follow' if follow else 'first'}_{lang}"
    tpl = (cfg.get("footer") or {}).get(key) or (cfg.get("footer") or {}).get(f"{key[:-3]}_en", "")
    s = cfg.get("sender", {})
    out = tpl.format(name=s.get("name", ""), role=s.get("role", ""), organisation=s.get("organisation", ""),
                     email=contact.get("email", ""), source=short_source(contact.get("source", "")),
                     org=org.get("name", ""))
    if s.get("phone"):
        out = out.rstrip("\n") + f"\n{s['phone']}\n"
    return out


def split_subject(text: str):
    m = re.match(r"\s*(subject|betreff):\s*(.+?)\s*\n", text, re.I)
    return (m.group(2), text[m.end():].lstrip("\n")) if m else (None, text)


def unsubscribe_header(cfg) -> str:
    """List-Unsubscribe value: a mailto to the sending inbox, which sync reads as an opt-out."""
    addr = str(cfg.get("sender", {}).get("address", "")).strip()
    if not addr or addr.upper() == "TODO":
        sys.exit("tenant.yaml sender.address is not set; the List-Unsubscribe header needs it")
    return f"<mailto:{addr}?subject=unsubscribe>"


def compose(cfg, org, contact, subject, body, *, follow: bool, lang: str, in_reply_to: str | None = None):
    """The message every draft gets: first email, follow-up and chain alike."""
    msg = EmailMessage()
    msg["To"] = contact["email"]
    s = cfg.get("sender", {})
    if s.get("name") and s.get("address") and s["address"] != "TODO":
        msg["From"] = f"{s['name']} <{s['address']}>"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg["Subject"] = subject
    msg["List-Unsubscribe"] = unsubscribe_header(cfg)
    msg.set_content(body.rstrip() + "\n\n" + build_footer(cfg, org, contact, follow=follow, lang=lang))
    return msg


def draft(args):
    cfg = tenant.config()
    pipeline = tenant.load(tenant.PIPELINE, {})
    org, t = find_touch(pipeline, args.touch)
    contacts = tenant.load(tenant.CONTACTS, {}) or {}
    contact = contacts.get(t["contact"]) or {}
    if not contact.get("email") or not contact.get("source"):
        sys.exit(f"no address with a source for {t['contact']} in contacts.private.yaml")
    lang = org.get("lang", "en")
    follow = t.get("kind") == "follow_up"

    src = tenant.DIR / t["body"]
    errors, warns, clean = lint_email.lint(src.read_text(encoding="utf-8"), followup=follow, lang=lang)
    for w in warns:
        print("warn ", w)
    if errors:
        for e in errors:
            print("ERROR", e)
        sys.exit("lint failed: fix the draft file and run draft again")
    clean_path = src.with_name(src.stem + ".clean.txt")
    clean_path.write_text(clean, encoding="utf-8")

    subject, body = split_subject(clean)
    thread = first_thread_for(org, t["contact"]) if follow else None
    if follow and not thread:
        sys.exit("follow-up but the first email to this contact has no gmail_thread_id")

    gm = service()
    assert_sender(gm)
    last_id = None
    if thread:
        th = gm.users().threads().get(userId="me", id=thread, format="metadata",
                                      metadataHeaders=["Subject", "Message-ID"]).execute()
        original = header(th["messages"][0], "Subject")
        subject = original if original.lower().startswith(("re:", "aw:")) else f"Re: {original}"
        last_id = header(th["messages"][-1], "Message-ID") or None
    if not subject:
        sys.exit("first email needs a 'Subject:' line at the top of the draft file")
    msg = compose(cfg, org, contact, subject, body, follow=follow, lang=lang, in_reply_to=last_id)

    payload = {"message": {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}}
    if thread:
        payload["message"]["threadId"] = thread
    if t.get("draft_id") and t.get("status") in ("drafted", "needs_approval", "ready"):
        try:
            gm.users().drafts().delete(userId="me", id=t["draft_id"]).execute()
        except Exception:
            pass  # already sent or deleted by hand
    d = gm.users().drafts().create(userId="me", body=payload).execute()

    with locked("claude"):
        pipeline = tenant.load(tenant.PIPELINE, {})
        org, t = find_touch(pipeline, args.touch)
        t.update(draft_id=d["id"], gmail_thread_id=d["message"]["threadId"], status="drafted",
                 drafted=dt.date.today().isoformat(), approved=False)
        tenant.save(tenant.PIPELINE, pipeline)
    print(f"drafted {args.touch}: draft_id {d['id']}  thread {d['message']['threadId']}")


def send_draft(draft_id: str) -> dict:
    """Used only by tools/send.py after every check has passed."""
    gm = service()
    if not _SENDER_OK:
        assert_sender(gm)
    m = gm.users().drafts().send(userId="me", body={"id": draft_id}).execute()
    return {"message_id": m["id"], "thread_id": m["threadId"]}


# ---------- read ----------

def _text_of(payload) -> str:
    if payload.get("mimeType", "").startswith("text/plain") and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        txt = _text_of(part)
        if txt:
            return txt
    if payload.get("mimeType", "").startswith("text/html") and payload.get("body", {}).get("data"):
        html = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
        return re.sub(r"<[^>]+>", " ", html)
    return ""


def strip_quote(text: str) -> str:
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith(">")]
    text = "\n".join(lines)
    m = QUOTE_START.search(text)
    return (text[: m.start()] if m else text).strip()


def read(args):
    th = service().users().threads().get(userId="me", id=args.thread, format="full").execute()
    for m in th["messages"]:
        print(f"--- {header(m, 'From')} | {header(m, 'Date')}")
        print(strip_quote(_text_of(m["payload"]))[:3000] or m.get("snippet", ""))
    print("---")


# ---------- sync ----------

def classify(message, me: str) -> str | None:
    frm = header(message, "From").lower()
    if me in frm:
        return None
    if "mailer-daemon" in frm or "postmaster" in frm or header(message, "X-Failed-Recipients"):
        return BOUNCE
    snippet = strip_quote(" " + (message.get("snippet") or ""))
    if UNSUBSCRIBE_ONLY.match(header(message, "Subject")) or UNSUBSCRIBE_ONLY.match(snippet):
        return OPT_OUT
    auto = header(message, "Auto-Submitted").lower()
    if (auto and auto != "no") or header(message, "X-Autoreply") or header(message, "X-Autorespond") \
            or header(message, "Precedence").lower() in ("auto_reply", "bulk", "junk") \
            or AUTO_SUBJECT.search(header(message, "Subject")):
        return AUTO
    if OPT_OUT_SHORT.match(snippet) or OPT_OUT_PHRASE.search(snippet):
        return OPT_OUT
    return HUMAN


RANK = {HUMAN: 4, OPT_OUT: 3, BOUNCE: 2, AUTO: 1}
META = ["From", "Subject", "Auto-Submitted", "X-Autoreply", "X-Autorespond", "Precedence", "X-Failed-Recipients"]


def sender_address(message) -> str:
    frm = header(message, "From")
    m = re.search(r"<([^>]+)>", frm)
    return (m.group(1) if m else frm).strip().lower()


def match_unsubscribes(messages, pipeline, contacts, me, found):
    """Unsubscribe mails from a recipient's mail client arrive as new messages, outside our thread.
    Tie each to the sent touches of the contact with that address, or else of the organisation with
    that domain. Adds (org_id, touch_id, opt_out, thread_id) rows to `found`."""
    by_addr = {(c.get("email") or "").lower(): cid for cid, c in contacts.items()}
    for m in messages:
        if classify(m, me) != OPT_OUT:
            continue
        addr = sender_address(m)
        cid = by_addr.get(addr)
        dom = tenant.domain_of(addr)
        for org in pipeline.get("orgs", []):
            if cid is None and org.get("domain") != dom:
                continue
            for t in org.get("touches", []):
                if t.get("status") != "sent" or t["id"] in found:
                    continue
                if cid is not None and t.get("contact") != cid:
                    continue
                found[t["id"]] = (org["id"], t["id"], OPT_OUT, t.get("gmail_thread_id"))
    return found


def scan(days: int):
    """[(org_id, touch_id, kind, thread_id)] for every sent touch with something new in its thread."""
    gm = service().users()
    me = my_address(service())
    pipeline = tenant.load(tenant.PIPELINE, {})
    contacts = tenant.load(tenant.CONTACTS, {}) or {}
    found = {}
    for org in pipeline.get("orgs", []):
        for t in org.get("touches", []):
            if t.get("status") != "sent" or not t.get("gmail_thread_id"):
                continue
            th = gm.threads().get(userId="me", id=t["gmail_thread_id"], format="metadata",
                                  metadataHeaders=META).execute()
            kinds = [k for k in (classify(m, me) for m in th["messages"]) if k]
            if kinds:
                best = max(kinds, key=RANK.get)
                if best == AUTO and t.get("auto_reply"):
                    continue  # already recorded; an out-of-office does not stop the follow-up
                found[t["id"]] = (org["id"], t["id"], best, t["gmail_thread_id"])
    # bounces that Gmail did not thread with the original
    by_addr = {c.get("email", "").lower(): cid for cid, c in contacts.items()}
    res = gm.messages().list(userId="me", q=f"from:(mailer-daemon OR postmaster) newer_than:{days}d").execute()
    for ref in res.get("messages", []):
        m = gm.messages().get(userId="me", id=ref["id"], format="metadata", metadataHeaders=META).execute()
        failed = (header(m, "X-Failed-Recipients") + " " + m.get("snippet", "")).lower()
        for addr, cid in by_addr.items():
            if addr and addr in failed:
                for org in pipeline.get("orgs", []):
                    for t in org.get("touches", []):
                        if t.get("contact") == cid and t.get("status") == "sent" and t["id"] not in found:
                            found[t["id"]] = (org["id"], t["id"], BOUNCE, t.get("gmail_thread_id"))
    # unsubscribe mails from the List-Unsubscribe header (not threaded with the original)
    res = gm.messages().list(userId="me", q=f"subject:unsubscribe newer_than:{days}d -from:me").execute()
    unsub = [gm.messages().get(userId="me", id=ref["id"], format="metadata", metadataHeaders=META).execute()
             for ref in res.get("messages", [])]
    match_unsubscribes(unsub, pipeline, contacts, me, found)
    return list(found.values())


def suppress(kind: str, value: str, reason: str):
    data = tenant.load(tenant.SUPPRESSION, {}) or {}
    data.setdefault(kind, {})[value.lower()] = f"{reason} {dt.date.today().isoformat()}"
    tenant.save(tenant.SUPPRESSION, data)


def apply_results(rows):
    contacts = tenant.load(tenant.CONTACTS, {}) or {}
    with locked("sync"):
        pipeline = tenant.load(tenant.PIPELINE, {})
        orgs = {o["id"]: o for o in pipeline.get("orgs", [])}
        for org_id, touch_id, kind, _ in rows:
            org = orgs[org_id]
            t = next(x for x in org["touches"] if x["id"] == touch_id)
            addr = (contacts.get(t["contact"]) or {}).get("email", "")
            if kind == AUTO:
                t["auto_reply"] = dt.date.today().isoformat()
                continue
            if kind == BOUNCE:
                t["status"] = "bounced"
                if addr:
                    suppress("addresses", addr, "bounced")
            elif kind == OPT_OUT:
                t["status"] = "opted_out"
                org["status"] = "opted_out"
                suppress("domains", org["domain"], "opted out")
            else:
                t["status"] = "replied"
                org["status"] = "replied"
            t["reply_seen"] = dt.date.today().isoformat()
        tenant.save(tenant.PIPELINE, pipeline)
    for org_id, touch_id, kind, _ in rows:
        if kind in (OPT_OUT, HUMAN):
            try:
                registry.claim(orgs[org_id]["domain"], orgs[org_id]["name"],
                               "opted_out" if kind == OPT_OUT else "replied")
            except registry.RegistryError as exc:
                print(f"warn  registry not updated for {org_id}: {exc}")


def sync(args):
    rows = scan(args.days)
    if not rows:
        print("no new replies, bounces or auto-replies")
    for org_id, touch_id, kind, thread in rows:
        flag = "  <-- MANUEL" if kind == HUMAN else ""
        print(f"{kind:8} {org_id:28} {touch_id:30} thread {thread}{flag}")
    if args.apply and rows:
        apply_results(rows)
        print(f"applied {len(rows)}")


# ---------- report mail ----------

def mail_self(args):
    path = Path(args.body).resolve()
    if path not in {tenant.REPORT.resolve(), tenant.WEEKLY.resolve()}:
        sys.exit("mail-self only sends the daily report or the weekly review")
    gm = service()
    me = my_address(gm)
    msg = EmailMessage()
    msg["To"] = me
    msg["Subject"] = f"Outreach {path.stem.replace('-', ' ')} {dt.date.today().isoformat()}"
    msg.set_content(path.read_text(encoding="utf-8"))
    raw = {"message": {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}}
    gm.users().messages().send(userId="me", body=raw["message"]).execute()
    print("mailed to the sending inbox")


def auth_status(args):
    print("token_file:", "yes" if google_auth.TOKEN.exists() else "no")
    print("refresh_token:", "yes" if google_auth.token_info().get("refresh_token") else "no")
    if args.check:
        try:
            print("inbox:", assert_sender(service()), "(matches tenant.yaml)")
        except SystemExit as exc:
            print(exc)
            sys.exit(3)
        except Exception as exc:
            print(f"GMAIL_LOGIN_EXPIRED: {exc}")
            sys.exit(3)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    st = sub.add_parser("auth-status")
    st.add_argument("--check", action="store_true")
    d = sub.add_parser("draft")
    d.add_argument("--touch", required=True)
    r = sub.add_parser("read")
    r.add_argument("--thread", required=True)
    s = sub.add_parser("sync")
    s.add_argument("--days", type=int, default=14)
    s.add_argument("--apply", action="store_true")
    m = sub.add_parser("mail-self")
    m.add_argument("--body", required=True)
    args = ap.parse_args()
    if args.cmd == "auth":
        google_auth.load_credentials(reauth=True, allow_browser=True)
        print("ok: token saved")
    elif args.cmd == "auth-status":
        auth_status(args)
    else:
        {"draft": draft, "read": read, "sync": sync, "mail-self": mail_self}[args.cmd](args)


if __name__ == "__main__":
    main()
