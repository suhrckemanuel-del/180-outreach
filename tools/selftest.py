"""Offline self-test: every sending rule against a throwaway tenant, Gmail stubbed. Zero LLM tokens.

Copies the real tenant's config to a temp folder as tenant 'selftest', fills the TODOs, and runs the
tools in-process. Nothing touches Gmail, monday or the real pipeline.

Usage:  python tools/selftest.py
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REAL = HERE.parent / "tenants" / "180dc-delft-rotterdam"
TMP = Path(tempfile.mkdtemp(prefix="outreach-selftest-"))
T = TMP / "tenants" / "selftest"
shutil.copytree(REAL, T, ignore=shutil.ignore_patterns("private", "state", "drafts", "cards"))
(T / "pipeline.yaml").write_text("orgs: []\n", encoding="utf-8")  # start empty: never test on the real pipeline
os.environ["OUTREACH_ROOT"] = str(TMP)
os.environ["OUTREACH_TENANT"] = "selftest"
sys.path.insert(0, str(HERE))

import yaml  # noqa: E402

cfg = yaml.safe_load((T / "tenant.yaml").read_text(encoding="utf-8"))
cfg["sender"]["address"] = "outreach@180dc.example"
cfg["booking_link"] = "https://calendar.app.google/selftest"
cfg["registry"]["backend"] = "local"
(T / "tenant.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
lim = yaml.safe_load((T / "limits.yaml").read_text(encoding="utf-8"))
lim.update(send_window=["00:00", "23:59"], send_weekdays=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
           last_send_date="2999-12-31", gap_seconds=[0, 0])
(T / "limits.yaml").write_text(yaml.safe_dump(lim, sort_keys=False), encoding="utf-8")

import gmail_draft  # noqa: E402
import lint_email  # noqa: E402
import pipeline as pl  # noqa: E402
import registry  # noqa: E402
import send  # noqa: E402
import tenant  # noqa: E402

REAL_DRAFT = gmail_draft.draft  # the follow-up test below swaps it for a stub
pl._resolve_mx = lambda domain: [f"mx.{domain}"]  # no real DNS in the self-test; MX checks stub it below
PASSED, FAILED = [], []


def check(name, cond):
    (PASSED if cond else FAILED).append(name)
    print(("ok    " if cond else "FAIL  ") + name)


GOOD_B = """Subject: Two ideas for your volunteer intake

Dear Ms de Vries,

