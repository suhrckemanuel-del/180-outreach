# 07 Build the candidate list first, cheaply

**Problem.** `targets.yaml` is empty and nothing can be drafted without it. Researching organisations
one by one before we know where good ones come from is the expensive way round.

**Approach: list first, research later.** Pull a broad list of names and websites with plain scripts
(no model reading pages), tag every row with its source and segment, and only spend research on the
rows a batch picks (ticket 08).

**Steps.**
1. Check each source, 15 minutes each, and write down what it gives (name, website, city, size,
   income, a way to download or page through it) in `docs/sources.md`:
   - CBF register of recognised charities (has income figures)
   - ANBI register (Belastingdienst; many small foundations, often no website)
   - Social Enterprise NL members
   - Aedes members (woningcorporaties), Rotterdam region only
   - Gemeente Rotterdam and Delft subsidy recipient lists, if published (shows the funding source directly)
   - Impact startups from the funding-radar digests (`Desktop/funding-radar-*.md`), as a comparison segment
   Keep any source that gives a website. Drop any that needs a login or forbids scraping.
2. One script per kept source, `tools/sources/<name>.py`, that writes rows into `targets.yaml`:
   `{name, website, city, country, segment, source, size_hint, status: new}`. De-duplicate on the
   website domain across sources and against the pipeline and suppression list.
3. Filter in code, not by reading: drop rows with no website, rows outside NL (first round), and the
   obvious national giants (income above a cut-off, if the source has income).
4. Delft and Rotterdam first: sort so those come out of the list first.

**Not in this ticket.** Reading websites, finding people, deciding tier. That is ticket 08, per batch.

**Done when.** `targets.yaml` holds at least 300 `new` rows with a website, at least 100 of them in
Delft or Rotterdam, each with its source, and `docs/sources.md` says which sources were worth it.
