# Client outreach kit

Tailored cold outreach with follow-ups, tracking and guarded sending, built to win paid
AI-automation projects. First tenant: 180DC Delft & Rotterdam. Built from the job-search outreach
kit on 2026-11-19.

- The plan and why: `docs/build-spec.md`
- One-time setup: `docs/setup.md`
- Every day and every Sunday: `docs/runbook.md`
- Rules for any Claude session here: `CLAUDE.md`

## How a day runs

```
07:00  daily_run.ps1   preflight: Gmail login alive?           (no -> Desktop alert, stop)
       Claude session  sync replies -> follow-ups -> research new orgs (Haiku) -> draft
                       -> lint -> checker agent (Haiku) -> Gmail draft -> send.py ready
08:30  send.py run     plain script: re-checks every rule, sends with 3-8 min gaps until the
-16:30                 daily cap, records each send, updates the shared registry
       report          mailed to the 180DC inbox: replies for Manuel, approvals waiting
```

## Tools (all zero LLM tokens)

| Script | Job |
|---|---|
| `firm_contacts.py <domain> --people` | Published addresses and a team digest from the organisation's own pages (Dutch page names added) |
| `pipeline.py` | Add organisations, contacts, touches; assigns the A/B arm; records outcomes |
| `lint_email.py` | Words, one ask, banned phrases, `[claim:]` against the ledger, `[src:]` required, no links but the booking page |
| `gmail_draft.py` | Draft from a touch id with the footer added in code; read threads; sync and classify replies |
| `send.py` | ready / approvals / approve / run: the only sender, with ramp, window, gaps, caps, suppression, registry, auto-pause |
| `registry.py` | Shared "who is talking to whom", monday.com or local |
| `followups.py` | Writes, checks, drafts and queues every due follow-up from the two stored workflows, no model |
| `outreach_due.py` | What is due today and how many new first emails fit |
| `stats.py` | Replies and positives by arm and tier |
| `selftest.py` | Offline checks of the rules against a throwaway tenant |
