# 09 Follow-ups without a model (DONE 2026-11-21)

**Was.** A session had to write every follow-up, so a missed or failed run meant no follow-ups, and the
job kit's audit found 23 finance first emails that never got their follow-up.

**Now.** Every first email stores the two workflows it names (`pipeline.py add-touch --workflows`).
`tools/followups.py prepare` finds every first email that is 7+ days old with no reply and no
follow-up, fills `templates/follow.<lang>.txt` ("which of these takes your team the most hours, X or
Y?"), lints it, makes the Gmail draft in the same thread and marks it ready. Follow-ups need no
approval, and `send.py run` sends them before new first emails. A reply, an opt-out or a bounce found
by `gmail_draft.py sync` stops the follow-up, because the organisation's status changes first.

After the follow-up: 4 days later `outreach_due.py` proposes one second person at the organisation
(written by a session, since it needs a new person), then closes the organisation.

**Tested.** `tools/selftest.py` covers it end to end (due after 7 days, text names both workflows, same
thread, no approval, sent before new first emails, never twice to one address).
