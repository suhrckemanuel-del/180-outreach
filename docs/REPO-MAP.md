# Repo map

Every file in this repo, what it is for, and how the pieces connect. Updated 2026-11-23.
Start with `README.md` for the idea, `docs/handoff-2026-11-21.md` for where the work stands.

## How the pieces connect

```
public registers ──> tools/sources/*.py ──> targets.yaml          (list building, no model)
                                               │  mark.py --pick: next batch of 25
                                               v
                     registry.py check ──> researcher agent ──> cards/<org>.md
                                               │  fits only
                                               v
                     pipeline.py add-org / add-contact / add-touch ──> pipeline.yaml
                                               │  names arm, language, template
                                               v
      templates/ + card + ledger.yaml ──> draft ──> lint_email.py ──> checker agent
                                               v
                     gmail_draft.py draft ──> send.py ready ──> needs_approval
                                               │  Manuel: send.py approve
                                               v
      daily_run.ps1 (scheduler) ──> send.py run ──> sent, logged, registry claimed
                                               │  7 days later
                                               v
                     followups.py prepare ──> same thread, same checks
      gmail_draft.py sync: replies, opt-outs, bounces ──> pipeline + suppression list
```

No model can send: a session ends at `send.py ready`. Only `send.py run`, started by the scheduler
or by Manuel, sends.

## Top level

| Path | What it is |
|---|---|
| `README.md` | What the kit does and how to start. |
| `CLAUDE.md` | Rules every Claude session follows here: never send, never approve, addresses only from the organisation's own pages, claims only from the ledger, token rules, writing rules. |
| `requirements.txt` | Python dependencies (PyYAML, Google API client and auth). |
| `.gitignore` | Keeps `tenants/*/private/`, `tenants/*/state/`, `tenants/*/drafts/` and `data/` out of git. |
| `.claude/agents/researcher.md` | Haiku agent: researches 1-5 organisations, writes one card each with a FIT/REJECT verdict and tier. Loads only when the session is opened in this repo. |
| `.claude/agents/checker.md` | Haiku agent: second reader for a batch of drafts, PASS/FAIL per draft against the card and the ledger. |

## docs/

