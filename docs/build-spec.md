# Build spec: client outreach for 180DC Delft & Rotterdam

Agreed with Manuel on 2026-11-18/19 in a grilling session. Built from the job-search outreach kit
(`Desktop/outreach-kit`, map in the vault at `projects/outreach-automation-map.md`), which stays as
it is. This file records what was decided and why, so nobody re-opens it by accident.

## Goal

**2-3 paid, interesting AI-automation projects signed by mid-January 2027**, from about **1,000
emails in total** (first emails + follow-ups) sent between the first send and 22 December 2026.

## Decisions

| # | Decision | Why |
|---|---|---|
| 1 | First user is 180DC Delft & Rotterdam finding its own clients. Selling the kit to other clients (one.immo and others) comes later. | Real results first; they become the case study for selling it. |
| 2 | Copy the job kit; everything branch-specific in `tenants/180dc-delft-rotterdam/`. A second client is a folder copy. | Reuse what works, and make the second tenant cheap. |
| 3 | The product: audit where the team's hours go, build one main automation, scope further work, hand over. No maintenance after handover. | A student team cannot run production systems after it leaves. |
| 4 | Entry: a free 30-minute call. Price set after it, depending on funding and the task. | The easiest yes for a nonprofit, and where funding is learned. |
| 5 | Targets: nonprofits, social enterprises, a few Rotterdam woningcorporaties. One visible repetitive workflow and an identifiable funding source are required. 20-100 staff is a guide, not a rule. Delft and Rotterdam first, open to the EU. | What matters is a paid, interesting project. |
| 6 | Language: English, German (Sie) for DE/AT/CH. No Dutch. | Manuel does not speak Dutch; calls must match the email. |
| 7 | Split test, alternating by draft order: A = track record leads (anonymised), B = value-first leads (two ideas from their site). | Manuel wants both; read as a direction only at ~30-50 per arm. |
| 8 | Follow-up after 7 days is the question: "which of these takes your team the most hours?". Then one more person at the organisation, then close. | The question failed as a cold opener in the job kit (0 of 9); it fits a follow-up. |
| 9 | Tier 1 (best ~150): full card, two ideas, Manuel approves each first email. Tier 2 (the rest): one verified fact, sector workflow as a guess, lint + checker agent, sent automatically. The first 30 first emails of any tier are approved too. | One person cannot approve 1,000 emails. |
| 10 | One new 180dc.org inbox. Ramp 20/35/50/65 a day by week from the first send, random 3-8 minute gaps, Mon-Fri 08:30-16:30, nothing after 22 Dec. | 180dc.org's reputation is shared by every branch worldwide; a new inbox has none. |
| 11 | Shared registry on a new monday.com board, keyed on domain; another owner's contact blocks for 90 days. | Several members do outreach; nobody may write to the same organisation twice. |
| 12 | Global 180DC has been told. The legal team owns the legal side. The kit still enforces opt-out, address source and suppression in code. | Policy only works if the sender cannot skip it. |
| 13 | Members who win projects build them; the branch centralises what works later. | |
| 14 | Following up on signals (funding rounds, postings) comes later. Reply handling is not "signals": it is in from day one. | A follow-up to someone who already answered is the worst possible email. |

## What was fixed from the job kit

1. The run prompt was cut off by the double quotes (Windows PowerShell 5.1 does not escape them for native programs). The prompt now has none, and the script refuses to run if one comes back.
2. Replies could not be read unattended (no read command existed). `gmail_draft.py read` exists and is covered by the allow-list.
3. Any mail from the firm's domain counted as a reply. Sync now reads each sent thread and tells human, opt-out, bounce and auto-reply apart.
4. Sending and recording were two steps (the model had to update the pipeline). `send.py run` records the send in the pipeline, the send log and the registry in the same step.
5. Sends went out in bursts of seconds. Now there is a random 3-8 minute gap.
6. Silent failures (dead login, run at the wrong hour). A preflight checks the login before anything runs; failures write an alert to the Desktop and pop up a message.
7. No model can send: the session ends at `send.py ready`; the sender is a plain script.
8. The footer, address source and opt-out are added by code, not by the model.

## Open items, in order

1. **Target list builder.** `targets.yaml` is empty. ~750 candidate organisations are needed for ~600
   first emails. Free sources to check: CBF register (recognised charities, with income), ANBI
   register, Social Enterprise NL members, Aedes members (woningcorporaties), plus the funding-radar
   digests for impact startups. Not yet checked which of these expose staff counts and websites.
2. **Setup** (docs/setup.md): inbox, Internal OAuth app, booking link, monday board and token.
3. **Ledger confirmations:** TR-EVIDENCE wording; BR-PAST-WORK needs the branch's OK; legal team reads the footer.
4. **The PC must stay awake 07:00-16:30 on weekdays**, or the cloud VM plan has to happen.
5. **Not tested against live services:** Gmail sending/sync on the new inbox, and the monday API. The
   self-test (`python tools/selftest.py`) covers the rules offline.
6. Later: signals (funding-radar, postings) as triggers; a second tenant (one.immo); a real database
   when more than one person writes to the pipeline.
