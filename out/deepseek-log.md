# Cheap-model worker log, 2026-11-25

Branch `deepseek/work-2026-11-25`. Base selftest before any task: **96 passed, 0 failed**.
No model calls in any code; standard library + `requirements.txt` only. Nothing pushed.

## T1. Staff-count bug in `tools/enrich.py`

- Files: `tools/enrich.py`, `tools/selftest.py`, this log.
- What changed: `staff_page_ok()` gates every `N medewerkers` figure. A figure counts only on a page
  whose URL (or the heading right above the figure) is about / team / over-ons / wie-zijn-wij /
  organisatie / bestuur / medewerkers; a page whose URL says partners, klanten, opdrachtgevers, fondsen,
  sponsor, steun, donateur, samenwerking, netwerk, leverancier or deelnemer never contributes. The
  homepage still counts when the 240 characters before the figure carry none of those words.
- Tests added: 3 (`enrich T1:` lines in `tools/selftest.py`): a partner's 500 is dropped while the
  organisation's 30 (homepage) and 24 (team page) are kept; a partners-only homepage yields no staff.
- Selftest after: **99 passed, 0 failed** (T1 alone), **102 passed, 0 failed** with T2.
- Assumption: a homepage figure is the organisation's own unless the sentence before it is about
  partners/clients/funders. Keeping the homepage was needed because batch-1 digs report size from it.

## T2. Better funder and contact coverage in `enrich.py`

- Files: `tools/enrich.py`, `tools/selftest.py`, this log.
- What changed: `GUARANTEED` in `choose_pages()` reserves two of the 8 page slots before the category
  loop: the best partners/fondsen/financiering page and the best team/contact page. The team pick is
  preferred when the URL or anchor also says contact/bereik/kontakt, because that page carries the
  addresses. The reserved categories are skipped in the normal loop, so nothing is fetched twice.
  `FETCH_BUDGET` unchanged (16).
- Tests added: 3 (`enrich T2:`): the partners page and its funder are read when eight other pages match;
  `/team/contact` (with the address) is read rather than only `/team`; the chosen set stays <= 8.
- Selftest after: **102 passed, 0 failed**.
- Assumption: "those two always make the 8" is read as two reserved slots, not as a raised page cap.
- Note: the pre-existing uncommitted edits to `tools/selftest.py` (made before this session) were
  committed with T1 because the file is one unit; nothing in `private/`, `drafts/`, `state/` or `data/`
  was staged.

## T3. Lead-list scripts (`docs/prompts/2026-11-25-s2-lead-lists.md`)

- **Skipped, as the prompt requires.** `docs/decisions-2026-11-25.md` has every `Answer:` blank (D1, D2,
  D3, D4, D5, D6, D17). A blank answer means "not decided: the session skips that part and says so", and
  every build item in S2 hangs off one of those decisions (regional ANBI needs D1, LRK needs D2, the
  segment/mark changes need D1, the list-request emails need D6, committing needs D17).
- Files: none. Tests added: none. Selftest unchanged at that point: **102 passed, 0 failed**.
- Nothing was written to `targets.yaml`, `pipeline.yaml` or `tenant.yaml`.

## T4. `tools/calls.py`

- Files: `tools/calls.py` (new), `tools/selftest.py`, this log.
- What it is: `add` / `list` / `due` / `log` over `tenants/<t>/state/calls.yaml` (gitignored). `due` prints
  the organisation, the number printed in its dossier (or `--phone`), the dossier path and its opener.
  `log --outcome call_booked` runs `pipeline.py set --outcome call`; `not_interested` suppresses the domain
  and sets the org `opted_out`, the same effect as an email opt-out. It never dials, fetches or sends.
- Tests added: 7 (`calls:` lines): refusing a second open call; due-today vs due-later; the number and
  opener are printed; list order by due date; call_booked reaching the pipeline; refusing a log with no
  planned call; not_interested suppressing; calls never entering `pipeline.yaml` and `send.py` never
  reading `calls.yaml`.
- Selftest after: **110 passed, 0 failed**.
- Assumption: `--org` is the pipeline org id; a call for an unknown org is allowed but warns, because the
  dossier track builds the call list before `add-org`. No staff names are stored in `calls.yaml`; only the
  org id, date, outcome and a free-text note.

## T5. `tools/verdict_harness.py`

- Files: `tools/verdict_harness.py` (new), `tools/selftest.py`, this log.
- What it is: reads `state/enrich/*.digest.md`, builds the job-A prompt from
  `docs/prompts/cheap-model-context.md` (the job-A block + the Never section, then the digest), calls the
  user's `model(prompt) -> str` loaded from the Python file in `VERDICT_MODEL` / `--model`, validates the
  record (fit|reject, tier 1-3, reason <= 25 words, evidence_url a substring of that digest), compares the
  verdict with the `VERDICT:` line of `cards/*.md`, and prints the match rate plus every mismatch and every
  invalid record. Exit 1 only for unusable records; a wrong verdict is data, not a failure.
- Tests added: 12 (`harness:` lines): prompt contains the rule and the digest; fenced JSON; prose rejected;
  each validation rule; the two stubbed digests matching the answer key 2/2; a raising model reported; a
  missing model file refused. No test or fixture calls a real model or network.
- Selftest after: **121 passed, 0 failed**.
- Assumption: the shared context doc lives with the code (`REPO/docs`), not under a tenant, so the harness
  reads it from `tools/verdict_harness.py`'s parent even when `OUTREACH_ROOT` points at a throwaway copy.
- Not done: no batch run against a real cheap model (that needs the user's model file).

## T6. Reply-kit classification tests

- Files: `tools/selftest.py`, this log. `tools/gmail_draft.py` was **not** edited.
- Tests added: 8 (`classify:` lines): Dutch out-of-office subject and a Dutch body carrying
  `Auto-Submitted`; German `Abwesenheitsnotiz` subject and a German body with `X-Autoreply`;
  "unsubscribe" mid-sentence in a longer English body; a `postmaster` bounce; a bounce with
  `X-Failed-Recipients` and the subject "unsubscribe"; a bounce that also says "geen interesse"
  (bounce must win over opt-out). All 8 passed against the current `classify` without any code change.
- Selftest after: **129 passed, 0 failed**.
- Not done: no case asserts a body-only out-of-office without any auto header, because `classify` reads
  those as human today; that is a known limit of the current rule, recorded here rather than papered over
  with a test that would lock in wrong behaviour.
