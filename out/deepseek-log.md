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