| Path | What it is |
|---|---|
| `docs/build-spec.md` | The plan agreed on 2026-11-18/19: goal, 14 decisions with reasons, what was fixed from the job-search kit, open items. Read before changing a rule. |
| `docs/TEAM-OVERVIEW.md` | Short explanation of the kit for 180DC team members. |
| `docs/runbook.md` | The daily procedure, step by step (sync, follow-ups, new organisations, check and queue, report). |
| `docs/setup.md` | One-time setup per tenant: inbox, OAuth app, booking link, monday board, scheduled task. |
| `docs/sources.md` | Ticket 07 result: every candidate source checked, kept or dropped and why, with URLs; rows per source and segment; filters and sort order. |
| `docs/handoff-2026-11-21.md` | Where the work stands, batch 1 results, open decisions, exact next commands. |
| `docs/REPO-MAP.md` | This file. |
| `docs/prompts/next-session-target-list.md` | The prompt used to start the ticket 07/08 session. |
| `docs/tickets/README.md` | Ticket index in working order: phase A (get batches out), phase B (turn readers into calls). |
| `docs/tickets/01-booking-attribution.md` | Know which email a booking came from. |
| `docs/tickets/02-booking-page-and-confirmation.md` | The booking page and its confirmation email. |
| `docs/tickets/03-offer-page.md` | One offer page on the branch website. |
| `docs/tickets/04-reply-kit.md` | What to send after "tell me more". |
| `docs/tickets/05-lecture-clash-flag.md` | Flag booked calls that land on a lecture. |
| `docs/tickets/06-show-up.md` | Reminder and prep note so booked calls happen. |
| `docs/tickets/07-candidate-list.md` | Build the candidate list cheaply (done 2026-11-21). |
| `docs/tickets/08-batch-loop.md` | Research, send and review in batches of 25 (batch 1 researched). |
| `docs/tickets/09-follow-ups.md` | Follow-ups without a model (done). |
| `docs/tickets/10-go-live.md` | First supervised run, then the schedule (Manuel's checklist). |
| `docs/tickets/11-shared-registry.md` | Shared registry on monday.com, when a second person sends. |

## tools/ (all plain Python, zero LLM tokens)

| Path | What it does |
|---|---|
| `tools/tenant.py` | Where a tenant's files live; every tool imports it. Picks the tenant from `OUTREACH_TENANT`. |
| `tools/pipeline.py` | `add-org`, `add-contact`, `add-touch`, `set`, `show`: the only way to change `pipeline.yaml`. Checks registry and suppression on add. |
| `tools/registry.py` | `check <domain>`: is anyone in the branch already talking to this organisation? Local file now, monday.com later. |
| `tools/firm_contacts.py` | Pulls the addresses and team pages an organisation publishes on its own site (used by the researcher). |
| `tools/lint_email.py` | Checks a draft: word count, one question, one link, banned words, `[claim:]` IDs exist and are usable, `[src:]` present. |
| `tools/gmail_draft.py` | Gmail: `draft --touch` (adds footer and opt-out), `read`, `sync` (classifies replies, opt-outs, bounces, auto-replies). |
| `tools/google_auth.py` | OAuth for the tenant's sending inbox; token in `private/`. |
| `tools/send.py` | `status`, `check`, `ready`, `approvals`, `approve` (Manuel), `run` (scheduler): every send rule, the ramp, gaps, window, auto-pause. |
| `tools/followups.py` | `prepare`: writes, lints, drafts and queues every due follow-up without a model. |
| `tools/outreach_due.py` | What today's run has to do, in order. Read-only. |
| `tools/stats.py` | Numbers for the weekly review, by arm and tier. Read-only. |
| `tools/writer_lock.py` | One writer for `pipeline.yaml` at a time. |
| `tools/selftest.py` | Offline self-test of every sending rule against a throwaway tenant (55 checks). Run it after any change. |
| `tools/daily_run.ps1` | The scheduled weekday run: preflight login check, one Claude session to prepare, then `send.py run`. |

### tools/sources/ (ticket 07, list building)

| Path | What it does |
|---|---|
| `tools/sources/_common.py` | Fetch with cache, domain de-dup against targets, pipeline and suppression, sort order (Delft/Rotterdam first, then size band). |
| `tools/sources/aedes.py` | Aedes member map feed: housing associations, Rotterdam region. |
| `tools/sources/social_enterprise_nl.py` | Social Enterprise NL members via its public API and member pages. |
| `tools/sources/anbi.py` | Belastingdienst ANBI open data (CC0): nonprofits in Delft and Rotterdam, filtered in code. |
| `tools/sources/rotterdam_subsidies.py` | Writes Rotterdam's 2024 subsidy amount into `size_hint` of matching rows. Adds no rows. |
| `tools/sources/mark.py` | Set a candidate's status by domain; `--pick` prints the next batch by the rule. |

Run order: `aedes.py`, `social_enterprise_nl.py`, `anbi.py`, `rotterdam_subsidies.py`.

## tenants/180dc-delft-rotterdam/ (everything specific to the sender)

| Path | What it is |
|---|---|
| `tenant.yaml` | Who sends, booking link, offer, languages, footer text, target filter, A/B arms, tiers, approval rules, registry settings. |
| `limits.yaml` | Pacing: ramp 20/35/50/65 a day by week, last send 2026-12-22, weekday window 08:30-16:30, 3-8 minute gaps, auto-pause thresholds. |
| `ledger.yaml` | The only claims an email may make about the sender, each with an ID and `usable: true/false`. |
| `targets.yaml` | Candidate organisations (1,796 on 2026-11-21) with source, segment, size hint and status (`new`, `researched`, `rejected` with `why`). |
| `pipeline.yaml` | Organisations, contacts (no addresses) and touches. Empty until batch 1 is drafted. |
| `cards/` | One research card per organisation researched (28 from batch 1). Written once, never redone. |
| `templates/README.md` | Rules for every draft and which template is for what. |
| `templates/first-A.en.md`, `first-A.de.md` | First email, arm A: track record first. |
| `templates/first-B.en.md`, `first-B.de.md` | First email, arm B: two ideas from their site first. |
| `templates/follow.en.md`, `follow.de.md` | Day-7 follow-up skeleton for a hand-written follow-up. |
| `templates/follow.en.txt`, `follow.de.txt` | The text `followups.py` fills in automatically. |
| `templates/chain.en.md` | Second person at the same organisation. |

## Not in the repo (git-ignored, local only)

| Path | What it holds |
|---|---|
| `tenants/*/private/` | Gmail OAuth credentials and token, `contacts.private.yaml` (addresses with the page they came from), `suppression.private.yaml` (opt-outs, bounces). |
| `tenants/*/state/` | Send log, run logs, daily report, local registry, STOP file, source download cache. |
| `tenants/*/drafts/` | Draft emails, tagged and clean. |
| `data/` | Scratch data. |

A second tenant is a copy of `tenants/180dc-delft-rotterdam/` with its own `tenant.yaml`, ledger and
templates; run any tool with `OUTREACH_TENANT=<name>`.
