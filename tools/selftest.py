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

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
