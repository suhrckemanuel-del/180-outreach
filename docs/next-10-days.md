# Next 10 days

Hand-edited. `tools/report.py` prints this file in the report, so keep it short and concrete.
Dates assume a start on Monday 24 November 2026; move them if the start slips.

## This week: make the numbers real

- **Mon 24 Nov** — commit this session's work on the branch, then skim `out/report.html` and fix anything that reads wrong.
- **Tue 25 Nov** — answer D1, D2 and D17 in `docs/decisions-2026-11-25.md`; they unblock the lead list and the commits.
- **Wed 26 Nov** — run `python tools/enrich.py batch --pick 50 --csv` on the non-cultural Delft and Rotterdam rows; read the top 40 in the report.
- **Thu 27 Nov** — send the 10 batch-1 emails still waiting, then approve the first 25 of the new shortlist.
- **Fri 28 Nov** — make the first cold calls from `python tools/calls.py due`; log every outcome.

## Next week: volume without noise

- **Mon 1 Dec** — run the next 50 enrichment rows and refresh the shortlist.
- **Tue 2 Dec** — check the bounce rate and the reply rate in `python tools/stats.py` before raising the cap.
- **Wed 3 Dec** — draft the team demo: report, explainer, and the numbers by arm.
- **Thu 4 Dec** — decide on the second inbox (D11) and the January wave (D10).
- **Fri 5 Dec** — review what the week produced and rewrite this file for the following ten days.
