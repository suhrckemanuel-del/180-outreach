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
