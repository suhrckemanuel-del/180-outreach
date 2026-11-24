# Scoping 03: enrichment and contact discovery

Date 2026-11-24. Read-only scoping; nothing was sent, bought or signed up for. Token numbers are
estimates from the measured baseline (474k tokens / 28 organisations = 17k each, batch 1) and from
typical page sizes; they are not measured on the new design. Batch 2 must measure them.

Free calls made: Vibe Prospecting `autocomplete` (free, worked), Vibe `fetch-entities-statistics`
(errored, no cost seen), `alexandria_library_search` (free), three web searches, one KvK page fetch.
No credit-spending call was made. Apollo, Clay, Lusha, ZoomInfo need login and were not tried.

## 1. What the 28 cards say about where tokens go

Each card has 9 lines. Only three need judgement: WORKFLOW (is there a repeated form/intake?), IDEAS
(one line each, in their words), VERDICT. ORG/FUNDING/PEOPLE/EMAILS are extraction and can be done by
code for most organisations. The 17k comes from the researcher reading the `firm_contacts.py` JSON plus
`--people` digest (~3-5k), then up to two WebFetch calls whose pages come back as full markdown
(~4-8k each), plus the agent's own prompt and tool overhead. Code can do the first for free and shrink
the second.

Patterns in the cards that predict the verdict:

| Pattern | FIT examples | REJECT examples |
|---|---|---|
| A form that asks questions ("Meld je aan", "Aanmelden", intake, volunteer sign-up) | OASE, Maaszicht, TeachBuddy, Kinderparadijs | Rotown, Theater Babel (only a newsletter form) |
| Funders named on own pages (VSBfonds, Gemeente, Vfonds) | OASE | Corridor, Babel, Rotown |
| Social enterprise segment (67% fit vs 23% ANBI nonprofit) | 8 of 12 | cultural ANBIs (6 of 13 nonprofits) |
| A printed address | all 11 fits have info@ | Rotown (none), Woonstad (security@ only) |
| Mailbox per function (aanmelden@, administratie@) | Maaszicht | Corridor (per-department boxes, no workflow) |

Theater Babel prints personal addresses beside names on /contact/ (deborah@, erik-ward@), the best
contact data in the batch, and was still rejected on workflow. So "has a named address" is not the
bottleneck; "visible workflow" is. Spend enrichment effort on workflow signals, not on people.

## 2. Field by field

"Code" means plain HTTP + parsing (0 LLM tokens, about 5-10 requests, polite gaps, cached 7 days by
`firm_contacts.py`). Coverage figures are my guesses, unmeasured.

| Field | Cheapest source | Cost per org | Coverage estimate |
|---|---|---|---|
| Domain, name, city, segment | Already in targets.yaml (ANBI open data, SE NL, Aedes) | 0 | 100% |
| Printed addresses + source page | `firm_contacts.py` (already code) | 0 tokens | ~85% have at least a role address |
| Named people + titles | Same digest; code regex on title words (directeur, bestuurder, voorzitter, coordinator) + bestuur/team page | 0 code; ~500-800 tokens if a model must pick the person | 60-70% a director or chair name |
| Address tied to a person | Code rule: address and name inside the same HTML block (li, article, vcard) | 0 | ~5-15% (matches Maaszicht, Babel) |
| Workflow signal | Code: count forms and input labels; words aanmelden/inschrijven/intake/verwijzing/vrijwilliger/aanvraag; portal links ("mijn...", login). Whether it is repetitive stays a model judgement | 0 code; ~1k tokens model on a ~600-word extract | form detection ~80%; JS-only forms (Typeform, Jotform, Wix) need crawl4ai rendering |
| Funders | Code: grep a funder-name list (VSBfonds, Vfonds, Oranje Fonds, Cultuurfonds, gemeente, subsidie) on home, over-ons, partners, jaarverslag pages; plus Rotterdam subsidy already in `size_hint` (225 rows) | 0 | funder named on ~40-50% of sites |
| Staff size | Code: team-page name count; regex "(\d+) medewerkers", FTE, vrijwilligers in the jaarverslag text. KvK employees band is paid | 0 | explicit on ~30%; team count as a floor otherwise |
| Income / budget | ANBI financial statement link (section 3); CBF needs written permission | PDF text by code 0; ~1.5-3k if a model reads the table | most ANBIs link statements, formats vary |
| Hiring signal (admin/office) | Code on own site: /vacatures, /werken-bij, sitemap hits; regex titles administratief, office manager, bedrijfsvoering, planner, secretariaat, vrijwilligerscoordinator, controller | 0 | vacancy page ~40%; relevant admin vacancy ~5-10% |
| Job-board hiring | Needs JobSpy/Apify; terms question open with Manuel | n/a | n/a |
| KvK number, SBI, employees | KvK Open Dataset is free but covers only BV/NV, has no name, no KvK number, no employees, 2-digit postcode: useless for stichtingen. KvK APIs are paid per request (Vestigingsprofiel: EUR 6.20/month + EUR 0.02/request; Basisprofiel price not confirmed) | paid | do not use |
| CBF income | Register copying forbidden without permission | n/a | n/a |
| Language, site up | Code: HTTP status, html lang | 0 | 99% |

