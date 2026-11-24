# Scoping 2026-11-24: what gets the most clients, in order

Five read-only scoping passes, one file each in this folder: `01-lead-sources.md`, `02-tools.md`,
`03-enrichment.md`, `04-local-assets.md`, `05-capacity-testing.md`. This page is the combined plan.
Numbers are estimates unless marked measured. The two weakest inputs: fit rates (from 12 and 13
organisations) and call-to-signed (no benchmark, assumed 10-35%).

## Where we stand

- **Today's plan gets about 0.8 signed projects** (base case), with a 19% chance of 2 or more. One inbox
  on the 20/35/50/65 ramp from 25 Nov sends **850 emails by 22 Dec**, which is 444 new organisations
  (not ~1,000: that assumed a 23 Nov start). `05` §1-2.
- **There are plenty of organisations.** The ANBI register alone has 31,421 usable rows nationwide, and
  `targets.yaml` holds 1,796. `01`.
- **Researched fits are what's scarce.** Week 1 needs 100 first emails and 10 are ready. At 17k tokens
  per organisation, week 1 alone means ~235 organisations researched (~4M tokens). `05` §1.4.
- **The sending cap binds from week 3**, and only volume (January, a second inbox) or a better reply and
  call rate moves the number of signed projects. `05` §2.4.

So the order is: research cheaply, research the right organisations, protect the domain, add volume,
convert better.

## The plan

### A. This week, no decision needed (build)

| # | What | Effort | Moves | Source |
|---|---|---|---|---|
| A1 | `tools/enrich.py`: per organisation, fetch home + sitemap + up to 8 pages by URL words (contact, over-ons, team/bestuur, vacatures, anbi/jaarverslag, aanmelden/intake), trafilatura to text, extract emails with their page, names beside them, forms and their labels, funders, staff hints, admin vacancies. 0 tokens. | 1 day | tokens per org | `03` §5, `02` stage 2 |
| A2 | Score gate in code on A1's facts (12 signals: social enterprise +3, form with labelled fields +3, named funder or subsidy +2, admin vacancy +2, cultural name -3...). Calibrate on the 28 batch-1 cards: all 11 fits must pass. Only those above the line go to the model. | 3 h | fit rate, tokens | `03` §6 |
| A3 | Researcher reads the ~600-word digest only, 5-8 organisations per call, returns card fields. Target ~3-4k tokens per organisation that gets a verdict, ~1.6M for 300 fits (vs ~13M today). | 3 h | tokens | `03` §5 |
| A4 | Port the MX and role-address checks from `BDR-pipeline/app/services/email_finder.py` (yours, MIT, has tests), **without** its address guessing. | 2 h | bounces | `04` |
| A5 | New lists: `anbi.py --region` for Rijnmond + Haaglanden, non-cultural only (2,095 rows); Rotterdam's recognised social entrepreneurs (~100); the LRK childcare register (CC0, websites, places per location as a size proxy, 31 nonprofit holders in Delft/Rotterdam, 377 nationally); Utrecht and Den Haag subsidy registers as funding facts. | 1 day | leads | `01` |
| A6 | Render tier-2 emails from card fields in code; the model writes one sentence. Lint and checker unchanged. | 4 h | tokens, consistency | `05` §4, tooling review item 7 |
| A7 | Deliverability: run mail-tester once on a draft; add a complaint stop rule (any spam complaint pauses the kit). | 1 h | inbox placement | `05` §5 |

Then run batch 2 through A1-A3, social enterprises first (67% fit), and measure tokens per organisation
against the 17k baseline.

### B. Needs your decision (each unlocks one step)

| # | Decision | My recommendation | What it unlocks |
|---|---|---|---|
| B1 | Drop cultural ANBIs and housing associations, add childcare, youth care, welzijn, work-integration SEs | Yes: cultural venues 0 of 6, housing 0 of 3 in batch 1 | A2, A5 |
| B2 | Anthropic API key with a spend cap for bulk research | **Decided 2026-11-24: no.** Everything runs in Claude Code; A1-A3 carry the token savings | (none) |
| B3 | January wave, 5-16 Jan (a `limits.yaml` change) | Yes, for pending follow-ups + first emails 5-9 Jan only | 850 → 1,435 emails; expected signed 0.8 → 1.3 |
| B4 | A second inbox from another 180DC member | Yes, but only after a clean first week in Postmaster Tools. Needs code (sender per touch) and a person who answers replies | → 1.5 signed; with B3, 2.45 (70% chance of 2+) |
| B5 | Who holds 180dc.org DNS: Postmaster Tools verification and a DMARC `rua=` report address | Ask before the first send | seeing a reputation drop before replies stop |
| B6 | The `BR-PROJECT-SHAPE` claim: "a student team working with you from February to May" | Yes: the ask becomes a project, not a chat | conversion |
| B7 | Legal team: Telecommunicatiewet art. 11.7 for email to published organisation addresses | Get the answer before B3/B4 raise volume | volume safely |
| B8 | Robots.txt on the LRK host says `Disallow: /`, but the file is the official open-data download | One cached fetch is fine, but it's your call | A5 childcare list |
| B9 | Vibe Prospecting, company-level fields only, after a free coverage test | Optional, low value | size and hiring signals |

### C. After a reply: converting it (the least known, highest-leverage step)

Moving call-to-signed from 20% to 30% is worth as much as 1.5x the volume (`05` §2.4).
Booking page, reply kit and offer page (tickets 02-04), a one-page scoping template, the funding path
ready for the call (the subsidy fact), same-day answers to replies, and warm introductions (alumni,
advisers, Rotterdam funders) for the top 30 tier-1 organisations.

## Ruled out, and why

| Tool or source | Why not |
|---|---|
| Google Maps (gosom, Places API, Apify) | Terms forbid scraping and storing; your own AMSA contracts note says so too. OpenStreetMap Overpass is the lawful fallback if lists run short. |
| JobSpy, LinkedIn, Indeed | Terms forbid automated access. The hiring signal comes from the organisation's own vacancy page (A1). |
| Apollo, Clay, Lusha, ZoomInfo, Vibe prospects, Firecrawl people enrich | Addresses not printed by the organisation: breaks the kit's rule and `lawful-basis.md`. |
| Firecrawl agent | 0 credits until 14 Dec, and costlier per org than the 5k target. |
| Reacher SMTP check | Needs port 25; the 3% bounce auto-pause already covers it. |
| instructor, vale, SOW repos, self-hosted CRMs, Instantly, warm-up networks | No gain over what the kit has, or paid, or a reputation risk. |
| afa-* / AMSA / one.immo code | Client-owned, no licence: reuse the design, not the code. |
| KvK open dataset, fund grantee lists (Oranje Fonds, DOEN, VSBfonds...) | No names or websites; no usable public lists. |

## Testing, honestly

With ~222 organisations per arm, a 2% vs 4% reply-rate gap is detected about 23% of the time. Only a large
gap (4% vs 12%) shows before 22 Dec. Judge arms only on "any human reply" 14 days after sending, within the
same segment and tier, and stop early only with the strict table in `05` §3.3 (10-0, 13-2, 17-3...). Don't
test subject lines or send times at this volume.

## Two things to fix soon in the kit

- `List-Unsubscribe` is a `mailto:` header. If 180dc.org is a Gmail bulk sender (~5,000 a day across all
  its senders; the status never expires), Google requires one-click unsubscribe over HTTPS. Find out the
  domain's volume (B5), and add a small HTTPS endpoint only if it applies.
- Fit rates, the score weights and call-to-signed are guesses until batch 2. Re-run `05`'s model once batch
  2 has replies.
