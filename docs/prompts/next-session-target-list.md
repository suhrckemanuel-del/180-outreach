Open a new Claude Code session in C:\Users\User\Desktop\180dc-outreach and paste this:

---

We are building client outreach for 180DC Delft & Rotterdam. Read CLAUDE.md, docs/build-spec.md and docs/tickets/README.md, then tickets 07 and 08. Run `python tools/selftest.py` once to see the kit is healthy.

Work ticket 07, then batch 1 of ticket 08, and stop before anything is sent.

Ticket 07, the candidate list:
1. Check each source in the ticket (CBF register, ANBI register, Social Enterprise NL, Aedes members for the Rotterdam region, Rotterdam and Delft subsidy recipient lists, the funding-radar digests on my Desktop). For each, find out what it gives: name, website, city, size or income, and whether it can be downloaded or paged through without a login and without breaking its terms. Write the findings to docs/sources.md as a table, with the URL you checked.
2. For every source that gives websites, write a small script in tools/sources/ that adds rows to tenants/180dc-delft-rotterdam/targets.yaml: name, website, city, country, segment, source, size_hint, status new. Plain HTTP and parsing, no model reading pages. Use Firecrawl only to discover how a source is structured. De-duplicate on the website domain, and against the pipeline and the suppression list. Put Delft and Rotterdam first.
3. Stop and ask me if a source needs a login, an account, payment, or looks like it forbids scraping. Do not work around that.
4. Target: at least 300 new rows with a website, at least 100 in Delft or Rotterdam.

Ticket 08, batch 1:
5. Pick 25 organisations by the rule in the ticket: about 13 nonprofits and 12 social enterprises, plus 2 or 3 Rotterdam woningcorporaties if the list has them, Delft and Rotterdam only. Check each with `python tools/registry.py check`.
6. Research with the researcher agent, five organisations per call. Save each card to tenants/180dc-delft-rotterdam/cards/. Mark rejects in targets.yaml with the reason.
7. For the fits: pipeline.py add-org, add-contact (only addresses printed on their own site), add-touch --kind first --workflows with the two workflows the email will name. Draft from the template the command names, lint until there is no ERROR, one checker agent call for the batch, then gmail_draft.py draft --touch and send.py ready. All of batch 1 should end in needs_approval.
8. Do not run send.py run or send.py approve. I approve and send.

End with a short report: the sources table (kept and dropped, and why), how many target rows per source and segment, batch 1 fit rate by segment, the list from `python tools/send.py approvals`, and any decision you need from me. Do not commit; ask me first.