## 3. Free structured sources, ranked

1. **ANBI publication on the organisation's own site (best).** An ANBI publishes on its own website
   (or a branch site) name, fiscal number, contact details, board names, objectives, policy plan,
   remuneration policy, activity report and financial statements. Enforcement is risk-based and uneven; a
   central portal is provided for in law from 1 Jan 2026 with possible exemptions for small ANBIs (I could
   not confirm it is live). Use: our ANBI row gives the fiscal number and name; code finds a link whose text
   contains ANBI, jaarverslag, jaarrekening or beleidsplan, and pulls the PDF for staff, funders and income by
   regex. It also gives board names for the subject line, with no model. Applies to the ANBI segment
   (1,308 rows) only, not social enterprises or housing corporations.
2. **Own pages by code**: home, over-ons, contact, team, bestuur, vacatures, werken-bij, partners,
   jaarverslag, anbi. `firm_contacts.py` covers most path guesses. Add partners, anbi, jaarverslag,
   steun-ons, financiers, and parse sitemap.xml (lists every URL free) filtering by those words instead of guessing.
3. **Rotterdam subsidy register**: already in size_hint for 225 rows. Other cities' subsidy registers would
   add the same; each is a one-off CSV, not a per-org cost.
4. **Annual report PDFs**: staff (FTE), funders, income via pypdf plus regex; cap at the first 15 pages and
   pages near "financiering" or "FTE"; model only if a table must be read.
5. **KvK**: free dataset useless for us; paid APIs cost money and the ANBI list already gives identity.
6. **CBF**: income figures, but written permission needed (open decision in handoff).
7. **Alexandria**: the only Dutch registers there are the insolvency register (negative check by KvK number,
   low value) and GLEIF. No KvK, ANBI, CBF or subsidy provider.

## 4. Connected tools: verdict

Rule recap: only addresses printed on the organisation's own pages; a database email for a named person
is personal data the organisation did not publish.

