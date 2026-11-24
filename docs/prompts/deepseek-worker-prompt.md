# DeepSeek worker: build queue for the outreach kit

You are a coding agent working in a local clone of https://github.com/suhrckemanuel-del/180-outreach
(private; do not copy any of it to a public place). Claude orchestrates and audits; you build. Work through
the queue below in order, without asking questions. If something is ambiguous, pick the safest reading, write
the assumption in `out/deepseek-log.md`, and continue.

## Setup (once)
1. `git checkout -b deepseek/work-2026-11-25`. All work stays on this branch. Never push, never merge.
2. Read `CLAUDE.md`, then `docs/scoping-2026-11-24/00-plan.md`, then the file for the task you are on. Do not read
   the whole repo. Do not read `tenants/*/private/`, `tenants/*/state/`, `tenants/*/drafts/` or `data/`.
3. `python tools/selftest.py` must print `0 failed` before you start and after every task.

## Rules per task
- Tests first: add checks to `tools/selftest.py` (stubbed HTTP, no network) that fail, then make them pass.
- One commit per task: `git commit -m "T<n>: <what>"`. Never commit anything in `private/`, `drafts/`, `state/`, `data/`.
- Append to `out/deepseek-log.md`: task, files touched, tests added, selftest count, assumptions, what you did not do.
- If a task fails twice, log it, `git stash` the attempt, and move to the next task.
- Zero model calls inside the code you write. Everything you build runs with plain Python and the standard library
  plus what is in `requirements.txt` (add to it only if truly needed, and say so).

## Queue (do in this order)
**T1. Staff-count bug in `tools/enrich.py`.** A figure like "500 medewerkers" on a partners page is a partner's size,
not the organisation's. Count staff only from pages whose URL or heading looks like about / team / organisation /
over-ons / wie-zijn-wij, never partners / klanten / opdrachtgevers. Test with a fixture page.

**T2. Better funder and contact coverage in `enrich.py`.** Today it reads 8 pages and misses funders named on a
partners page and addresses on a team page. Add: when the homepage links a partners/fondsen page or a team/contact
page, those two always make the 8. Fixture tests for both. Keep the request budget (`FETCH_BUDGET`) unchanged.

**T3. Lead-list scripts.** Read `docs/prompts/2026-11-25-s2-lead-lists.md`. Build only the parts whose decision in
`docs/decisions-2026-11-25.md` is answered `yes`; blank means skip and log it. Follow `tools/sources/_common.py`.
Respect robots.txt, one request at a time, cache downloads. No Google Maps, no LinkedIn, no Indeed.

**T4. `tools/calls.py`.** Read `docs/prompts/2026-11-25-s4-high-value-track.md`, the calls section only. A small CLI
that tracks planned and made calls (org, date, outcome, next step) in `tenants/<t>/state/calls.yaml`. It never
dials, never fetches. Tests for add / list / due-today.

**T5. `tools/verdict_harness.py`.** Provider-agnostic test bench for a cheap model: reads digests from
`tenants/<t>/state/enrich/*.digest.md`, builds the verdict prompt from `docs/prompts/cheap-model-context.md` (job A),
calls a function `model(prompt) -> str` that the user supplies via an env var pointing at a Python file (no keys in
the repo), validates the JSON (verdict fit|reject, tier 1-3, reason <= 25 words, evidence_url must be a substring of
the digest), compares to the answer key in `tenants/<t>/cards/*.md` (`VERDICT:` line), and prints the match rate and
every mismatch. Include a stub model for the self-test.

**T6. Reply-kit tests.** Add tests for the cases in `tools/gmail_draft.py classify` that are missing (out-of-office
in Dutch and German, "unsubscribe" in a body, bounce notices). Only add tests; do not edit `gmail_draft.py`.

**T7. Docs.** Update `docs/REPO-MAP.md` for new files, and add `docs/enrich.md` (what it does, how to run, how the
score is calibrated, known limits). Short and factual.

## Do not touch (propose a patch in `out/patches/<name>.diff` and a note in the log instead)
`tools/send.py`, `tools/gmail_draft.py`, `tools/pipeline.py`, `tools/registry.py`, `tools/tenant.py`,
`tenant.yaml`, `ledger.yaml`, `limits.yaml`, `pipeline.yaml`, `targets.yaml`, and anything under `private/`,
`state/`, `drafts/`, `data/`.

## Hard stops
Never write, guess or construct an email address. Never send, approve or call Gmail. Never claim anything about the
sender outside `ledger.yaml`. Never name a client. Never use a service other than the model running you.
Never put real names or addresses of staff into new files, fixtures or logs: use invented ones (`jan@voorbeeld.nl`).

## Done
When the queue is empty or you are stuck on three tasks in a row, stop and write `out/deepseek-log.md` summary:
tasks done, commits, selftest count, open assumptions, anything that needs a human decision.
