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

## T7. Docs

- Files: `docs/enrich.md` (new), `docs/REPO-MAP.md`, this log.
- `docs/enrich.md`: what `enrich.py` reads and writes, the request budget, the four commands, the 12 score
  signals with their points, the calibration result on the 28 cards, and the known limits (staff only from
  about/team pages, printed-only addresses, JS/PDF pages, heuristic page selection, 600-word digest).
- `REPO-MAP.md`: new rows for `tools/enrich.py`, `tools/calls.py`, `tools/verdict_harness.py`, the
  `docs/enrich.md` row, selftest count 75 -> 129, date bumped to 2026-11-25.
- Tests added: none (docs only). Selftest after: **129 passed, 0 failed**.

## Summary

- Tasks done: T1, T2, T4, T5, T6, T7. T3 skipped because every decision in
  `docs/decisions-2026-11-25.md` is blank, which the S2 prompt defines as "skip and say so".
- Commits on `deepseek/work-2026-11-25` (nothing pushed, nothing merged):
  `T1` staff counts, `T2` guaranteed funders/team pages, `T4` calls.py, `T5` verdict_harness.py,
  `T6` reply-kit tests, `T7` docs.
- Selftest: 96 passed / 0 failed at the start, **129 passed / 0 failed** at the end.
- Tests added: 33 (3 T1, 3 T2, 7 T4, 12 T5, 8 T6); T7 adds none. 96 -> 129 checks.
- Open assumptions: staff counts kept on the homepage unless the sentence before the figure names
  partners/clients/funders; "those two always make the 8" read as two reserved page slots, budget
  unchanged; `calls.py --org` is the pipeline org id and an unknown org only warns; the harness reads
  the shared context doc from the repo root, not from `OUTREACH_ROOT`.
- For a human decision: the blanks in `docs/decisions-2026-11-25.md` (D1-D6, D17) block T3 and every
  lead-list script; and the harness has not been run against a real cheap model, which needs the user's
  model file and, if it costs money, their go-ahead.
- Not done, deliberately: no model call, no network in any test, no change to `send.py`,
  `gmail_draft.py`, `pipeline.py`, `registry.py`, `tenant.py`, `tenant.yaml`, `ledger.yaml`,
  `limits.yaml`, `pipeline.yaml`, `targets.yaml`, or anything under `private/`, `state/`, `drafts/`,
  `data/`. No email address was written, guessed or constructed.

## W0-W6. Second session, 2026-11-24: report, explainer, handoff

- Answers given in the session prompt: D1, D2, D17 and COMMIT_DOCS were all blank.
  - W0 skipped: nothing was written into `docs/decisions-2026-11-25.md`; only D0 is answered.
  - W1 skipped: COMMIT_DOCS was blank, so the planning docs were not committed.
  - D17 was blank, so **no commits at all** were made. W2-W5 live in the working tree and are listed
    in `HANDOFF.md`; W6 is this log entry.
- W2 done: `enrich.py batch --csv [PATH]` (default `out/shortlist.csv`). Ten columns, no personal
  names and no addresses (address_found is yes/no); the terminal table is unchanged. 5 checks.
- W3 done: `tools/report.py` writes `out/report.html` (16.4 KB, about 0.7 s, light CSS only, no
  external file, no @ and no contact name anywhere in the page) and prints `docs/next-10-days.md`.
  8 checks.
- W4 done: `docs/explainer/index.html`, 5 slides, arrow-key and click navigation, 8 "why we built it
  this way" boxes, zero external requests (checked in the browser: one document request, no console
  errors). Numbers rounded; it points at report.html for live figures.
- W5 done: `HANDOFF.md` at the repo root.
- W6 done: selftest **142 passed, 0 failed** (was 129); report written; the safe commands in the
  handoff's run tables were executed, and the ones that send or write to Gmail are marked as not run.
- Bugs found while checking the real data, both fixed and covered:
  - one card's reason mentions `management@` with no domain, which the email scrub missed;
  - a test contact named `S` made the name scrub rewrite single letters inside CSS class names, so
    scrubbing now uses word boundaries, a three-character minimum, and runs on text fields only.
- Not done, deliberately: no push, no commit, no email, no Gmail write, no OAuth, no model call, no
  read of `private/`, no change to Manuel's uncommitted files, no edit of `targets.yaml`.
- Still open: D1-D17 (D0 answered), and `out/shortlist.csv` was not generated, so the report shows the
  gate stage as "not measured yet" rather than guessing.