| Tool | What it adds | Cost | Conflict with the printed-address rule / GDPR | Verdict |
|---|---|---|---|---|
| Firecrawl scrape / map | Clean markdown, URL list | 0 credits until 14 Dec, then paid | None (own pages); same as crawl4ai | Use crawl4ai locally; map only as sitemap fallback after 14 Dec |
| Firecrawl agent | Multi-page research, structured output | credits, expensive | Facts not tagged per URL by our rules | No; would exceed the 5k target |
| Firecrawl people_company_search | Names, titles, LinkedIn URLs (never emails) | paid per row | Name from a third party violates "every fact about a recipient needs its page"; personal data collected from another source (GDPR Art. 14 duty) | No for now |
| Firecrawl people_company_enrich | Work emails via provider waterfall | paid per hit | Returns an email not printed by the organisation: forbidden | No |
| Alexandria catalogue | Free to browse. Many email finders (Hunter, Apollo, Prospeo, Icypeas, FullEnrich, Findymail) and company enrichers (PredictLeads has hiring) | per call | Email finders and pattern guessers are exactly what the rule bans | No registers we need; finders excluded |
| Vibe Prospecting | Free `autocomplete` worked: LinkedIn categories "non-profit organizations", "community services", "civic and social organizations" exist. Filters for company size band, revenue band and hiring events (hiring_in_operations_department etc.). `fetch-entities-statistics` errored | `enrich-business`, `fetch-entities`, export spend credits; `estimate-cost` free | Prospect data carries personal emails and phones: conflict. Business-level size/hiring signals are not personal data but are third-party and LinkedIn-derived; many small Dutch stichtingen likely have no LinkedIn page, so coverage is doubtful and unmeasured | Maybe business-level only for size/hiring signal after a free sample test on ~20 known domains. Never prospects |
| Apollo, Clay, Lusha, ZoomInfo | Contact emails, firmographics | account + credits | Their value is named-person emails, which the rule forbids; weak coverage of small Dutch nonprofits | No |
| Apify | Maps and job-board actors | money + site terms | Terms decision already open; Apify MCP tools did not load | No |

**Could a database email be used only to find the person's name/title, with the email still going to the
printed address?** Technically yes, for the name and title only. I recommend against it by default:
(1) a name taken from LinkedIn or a vendor cannot be written into an email because the card rule needs the
organisation's own page for each recipient fact; (2) under GDPR it is personal data obtained from a source
other than the organisation, which brings an Article 14 information duty and means docs/lawful-basis.md would
have to name the database; (3) it adds cost for little gain, because workflow, not the name, decided fit in
batch 1. When the site prints no leader name, take it from the ANBI board list or jaarverslag on the
organisation's own site, tagged `[src:URL]`.

## 5. Proposed pipeline, in order, tokens per organisation

Steps 0-5 are code, cached in `state/`, in one `tools/enrich.py` (extends `firm_contacts.py` and the planned
`site_digest.py`). It emits a facts record with the URL of every value.

| Step | What | Tokens |
|---|---|---|
| 0. Free filters on rows already held | drop cultural ANBIs by name words, attach Rotterdam subsidy as funding fact, registry/suppression check | 0 |
| 1. Site alive + sitemap | GET /, robots.txt, sitemap.xml (3 requests); language, redirects | 0 |
| 2. Page selection by URL words | up to 8 pages: contact, over-ons/team/bestuur, vacatures, partners/financiering, jaarverslag/anbi, and 1-2 matching aanmeld/inschrijv/intake/vrijwilliger | 0 |
| 3. Parse (trafilatura; crawl4ai only if a page is JS-empty) | emails + page, names and titles in same block, forms and labels, funder hits, FTE regex, vacancy titles, jaarverslag PDF first 15 pages | 0 |
| 4. Score gate (section 6) | rank, drop below threshold | 0 |
| 5. Digest for the top ~45% | 5 fact lines + 3 best passages (~600 words) with URLs | 0 |
| 6. Model judgement (Haiku, 5-8 orgs per call) | confirms workflow in their words, writes IDEA 1/2, verdict, tier; reads extract only | ~2-2.5k per org (extract ~1.5k, card ~0.3k, amortised overhead) |
| 7. Spot check | one narrow WebFetch if the digest is ambiguous (~15% of orgs) | ~3k x 15% = ~0.5k |

| Design | Tokens per org | Note |
|---|---|---|
| A. Today (script + 2 WebFetch) | ~17k | measured |
| B. Digest only, every org to the model | ~3.5-4.5k | meets target but spends model on orgs code could reject |
| C. This proposal (code gate, 45% to model) | ~1.6-2k average per organisation scanned; ~3-4k per organisation that reaches a verdict | well under 5k |
| D. Code-only verdict | 0 | not enough for IDEAS in their words; use as gate only |
| E. Firecrawl agent per org | likely above 17k equivalent plus credits | reject |