Your site says new volunteers sign up through a form and are matched by hand each week. [src:https://stichtingx.nl/vrijwilligers] Two things we could automate there:

1. match new sign-ups to open shifts and draft the confirmation email
2. fill the monthly funder report from the intake records

I lead AI at 180 Degrees Consulting Delft & Rotterdam [claim:ROLE] and recently built and demoed an automation that reads incoming reports and drafts the next step. [claim:TR-PROPERTY] We run short projects for nonprofits: audit, one automation built with you, handover.

Would a free 30-minute call be useful to go through these? https://calendar.app.google/selftest

Best regards,
Manuel
"""

FOLLOW = """Ms de Vries, one short question on my note last week: which of these takes your team the most hours, matching volunteers to shifts or the monthly funder report? A one-line answer helps us either way.

Manuel
"""

# ---------- lint ----------
e, w, clean = lint_email.lint(GOOD_B, followup=False, lang="en")
check("lint: a good arm-B email passes", not e)
check("lint: --clean strips both tag kinds", "[claim:" not in clean and "[src:" not in clean)
bad = GOOD_B.replace("Two things", "Two things — both quick?")
check("lint: em dash and a second question fail", len(lint_email.lint(bad, followup=False, lang="en")[0]) >= 2)
check("lint: unknown claim ID fails", lint_email.lint(GOOD_B.replace("TR-PROPERTY", "TR-NOPE"), followup=False, lang="en")[0])
check("lint: unusable claim fails", lint_email.lint(GOOD_B.replace("TR-PROPERTY", "BR-PAST-WORK"), followup=False, lang="en")[0])
check("lint: first email without [src:] fails",
      lint_email.lint(GOOD_B.replace(" [src:https://stichtingx.nl/vrijwilligers]", ""), followup=False, lang="en")[0])
check("lint: a second link fails", lint_email.lint(GOOD_B.replace("handover.", "handover, see https://x.org."), followup=False, lang="en")[0])
check("lint: a time-saving number fails", lint_email.lint(GOOD_B.replace("handover.", "handover, saving 20%."), followup=False, lang="en")[0])
check("lint: an unfilled template slot fails", lint_email.lint(GOOD_B.replace("Ms de Vries", "{first name}"), followup=False, lang="en")[0])
check("lint: footer in the body fails", lint_email.lint(GOOD_B + '\n--\nNot relevant? Reply "no"', followup=False, lang="en")[0])
check("lint: the follow-up passes", not lint_email.lint(FOLLOW, followup=True, lang="en")[0])
check("lint: English email with --lang de fails", lint_email.lint(GOOD_B, followup=False, lang="de")[0])

# ---------- pipeline + arms ----------
def ns(**kw):
    return Namespace(**kw)

for i, (oid, dom, tier) in enumerate([("org-a", "orga.nl", 1), ("org-b", "orgb.nl", 2), ("org-c", "orgc.de", 2)]):
    pl.add_org(ns(id=oid, name=oid.upper(), domain=f"https://www.{dom}/", city="Rotterdam",
                  country="DE" if dom.endswith(".de") else "NL", segment="nonprofit", tier=tier, card=None))
    pl.add_contact(ns(org=oid, id=f"{oid}-p1", name="P One", title="Directeur", email=f"p1@{dom}",
                      source=f"https://{dom}/team", allow_other_domain=False))
    pl.add_touch(ns(org=oid, contact=f"{oid}-p1", kind="first",
                    workflows=["matching volunteers to shifts", "the monthly funder report"]))
p = tenant.load(tenant.PIPELINE)
arms = [o["touches"][0]["arm"] for o in p["orgs"]]
check("pipeline: arms alternate A, B, A", arms == ["A", "B", "A"])
check("pipeline: German org gets lang de", p["orgs"][2]["lang"] == "de")
check("pipeline: domain normalised", p["orgs"][0]["domain"] == "orga.nl")
try:
    pl.add_contact(ns(org="org-a", id="x", name="X", title="t", email="x@other.org",
                      source="https://orga.nl/team", allow_other_domain=False))
    check("pipeline: address off the org's domain is refused", False)
except SystemExit:
    check("pipeline: address off the org's domain is refused", True)

# lawful basis and MX check on add-contact
stored = tenant.load(tenant.CONTACTS)["org-a-p1"]
check("basis: the default basis is stored next to the address, naming its source page",
      stored["basis"].startswith("legitimate interest") and "https://orga.nl/team" in stored["basis"])
pl.add_contact(ns(org="org-a", id="org-a-p2", name="P Two", title="Bestuurder", email="p2@orga.nl",
                  source="https://orga.nl/team", allow_other_domain=False, basis="consent: asked us to write"))
check("basis: --basis is stored as given", tenant.load(tenant.CONTACTS)["org-a-p2"]["basis"] == "consent: asked us to write")


def refused_with(stub, email):
    pl._resolve_mx = stub
    try:
        pl.add_contact(ns(org="org-a", id="org-a-mx", name="M", title="t", email=email,
                          source="https://orga.nl/team", allow_other_domain=True))
        return None
    except SystemExit as exc:
        return str(exc)
    finally:
        pl._resolve_mx = lambda domain: [f"mx.{domain}"]


def _dns_down(domain):
    raise pl.DnsUnreachable("LifetimeTimeout: no answer")


msg_none = refused_with(lambda d: [], "x@nomail.example")
check("mx: an address whose domain has no mail server is refused", msg_none is not None and "no mail server" in msg_none)
msg_down = refused_with(_dns_down, "x@orga.nl")
check("mx: DNS unreachable refuses with a clear message, never accepts",
      msg_down is not None and "could not reach DNS" in msg_down)
check("mx: a refused address is not stored", "org-a-mx" not in tenant.load(tenant.CONTACTS)
      and all(c["id"] != "org-a-mx" for c in tenant.load(tenant.PIPELINE)["orgs"][0]["contacts"]))
check("mx: a domain with a mail server is accepted", refused_with(lambda d: ["mx1." + d], "p3@orga.nl") is None)

# give every first touch a body and a fake Gmail draft
(T / "drafts").mkdir(exist_ok=True)
for o in p["orgs"]:
    t = o["touches"][0]
    body = GOOD_B if o["lang"] == "en" else GOOD_B  # German case is checked by lint above
    (T / t["body"]).write_text(body, encoding="utf-8")
    t.update(status="drafted", draft_id=f"d-{t['id']}", drafted=dt.date.today().isoformat())
p["orgs"][2]["lang"] = "en"  # keep the third org sendable for the loop test
tenant.save(tenant.PIPELINE, p)

# ---------- registry ----------
registry._local_put("orgb.nl", {"org": "ORG-B", "owner": "someone-else", "status": "contacted",
                                "blocked_until": (dt.date.today() + dt.timedelta(days=30)).isoformat()})
check("registry: another owner's recent contact blocks", registry.blocked_reason("orgb.nl") is not None)
check("registry: our own claim does not block", registry.blocked_reason("orga.nl") is None)
registry._local_put("orgb.nl", {"org": "ORG-B", "owner": "someone-else", "status": "contacted", "blocked_until": "2020-01-01"})
check("registry: an expired block frees the domain", registry.blocked_reason("orgb.nl") is None)

# ---------- ready / approval ----------
check("ready: tier 1 goes to needs_approval", send.cmd_ready(ns(touch="org-a-p1-1")) == 0
      and send.find(tenant.load(tenant.PIPELINE), "org-a-p1-1")[1]["status"] == "needs_approval")
send.cmd_ready(ns(touch="org-b-p1-1"))
check("ready: tier 2 inside the first 30 also needs approval",
      send.find(tenant.load(tenant.PIPELINE), "org-b-p1-1")[1]["status"] == "needs_approval")
send.cmd_approve(ns(touch=["org-a-p1-1", "org-b-p1-1"]))
check("approve: both become ready", all(send.find(tenant.load(tenant.PIPELINE), x)[1]["status"] == "ready"
                                        for x in ("org-a-p1-1", "org-b-p1-1")))

# suppression holds org-c
tenant.save(tenant.SUPPRESSION, {"domains": {"orgc.de": "opted out"}})
check("suppression: a suppressed domain is held", send.cmd_ready(ns(touch="org-c-p1-1")) == 2)

# ---------- the send loop with Gmail stubbed ----------
sent_ids = []
gmail_draft.send_draft = lambda draft_id: (sent_ids.append(draft_id) or {"message_id": "m-" + draft_id, "thread_id": "th-" + draft_id})
send.cmd_run(ns(dry_run=False, max=None))
p = tenant.load(tenant.PIPELINE)
check("run: sends exactly the two ready touches", sorted(sent_ids) == ["d-org-a-p1-1", "d-org-b-p1-1"])
check("run: the pipeline records sent + thread in the same step",
      all(send.find(p, x)[1]["status"] == "sent" and send.find(p, x)[1]["gmail_thread_id"] for x in ("org-a-p1-1", "org-b-p1-1")))
check("run: the send log has both rows with arm and tier", len(send.sent_rows()) == 2 and send.sent_rows()[0][4] in "AB")
check("run: the registry now holds our claim", (registry.lookup("orga.nl") or {}).get("status") == "contacted")
check("run: the suppressed org was not sent", "d-org-c-p1-1" not in sent_ids)

# ---------- follow-ups, end to end, no model ----------
try:
    pl.add_touch(ns(org="org-a", contact="org-a-p1", kind="first", workflows=["only one"]))
    check("pipeline: a first email without two workflows is refused", False)
except SystemExit:
    check("pipeline: a first email without two workflows is refused", True)

import followups  # noqa: E402
import outreach_due  # noqa: E402

check("follow-up: nothing due on the day of sending", not list(followups.due(tenant.load(tenant.PIPELINE), dt.date.today())))
p = tenant.load(tenant.PIPELINE)
eight_days_ago = (dt.datetime.now() - dt.timedelta(days=8)).isoformat(timespec="seconds")
for x in ("org-a-p1-1", "org-b-p1-1"):
    send.find(p, x)[1]["sent"] = eight_days_ago
tenant.save(tenant.PIPELINE, p)
TAB, NL = chr(9), chr(10)
tenant.SENT_LOG.write_text("".join(
    TAB.join([eight_days_ago, o, t, "first", "A", "1", "d"]) + NL
    for o, t in (("org-a", "org-a-p1-1"), ("org-b", "org-b-p1-1"))), encoding="utf-8")
due_lines = outreach_due.plan(tenant.load(tenant.PIPELINE), dt.date.today())["FOLLOW-UP"]
check("follow-up: outreach_due lists both after 7 days", len(due_lines) == 2)

def fake_draft(args):
    with tenant_lock("claude"):
        pp = tenant.load(tenant.PIPELINE)
        org, t = send.find(pp, args.touch)
        first = next(x for x in org["touches"] if x.get("contact") == t["contact"] and x.get("kind") == "first")
        t.update(status="drafted", draft_id="d-" + args.touch, gmail_thread_id=first["gmail_thread_id"],
                 drafted=dt.date.today().isoformat())
        tenant.save(tenant.PIPELINE, pp)

from writer_lock import locked as tenant_lock  # noqa: E402
gmail_draft.draft = fake_draft
check("follow-up: prepare writes and queues both", followups.prepare(ns(dry_run=False)) == 0)
p = tenant.load(tenant.PIPELINE)
fu_a = send.find(p, "org-a-p1-fu")[1]
body_a = (T / fu_a["body"]).read_text(encoding="utf-8")
check("follow-up: ready without approval", fu_a["status"] == "ready")
check("follow-up: the question names both stored workflows",
      "matching volunteers to shifts or the monthly funder report?" in body_a and body_a.startswith("P,"))
check("follow-up: same thread as the first email", fu_a["gmail_thread_id"] == send.find(p, "org-a-p1-1")[1]["gmail_thread_id"])
check("follow-up: a second prepare adds nothing", not list(followups.due(p, dt.date.today())))

# a new first email is queued too; the loop must send the follow-ups before it
pl.add_org(ns(id="org-d", name="ORG-D", domain="orgd.nl", city="Delft", country="NL", segment="nonprofit", tier=2, card=None))
pl.add_contact(ns(org="org-d", id="org-d-p1", name="Q", title="Directeur", email="q@orgd.nl", source="https://orgd.nl/team", allow_other_domain=False))
pl.add_touch(ns(org="org-d", contact="org-d-p1", kind="first", workflows=["intake", "reports"]))
p = tenant.load(tenant.PIPELINE)
t_d = send.find(p, "org-d-p1-1")[1]
(T / t_d["body"]).write_text(GOOD_B, encoding="utf-8")
t_d.update(status="ready", draft_id="d-org-d-p1-1", approved=True, drafted=dt.date.today().isoformat())
tenant.save(tenant.PIPELINE, p)
sent_ids.clear()
send.cmd_run(ns(dry_run=False, max=2))
check("run: follow-ups go before new first emails", sorted(sent_ids) == ["d-org-a-p1-fu", "d-org-b-p1-fu"])
org, t = send.find(tenant.load(tenant.PIPELINE), "org-a-p1-fu")
check("follow-up: a second follow-up to the same address is refused",
      any("already had its follow-up" in r for r in send.content_and_contact_reasons(org, {**t, "id": "x", "status": "drafted", "draft_id": "y"}, dt.date.today())))

# daily cap from the ramp
first_send = dt.date.today() - dt.timedelta(days=8)
check("ramp: the first send's day is week 1", send.daily_cap(first_send) == (lim["ramp_per_week"][0], 1))
check("ramp: 8 days after the first send is week 2", send.daily_cap(dt.date.today()) == (lim["ramp_per_week"][1], 2))
check("ramp: four weeks later the last value holds",
      send.daily_cap(dt.date.today() + dt.timedelta(days=40))[0] == lim["ramp_per_week"][-1])

# STOP
tenant.STOP.write_text("test", encoding="utf-8")
check("STOP: holds everything", any("STOP" in r for r in send.clock_reasons(None, [], dt.datetime.now())))
tenant.STOP.unlink()

# auto-pause on bounces
p = tenant.load(tenant.PIPELINE)
for i in range(45):
    p["orgs"][1]["touches"].append({"id": f"fake-{i}", "contact": "org-b-p1", "kind": "first",
                                    "status": "bounced" if i < 3 else "sent", "sent": f"2026-11-0{1 + i % 9}T09:00:00"})
check("auto-pause: >3% bounces over 40+ sends pauses", send.auto_pause_reason(p) is not None)

# ---------- reply classification ----------
def msg(frm, subject="Re: x", snippet="", **headers):
    hs = [{"name": "From", "value": frm}, {"name": "Subject", "value": subject}]
    hs += [{"name": k.replace("_", "-"), "value": v} for k, v in headers.items()]
    return {"payload": {"headers": hs}, "snippet": snippet}

me = "outreach@180dc.example"
check("classify: our own message is skipped", gmail_draft.classify(msg("Manuel <outreach@180dc.example>"), me) is None)
check("classify: mailer-daemon is a bounce", gmail_draft.classify(msg("Mail Delivery Subsystem <mailer-daemon@googlemail.com>"), me) == "bounce")
check("classify: Auto-Submitted is auto", gmail_draft.classify(msg("a@orga.nl", Auto_Submitted="auto-replied"), me) == "auto")
check("classify: 'Afwezig' subject is auto", gmail_draft.classify(msg("a@orga.nl", subject="Afwezig: tot 1 december"), me) == "auto")
check("classify: a bare 'No thanks' is an opt-out", gmail_draft.classify(msg("a@orga.nl", snippet="No thanks. On Tue, 24 Nov 2026 Manuel wrote: Dear"), me) == "opt_out")
check("classify: 'geen interesse' is an opt-out", gmail_draft.classify(msg("a@orga.nl", snippet="Wij hebben geen interesse, groet Jan"), me) == "opt_out")
check("classify: a real answer is human", gmail_draft.classify(msg("a@orga.nl", snippet="Interesting, the funder report is our biggest pain. Can you do Thursday?"), me) == "human")
check("classify: 'no' inside a real answer stays human",
      gmail_draft.classify(msg("a@orga.nl", snippet="No problem, we would like to talk next week."), me) == "human")

# ---------- footer ----------
c = {"email": "p1@orga.nl", "source": "https://orga.nl/team"}
foot = gmail_draft.build_footer(tenant.config(), {"name": "ORG-A"}, c, follow=False, lang="en")
check("footer: names the address source and the opt-out", "orga.nl/team" in foot and 'Reply "no"' in foot and "ORG-A" in foot)
foot_de = gmail_draft.build_footer(tenant.config(), {"name": "ORG-C"}, c, follow=False, lang="de")
check("footer: German footer for lang de", "Kein Interesse" in foot_de)

# ---------- the Gmail login must be the tenant's inbox ----------
class FakeGmail:
    def __init__(self, addr):
        self.addr = addr

    def users(self):
        return self

    def getProfile(self, userId):
        return self

    def execute(self):
        return {"emailAddress": self.addr}

check("sender: the matching inbox is accepted", gmail_draft.assert_sender(FakeGmail("Outreach@180dc.example")) == "outreach@180dc.example")
try:
    gmail_draft.assert_sender(FakeGmail("someone.personal@gmail.com"))
    check("sender: a personal Gmail login is refused", False)
except SystemExit as exc:
    check("sender: a personal Gmail login is refused", "WRONG_ACCOUNT" in str(exc))

# ---------- List-Unsubscribe header and "unsubscribe" as an opt-out ----------
import base64 as _b64  # noqa: E402
import email as _email  # noqa: E402


class _Exec:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class FakeDraftGmail:
    """Enough of the Gmail API for gmail_draft.draft(): profile, thread metadata, draft create/delete."""
    def __init__(self):
        self.created = []

    def users(self):
        return self

    def getProfile(self, userId):
        return _Exec({"emailAddress": "outreach@180dc.example"})

    def drafts(self):
        return self

    def threads(self):
        return self

    def create(self, userId, body):
        self.created.append(body)
        return _Exec({"id": f"dr-{len(self.created)}", "message": {"threadId": body["message"].get("threadId", f"th-{len(self.created)}")}})

    def delete(self, userId, id):
        return _Exec({})

    def get(self, userId, id, format=None, metadataHeaders=None):
        return _Exec({"messages": [{"payload": {"headers": [{"name": "Subject", "value": "Two ideas"},
                                                            {"name": "Message-ID", "value": "<m1@180dc.example>"}]}}]})


fake_gm = FakeDraftGmail()
gmail_draft.service = lambda **kw: fake_gm
pl.add_org(ns(id="org-e", name="ORG-E", domain="orge.nl", city="Delft", country="NL", segment="nonprofit", tier=2, card=None))
for cid in ("org-e-p1", "org-e-p2"):
    pl.add_contact(ns(org="org-e", id=cid, name="R", title="Directeur", email=f"{cid}@orge.nl",
                      source="https://orge.nl/team", allow_other_domain=False))
pl.add_touch(ns(org="org-e", contact="org-e-p1", kind="first", workflows=["intake", "reports"]))
pl.add_touch(ns(org="org-e", contact="org-e-p2", kind="chain", workflows=["intake", "reports"]))
p = tenant.load(tenant.PIPELINE)
for tid in ("org-e-p1-1", "org-e-p2-1"):
    (T / send.find(p, tid)[1]["body"]).write_text(GOOD_B, encoding="utf-8")
REAL_DRAFT(ns(touch="org-e-p1-1"))
p = tenant.load(tenant.PIPELINE)
send.find(p, "org-e-p1-1")[1]["status"] = "sent"
tenant.save(tenant.PIPELINE, p)
pl.add_touch(ns(org="org-e", contact="org-e-p1", kind="follow_up", workflows=None))
(T / "drafts" / "org-e-p1-fu.txt").write_text(FOLLOW, encoding="utf-8")
REAL_DRAFT(ns(touch="org-e-p1-fu"))
REAL_DRAFT(ns(touch="org-e-p2-1"))
want = "<mailto:outreach@180dc.example?subject=unsubscribe>"
heads = [_email.message_from_bytes(_b64.urlsafe_b64decode(b["message"]["raw"]))["List-Unsubscribe"] for b in fake_gm.created]
check("unsubscribe: first email, follow-up and chain all carry List-Unsubscribe to the sender",
      len(heads) == 3 and all(h == want for h in heads))
check("unsubscribe: the follow-up is still threaded", fake_gm.created[1]["message"].get("threadId") == "th-1")

check("classify: subject 'unsubscribe' with an empty body is an opt-out",
      gmail_draft.classify(msg("a@orga.nl", subject="unsubscribe"), me) == "opt_out")
check("classify: a reply whose body is just 'Unsubscribe' is an opt-out",
      gmail_draft.classify(msg("a@orga.nl", subject="Re: Two ideas", snippet="Unsubscribe."), me) == "opt_out")
check("classify: an unsubscribe mail flagged auto-generated is still an opt-out",
      gmail_draft.classify(msg("a@orga.nl", subject="unsubscribe", Auto_Submitted="auto-generated"), me) == "opt_out")
p = tenant.load(tenant.PIPELINE)
contacts = tenant.load(tenant.CONTACTS)
rows = gmail_draft.match_unsubscribes([msg("P One <p1@orga.nl>", subject="unsubscribe")], p, contacts, me, {})
check("sync: an unthreaded unsubscribe mail opts out that contact's sent touches",
      sorted(rows) == ["org-a-p1-1", "org-a-p1-fu"] and all(r[2] == "opt_out" for r in rows.values()))
rows = gmail_draft.match_unsubscribes([msg("office@orgb.nl", subject="unsubscribe")], p, contacts, me, {})
check("sync: an unsubscribe from another address at the domain opts out the organisation",
      sorted(rows) == ["org-b-p1-1", "org-b-p1-fu"])

# a touch whose contact has no lawful basis is held
p = tenant.load(tenant.PIPELINE)
org_e, t_e = send.find(p, "org-e-p2-1")
check("basis: a contact with a basis is not held for it",
      not any("lawful basis" in r for r in send.content_and_contact_reasons(org_e, t_e, dt.date.today())))
contacts = tenant.load(tenant.CONTACTS)
contacts["org-e-p2"].pop("basis")
tenant.save(tenant.CONTACTS, contacts)
check("basis: send.py holds a touch whose contact has no basis",
      send.cmd_ready(ns(touch="org-e-p2-1")) == 2
      and any("lawful basis" in r for r in send.content_and_contact_reasons(org_e, t_e, dt.date.today())))

# ---------- approval page ----------
(T / "cards").mkdir(exist_ok=True)
(T / "cards" / "org-f.md").write_text(
    "ORG: x\nWORKFLOW: volunteers <b>sign up</b> by form (https://orgf.nl/vrijwilligers)\n"
    "FUNDING: javascript:alert(1) and gemeente subsidy https://orgf.nl/over?a=1&b=2\n", encoding="utf-8")
pl.add_org(ns(id="org-f", name="<script>alert(1)</script> & Co", domain="orgf.nl", city="Delft", country="NL",
              segment="nonprofit", tier=2, card="cards/org-f.md"))
pl.add_contact(ns(org="org-f", id="org-f-p1", name="S", title="Directeur", email="info@orgf.nl",
                  source="https://orgf.nl/contact", allow_other_domain=False))
pl.add_touch(ns(org="org-f", contact="org-f-p1", kind="first", workflows=["intake", "reports"]))
p = tenant.load(tenant.PIPELINE)
t_f = send.find(p, "org-f-p1-1")[1]
(T / t_f["body"]).write_text(GOOD_B, encoding="utf-8")
t_f.update(status="drafted", draft_id="d-org-f", drafted=dt.date.today().isoformat())
tenant.save(tenant.PIPELINE, p)
send.cmd_ready(ns(touch="org-f-p1-1"))
send.cmd_approvals(ns(html=True))
page = (T / "state" / "approvals.html").read_text(encoding="utf-8") if (T / "state" / "approvals.html").exists() else ""
check("approvals: --html writes state/approvals.html with the touch id to approve",
      "org-f-p1-1" in page and "send.py approve --touch org-f-p1-1" in page)
check("approvals: every text is escaped", "<script>alert" not in page and "&lt;script&gt;alert(1)&lt;/script&gt; &amp; Co" in page
      and "<b>sign up" not in page)
check("approvals: card facts keep their source links, and only http(s) becomes a link",
      'href="https://orgf.nl/vrijwilligers"' in page and 'href="https://orgf.nl/over?a=1&amp;b=2"' in page
      and 'href="javascript' not in page)
check("approvals: the clean text is shown, tags stripped, with the footer",
      "Two ideas for your volunteer intake" in page and "[claim:" not in page and "[src:" not in page
      and "We found info@orgf.nl on orgf.nl/contact" in page)
check("approvals: tier and arm are shown", "tier 2 · arm" in page)

# ---------- enrich.py: code-only site facts and the score gate (HTTP stubbed, no network) ----------
import enrich  # noqa: E402

HOME = ("<html><body><nav><a href='/aanmelden'>Aanmelden</a> <a href='/contact'>Contact</a> "
        "<a href='/vacatures'>Vacatures</a></nav><h1>Stichting Voorbeeld</h1>"
        "<p>Wij werken met 25 medewerkers. De werkdruk is hoog en alles gaat handmatig in Excel. Mogelijk gemaakt door Oranje Fonds.</p>"
        "<p>Jan de Vries - jan [at] voorbeeld.nl</p><p>Aanmelden: <a href='mailto:aanmelden@voorbeeld.nl'>mail</a></p>"
        "<p>Extern: spam@elders.com</p></body></html>")
FORM = ("<html><body><form action='/x'><label>Naam</label><input name=n><label>Leeftijd kind</label><input name=a>"
        "<label>School</label><input name=s><label>Hulpvraag</label><textarea name=h></textarea></form></body></html>")
PAGES = {
    "https://voorbeeld.nl/": HOME, "https://voorbeeld.nl/aanmelden": FORM,
    "https://voorbeeld.nl/contact": "<html><body><p>Bel ons.</p></body></html>",
    "https://voorbeeld.nl/vacatures": "<html><body><h2>Administratief medewerker</h2></body></html>",
}
CALLS = []


def stub(url):
    CALLS.append(url)
    if url.endswith("robots.txt"):
        return {"body": "User-agent: *\nDisallow: /vacatures\n", "final": url, "ctype": "text/plain"}
    if url in PAGES:
        return {"body": PAGES[url], "final": url, "ctype": "text/html"}
    return None


facts = enrich.enrich("voorbeeld.nl", fetcher=stub, mx_check=False)
addrs = {e["address"]: e for e in facts["emails"]}
check("enrich: a printed mailto address on the domain is found, with its page",
      "aanmelden@voorbeeld.nl" in addrs and addrs["aanmelden@voorbeeld.nl"]["url"].startswith("https://voorbeeld.nl/"))
check("enrich: '[at]' is decoded and the name printed beside the address is kept",
      "jan@voorbeeld.nl" in addrs and addrs["jan@voorbeeld.nl"]["name"] == "Jan de Vries")
check("enrich: an address on another domain is skipped", not any("elders" in a for a in addrs))
check("enrich: robots.txt is obeyed (a disallowed page is never fetched)",
      "https://voorbeeld.nl/vacatures" not in CALLS and facts["vacancies"] == [])
check("enrich: every extracted value carries a URL",
      all(x.get("url") for k in ("emails", "forms", "funders", "staff", "pain") for x in facts[k]) and facts["funders"] and facts["staff"])
check("enrich: the workflow form's field labels are read",
      any(f["kind"] == "form" and "Hulpvraag" in f["fields"] for f in facts["forms"]))
check("enrich: it suggests the printed workflow address over a general one",
      facts["role_match"]["address"] == "aanmelden@voorbeeld.nl")
check("enrich: no guessing, every address returned is printed in the fixture pages",
      all(a in " ".join(PAGES.values()).replace(" [at] ", "@") for a in addrs))
check("enrich: it stays inside the request budget", len(CALLS) <= enrich.FETCH_BUDGET)
sc = enrich.score(facts, {"name": "Stichting Voorbeeld", "segment": "social_enterprise"}, d1=False)
check("score: a social enterprise with a workflow form, funder and named person goes to the model",
      sc["go"] and sc["score"] >= 9)
no_addr = dict(facts, emails=[])
check("score: gate on no on-domain address (skip, whatever the points)",
      enrich.score(no_addr, {"segment": "social_enterprise"}, d1=False)["skip"] == "no on-domain address")
check("score: gate on a site that is down", enrich.score(dict(facts, alive=False), {}, d1=False)["skip"] == "site down")
check("score: gate on a suppressed domain",
      enrich.score(facts, {}, d1=False, suppressed={"voorbeeld.nl"})["skip"] == "suppressed")
check("score: cultural names only lose points when D1 is yes",
      enrich.score(facts, {"name": "Theater X"}, d1=True)["score"] == enrich.score(facts, {"name": "Theater X"}, d1=False)["score"] - 3)
check("enrich: a person without a printed address stays without one (no guessing path)",
      enrich.enrich("zonder.nl", fetcher=lambda u: {"body": "<html><body><p>Jan de Vries, directeur</p></body></html>", "final": u, "ctype": "text/html"}
                    if not u.endswith("robots.txt") else None, mx_check=False)["emails"] == [])

# reviewer findings: redirects, robots failures, uncached failures, odd mailto, sister TLDs
CALLS2 = []


def stub_redirect(url):
    CALLS2.append(url)
    if url.endswith("robots.txt"):
        return {"body": "", "final": url, "ctype": "text/plain", "status": 404}
    if url == "https://redir.nl/":
        return {"body": "<html><body><p>x@redir.nl</p></body></html>", "final": "https://elders.com/", "ctype": "text/html", "status": 200}
    return None


f2 = enrich.enrich("redir.nl", fetcher=stub_redirect, mx_check=False)
check("enrich: a redirect to another host is dropped, its content never used", not f2["alive"] and f2["emails"] == [])
CALLS3 = []


def stub_robots_down(url):
    CALLS3.append(url)
    return {"body": "", "final": url, "ctype": "", "status": 503} if url.endswith("robots.txt") else {"body": "<html>x</html>", "final": url, "ctype": "text/html", "status": 200}


f3 = enrich.enrich("robotsdown.nl", fetcher=stub_robots_down, mx_check=False)
check("enrich: an unreachable robots.txt (5xx) means nothing is fetched", CALLS3 == ["https://robotsdown.nl/robots.txt"] and not f3["alive"])
n_before = len(CALLS2)
enrich.enrich("redir.nl", fetcher=stub_redirect, mx_check=False)
check("enrich: a failed fetch is not cached (the next run asks again)", len(CALLS2) > n_before)
mail_html = "<a href='mailto:a@multi.nl,b@multi.nl'>x</a><a href='mailto:Jan%20%3Cjan@multi.nl%3E'>y</a>"
got = sorted(e["address"] for e in enrich.extract_emails(mail_html, "https://multi.nl/", "multi.nl"))
check("enrich: a multi-recipient or decorated mailto yields single clean addresses only", got == ["a@multi.nl", "jan@multi.nl"])
check("enrich: an address on a sister TLD of a suppressed domain is suppressed",
      enrich.score(dict(facts, domain="voorbeeld.com"), {}, d1=False, suppressed={"voorbeeld.nl"})["skip"] == "suppressed")
check("enrich: x.co.uk style names keep their stem", enrich.stem("shop.ziggo.co.uk") == "ziggo")

# ---------- T1: a partner's staff count is not the organisation's ----------
SAMEN = {
    "https://samen.nl/": "<html><body><h1>Stichting Samen</h1><p>Wij werken met 30 medewerkers.</p>"
                        "<p><a href='/over-ons/team'>Team</a> <a href='/over-ons/partners'>Partners</a></p></body></html>",
    "https://samen.nl/over-ons/team": "<html><body><h1>Team</h1><p>Wij zijn met 24 medewerkers.</p></body></html>",
    "https://samen.nl/over-ons/partners": "<html><body><h1>Onze partners</h1>"
                                          "<p>Bakkerij Jansen werkt met 500 medewerkers.</p></body></html>",
}


def stub_pages(pages):
    def f(url):
        if url.endswith("robots.txt"):
            return {"body": "", "final": url, "ctype": "text/plain", "status": 404}
        return {"body": pages[url], "final": url, "ctype": "text/html"} if url in pages else None
    return f


fs = enrich.enrich("samen.nl", fetcher=stub_pages(SAMEN), mx_check=False)
numbers = [s["n"] for s in fs["staff"]]
check("enrich T1: a partner's staff figure on a partners page is not counted as the organisation's",
      500 not in numbers and not any(s["url"].endswith("/partners") for s in fs["staff"]))
check("enrich T1: the organisation's own figures on its homepage and team page are kept",
      30 in numbers and 24 in numbers)
PARTNERS_ONLY = {
    "https://alleenpartners.nl/": "<html><body><h1>Onze partners</h1>"
                                 "<p>Bakkerij Jansen werkt met 500 medewerkers.</p></body></html>",
}
check("enrich T1: a staff figure on a partners page never counts, even on the homepage",
      enrich.enrich("alleenpartners.nl", fetcher=stub_pages(PARTNERS_ONLY), mx_check=False)["staff"] == [])

# ---------- T2: the funders page and the team page always make the 8 ----------
NAV = {
    "https://nav.nl/": "<html><body><h1>Stichting Navigatie</h1><p><a href='/contact'>Contact</a> "
                       "<a href='/team'>Team</a> <a href='/team/contact'>Team contact</a> "
                       "<a href='/over-ons/partners'>Partners</a> <a href='/vacatures'>Vacatures</a> "
                       "<a href='/anbi'>ANBI</a> <a href='/aanmelden'>Aanmelden</a> "
                       "<a href='/inschrijven'>Inschrijven</a> <a href='/intake'>Intake</a></p></body></html>",
    "https://nav.nl/team/contact": "<html><body><h1>Team</h1><p>Mail <a href='mailto:team@nav.nl'>team@nav.nl</a></p></body></html>",
    "https://nav.nl/over-ons/partners": "<html><body><h1>Partners</h1><p>Gesteund door Oranje Fonds.</p></body></html>",
}
for u in ("contact", "team", "vacatures", "anbi", "aanmelden", "inschrijven", "intake"):
    NAV[f"https://nav.nl/{u}"] = f"<html><body><p>{u}</p></body></html>"
fn = enrich.enrich("nav.nl", fetcher=stub_pages(NAV), mx_check=False)
check("enrich T2: the partners page is read even when eight other pages match",
      any(x.endswith("/partners") for x in fn["pages"]) and any(f["name"] == "Oranje Fonds" for f in fn["funders"]))
check("enrich T2: the team contact page (with the address) is read, not just the team page",
      any(x.endswith("/team/contact") for x in fn["pages"])
      and any(e["address"] == "team@nav.nl" for e in fn["emails"]))
check("enrich T2: guaranteed pages still fit the request budget", len(enrich.choose_pages(
    "https://nav.nl/", NAV["https://nav.nl/"], enrich.Site("nav.nl", fetcher=stub_pages(NAV)), [])) <= enrich.MAX_PAGES)

# ---------- T4: calls.py, the call track (never in the send path) ----------
import io  # noqa: E402
from contextlib import redirect_stdout  # noqa: E402

import calls  # noqa: E402

calls.CALLS = T / "state" / "calls.yaml"
(T / "dossiers").mkdir(exist_ok=True)
(T / "dossiers" / "orga.md").write_text(
    "# Org A\n\n## Opener\nHello, I am calling about your volunteer intake. Is now a good time?\n\n"
    "Phone: 010-1234567\n", encoding="utf-8")
calls.add(ns(org="org-a", due="2026-12-01", script="dossiers/orga.md", phone=None))
calls.add(ns(org="org-b", due="2026-11-25", script=None, phone=None))
try:
    calls.add(ns(org="org-a", due="2026-12-02", script=None, phone=None))
    check("calls: a second planned call for the same organisation is refused", False)
except SystemExit:
    check("calls: a second planned call for the same organisation is refused", True)


def calls_out(fn, *args, **kw):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(Namespace(*args, **kw)) if args else fn(Namespace(**kw))
    return buf.getvalue()


today_text = calls_out(calls.due, date=dt.date(2026, 11, 25))
check("calls: due today lists only the call that is due", "org-b" in today_text and "org-a" not in today_text)
all_text = calls_out(calls.due, date=dt.date(2026, 12, 1))
check("calls: due lists both when both are due, with the dossier's number and opener",
      "org-a" in all_text and "org-b" in all_text and "010-1234567" in all_text and "volunteer intake" in all_text)
check("calls: list shows the planned calls by due date",
      [x.split()[1] for x in calls_out(calls.list_calls, all=False).strip().splitlines()] == ["org-b", "org-a"])

calls.log(ns(org="org-b", outcome="call_booked", note="Tuesday 10:00"))
p = tenant.load(tenant.PIPELINE)
org_b = next(o for o in p["orgs"] if o["id"] == "org-b")
check("calls: call_booked is recorded and runs pipeline.py set --outcome call",
      org_b.get("outcome") == "call" and any(c["org"] == "org-b" and c["status"] == "done" for c in calls.load()))
calls.log(ns(org="org-a", outcome="callback", note=None))
try:
    calls.log(ns(org="org-a", outcome="no_answer", note=None))
    check("calls: logging an organisation with no planned call is refused", False)
except SystemExit:
    check("calls: logging an organisation with no planned call is refused", True)

calls.add(ns(org="org-e", due="2026-12-03", script=None, phone=None))
calls.log(ns(org="org-e", outcome="not_interested", note=None))
check("calls: not_interested suppresses the domain like an email opt-out",
      "orge.nl" in (tenant.load(tenant.SUPPRESSION).get("domains") or {}))
check("calls: calls never enter pipeline.yaml, and send.py never reads them",
      all("calls" not in o for o in tenant.load(tenant.PIPELINE)["orgs"])
      and "calls.yaml" not in (HERE / "send.py").read_text(encoding="utf-8")
      and "import calls" not in (HERE / "send.py").read_text(encoding="utf-8"))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