For 300 fits at a 55-60% post-gate fit rate: ~520 organisations reach a model verdict, ~1,150 scanned by code
(1,796 rows held): about 520 x 3k = ~1.6M tokens, versus ~13M today.

## 6. Pre-filter score, in code

Integer points from the facts record. Weights are priors from the 28 cards, not fitted: first run
`enrich.py score` over the 28 labelled cards (11 fit, 17 reject) and adjust.

| Signal | Points | Evidence |
|---|---|---|
| Segment social_enterprise | +3 | 67% fit |
| ANBI non-cultural social/care/youth/housing/education/volunteer words | +1 | Maaszicht, Opwijs, Kinderparadijs |
| Cultural words in name (theater, museum, festival, muziek, orkest, poppodium, galerie) | -3 | 6 of 13 nonprofits, ~0 fit |
| Form with 3+ labelled fields, or aanmelden/inschrijven/intake/verwijzen/aanvragen in nav | +3 | OASE, Maaszicht, TeachBuddy, Equal Recruitment |
| Client or volunteer portal ("mijn...", login, dashboard) | +2 | TeachBuddy, Woonstad |
| Only newsletter form or ticket shop | -2 | Babel, Rotown |
| 1+ named funder, or Rotterdam subsidy EUR 50k-1M | +2 | OASE |
| Staff signal about 8-100 | +1; above ~150: -3 | Corridor mis-rejected as too big (guide is 20-100) |
| Admin/office/bedrijfsvoering/planner/vrijwilligerscoordinator vacancy on own site | +2 | hiring signal |
| A person's name beside a printed address | +1 | Maaszicht, Babel |
| Large woningcorporatie | -2 | 0 of 3 |
| Gate: no on-domain address, site unreachable, suppressed or blocked | skip | Rotown, Woonstad |

Threshold: to the model if score >= 3. Check recall on the 11 known fits (all must clear) and how many of
the 17 rejects it would have skipped. Hand-review the skipped bottom decile of each new batch (about 30
organisations) to catch hidden fits. After ~100 verdicts replace the weights with logistic regression on the
same features (setfit stays an option, per the tooling review).

## 7. Contact strategy

Expect the printed-address mix to stay about 85% role-only and 10-15% personal beside a name. Do not try to
raise the named share through databases. Instead:
- Prefer a printed functional address that matches the workflow (aanmelden@, vrijwilligers@, administratie@)
  over info@: it reaches the owner of the workflow and is not personal data. Maaszicht printed five.
  Store a `role_match` field and use it when the template says "your intake".
- The director's name for the subject line comes from the ANBI board or team page, tagged `[src:]`.
- The second contact per organisation can be a functional mailbox, which also lowers the personal-data load.

## 8. Decisions and caveats for Manuel

1. Approve `tools/enrich.py` as stage one; the researcher agent then only reads the extract. Measure tokens on batch 2.
2. Vibe business-level enrichment: allow a free `show-sample`/`estimate-cost` test only; no prospects, no emails.
3. The CBF email to data@cbf.nl is still the only route to income data.
4. Unverified: KvK Basisprofiel price; whether the central ANBI portal is live; any database's coverage of small
   Dutch foundations; all token and coverage estimates; section 6 weights.

Sources: KvK Open Dataset page (https://www.kvk.nl/producten-bestellen/kvk-handelsregister-open-data-set/),
KvK developer portal (https://developers.kvk.nl/), Belastingdienst on publishing ANBI information on a website
(https://belastingdienst.nl/wps/wcm/connect/bldcontenten/belastingdienst/business/business-public-benefit-organisations/public_benefit_organisations/publishing-anbi-information-on-a-website),
SRA note (https://www.sra.nl/nieuws/004501/2025/10/meer-transparantie-anbis), repo cards, handoff-2026-11-21, tooling-review-2026-11-23.
