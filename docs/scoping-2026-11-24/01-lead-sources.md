# Lead sources beyond sources.md, scoped 2026-11-24

Read-only research. Nothing was added to the kit, nothing scraped in bulk, no sign-ups, no email. Single downloads of
open-data files (LRK csv, ANBI zip already cached, Utrecht xlsx, one Den Haag API call) were used only to count rows.
"Verified" means I opened the source's own page or file. "Unverified" means a search snippet or memory only; re-check
before building.

## Bottom line

1. The biggest unused pool is already in hand: **ANBI nationwide** (31,421 rows pass the kit's own filters; 7,103 carry the
   cultural flag). `anbi.py --region` alone adds 2,095 non-cultural rows in Rijnmond and Haaglanden. Rows are not the
   bottleneck; research tokens per organisation are.
2. The best new source is the **Landelijk Register Kinderopvang (LRK)**: CC0 csv, own-website column, legal form, KvK number and
   places per location (a real size proxy). Childcare and peuterzaal foundations look like the two batch-1 education fits
   (Opwijs, Kinderparadijs: enrolment and fees visible).
3. **Rotterdam's own "erkende sociaal ondernemers" list plus the Impactkaart and Goed Inkopen 010 platforms** (run by Voor Goed
   Agency) are a local source of social enterprises, the segment with the 67% fit rate. Only 25 are left from Social Enterprise NL.
4. Municipal subsidy registers (Utrecht, Den Haag, Vlaardingen) give no websites, but work as enrichment of ANBI rows exactly like
   `rotterdam_subsidies.py`: they give funding and size, which the researcher lacked.
5. No source gives staff counts. Nothing found for Delft that the kit does not already have.
6. Maps, JobSpy, LinkedIn, Indeed: terms problems, decisions for Manuel, listed below. The pool without them is already
   about 3x the 300 fits needed (estimate at the end).

## Ranked table

Fit estimate is relative to batch 1 (social enterprises 67%, n=12; ANBI nonprofits 23%, n=13, but 3 of 7 non-cultural = 43%;
housing 0%). All fit figures are small-sample guesses.

| # | Source | Rows in our regions | Website / size signal | Terms | Effort | Expected fit | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Social Enterprise NL (already in kit, not yet worked) | 25 left in Delft/Rotterdam, 34 Rijnmond/Haaglanden, 391 rest of NL | site yes / size no | already cleared in sources.md | none, rows exist | 50-67% | **adopt now** (use before anything else) |
| 2 | Rotterdam erkende sociaal ondernemers (PDF, April 2026, monthly) + Impactkaart + Goed Inkopen 010 | list ~100 names (policy target was 50 to 100 recognised); Impactkaart count not shown | names only in the PDF (websites need a lookup); Impactkaart/GI010 show detail pages, JS-rendered / size no | PDF is a public tender annex; Impactkaart page states no terms, contact impactkaart@voorgoedagency.nl; GI010 has a disclaimer I could not read | PDF: easy; the two sites: headless or ask Voor Goed for an export | 50-60% | **adopt now** for the PDF; **decision for Manuel** to email Voor Goed for the Impactkaart export |
| 3 | LRK childcare register (DUO), nonprofit holders | Delft+Rotterdam 31 holders (20 with 60-700 places); Rijnmond/Haaglanden 72 (33); Randstad subset 134 (52); NL 377 (345 with a website) | website column yes, kindplaatsen per location (size proxy), KvK number | CC0 open data, but host robots.txt says `Disallow: /` (see note) | one csv, plain HTTP, ~12 MB | 35-45% (n=2 comparable fits) | **adopt now** |
| 4 | ANBI `--region` and rest of NL, with a care/welzijn keyword priority and the cultural flag dropped | Rijnmond/Haaglanden 2,095 non-cultural; Delft+Rotterdam 990 non-cultural (361 cultural already loaded); rest of NL 21,233 non-cultural | website yes / no size | CC0 | already built: flag only | ~25-40% for non-cultural social/care | **adopt now** |
| 5 | Subsidy registers as enrichment: Utrecht, Den Haag, Vlaardingen | Utrecht 970 grants in the April 2026 file, 286 distinct applicants; Den Haag row count not obtained (see note); Vlaardingen csv, count not checked | **no website**; amount paid = size and funding signal | Utrecht CC0, Den Haag CC0 page (register itself a web app), Vlaardingen CC0 | Utrecht: xlsx, trivial. Den Haag: needs the app's JSON. Vlaardingen: csv | raises fit of matched ANBI rows (guess +10 points); adds no rows | **adopt now** (Utrecht first) |
| 6 | KvK Handelsregister open dataset | 0 usable | no name, no website, BV and NV only | CC BY 4.0 | - | - | **skip** (verified: fields are start date, legal form, 2-digit postcode, SBI) |
| 7 | KvK paid APIs (Zoeken, Basisprofiel) | all legal forms, by KvK number | name, SBI, sometimes employees | paid per call | API key and money | - | **skip** (spends money; ask only if the free pool runs dry) |
| 8 | CBF register (already dropped) | national giants mostly | income on paspoort pages | disclaimer forbids copying | email data@cbf.nl | low (giants) | **decision for Manuel**, unchanged |
| 9 | Google Maps (gosom scraper) | unbounded, commercial businesses mixed in | website yes, size no (review count only) | **terms problem**: Maps Platform terms restrict scraping and storing Maps content; the Service Specific Terms snippet I saw allows caching `place_id` only | scraper ready, one script | est. 15-25% (commercial noise) | **decision for Manuel** |
| 10 | Google Places API (the licensed route) | same | website needs the higher-priced SKU (from memory, unverified: free monthly allowance of about 1,000 calls) | licensed, but storing results beyond place_id still conflicts with the terms snippet | billing account (a card) | as row 9 | **decision for Manuel**, I would not recommend |
| 11 | JobSpy on LinkedIn, Indeed, Glassdoor | hiring signal, few rows | company name, no size | **LinkedIn user agreement 8.2 forbids scripts, robots and automated means** (verified); Indeed robots.txt is long and disallows many paths, its terms forbid scraping (unverified) | scraper ready | signal, not source | **decision for Manuel** |
| 12 | Adzuna jobs API | NL support unconfirmed (docs example is UK only) | company name | needs registration and keys (verified); terms on storage not read | sign-up needed | signal only | **decision for Manuel** (sign-up), low priority |
| 13 | Sociaal Werk Nederland members (500+ organisations) | no public list found | - | robots.txt allows all | ask the association | high (welzijn core) | **decision for Manuel**: email, the list is not published (unverified; I fetched /leden: 404) |
| 14 | PSO-Nederland certified organisations ("more than 800") | national; Rotterdam subset unknown | search is JS, loaded 0 results for me | unknown | headless | like social enterprises, but many are large sociale werkbedrijven | **skip for now**, revisit |
| 15 | Fonds 1818 annual grantee tables (Den Haag 400-485 projects a year, Zuid-Holland 19 municipalities) | hundreds a year, mostly amateur art and small clubs | name, project, area, amount; no website | full list on fonds1818.nl not confirmed (only a local news site republished the 2024 table) | HTML per year, unverified | low (small associations) | **skip** |
| 16 | DOEN portfolio | 51 list pages; names only | name only on the list | robots allows all | detail page per org | low-medium | **skip** (cost per row too high) |
| 17 | Oranje Fonds, VSBfonds, Kansfonds, Skanfonds, Nationale Postcode Loterij | Oranje: grants only inside annual-report PDFs (unverified count); VSB: examples only; Kansfonds: ~40 project articles, no place field | - | - | PDF parsing | low | **skip** (no complete public lists) |
| 18 | TenderNed publications | award winners in sociaal domein tenders | name only | CC0 data, but the API needs a username and password requested by email (functioneelbeheer@tenderned.nl) | sign-up | low | **skip** |
| 19 | B Corp directory | Dutch companies are mostly commercial BVs | website yes | B Lab robots.txt carries content-signal restrictions | scraping | low (not nonprofit) | **skip** |
| 20 | Amsterdam subsidy register | restricted, licence "unknown" on data.overheid.nl, HTML register at subsidie-feiten.amsterdam.nl | no website | unclear | - | - | **skip** |
| 21 | NLvoorelkaar volunteer platform | organisations seeking volunteers | - | robots.txt: `Disallow: /zoeken`, crawl-delay 10; site returned 403 to my fetch | - | medium (volunteer sign-up is a visible workflow) | **skip**, would need their consent |
| 22 | Energy cooperatives (HIER) | about 700 nationally | - | - | no public dataset found | low (volunteer-run) | **skip** |
| 23 | Impact Hub Rotterdam, Social Impact Factory, Buy Social, Voor Goed | no public member lists found | - | - | - | - | **skip** (go through Voor Goed via row 2) |
| 24 | Germany / Belgium / EU registers | not checked | - | - | - | - | **defer**: the Dutch pool covers the target many times over; no verified source found for DE or BE, only a note that Flanders publishes open data under a "Sociale economie" theme |
| 25 | Zorg: DigiMV / jaarverantwoordingzorg.nl | zorg providers with annual accountability; the site says data is "partly public" with downloads | unknown fields | unknown | check once | unknown | **check next**, only the field list (is there an employee count?) |

Row 5 note: the Den Haag opendata API returned a single file link (an HTML download), not rows; the real register is the web
app at https://subsidieregister.denhaag.nl/. Treat Den Haag as unverified until the app's JSON is inspected.

## Notes per adopt-now source

### 1. Social Enterprise NL (rows exist)
Nothing to build. Order of use: 25 Delft/Rotterdam, then the 34 in the region, then the 391 rest of NL. At 50-67% this is
the best fit rate we have, and 450 rows is enough for roughly 225-300 fits on its own.

### 2. Rotterdam recognised social entrepreneurs
- The list: "Overzicht erkende sociaal ondernemers", April 2026, 5 pages, updated monthly. I read the copy attached to TenderNed
  publication 416011:
  https://www.tenderned.nl/papi/tenderned-rs-tns/v2/publicaties/416011/documenten/14102309/content
  Names grouped by sector (agrifood, bouw en infra, bedrijfsuitjes, ...), roughly 100, no websites. It is the leading list for
  Rotterdam, Schiedam, Vlaardingen, Westvoorne and Zuidplas (Werkcentrum Rijnmond is named as host in a search snippet; unverified).
- Its two companion platforms: https://www.goedinkopen010.nl (run by Voor Goed Agency, filter "SR-erkend: JA") and
  https://www.impactkaart.nl ("geographic overview of all impact enterprises in the region Rijnmond", filter label
  "Social Return Rijnmond"). Both are JS lists with no download; Impactkaart says missing entries go to impactkaart@voorgoedagency.nl.
- Build: parse the PDF text (pypdf worked), look each name up against Social Enterprise NL and the web to get the domain
  (one search per name, about 100 searches), skip names already in targets.yaml. Do not drive the two sites with a scraper
  before asking Voor Goed.
- Why it fits: these are social enterprises with orders, deliveries and bookings, the same shape as Lunch Bunch,
  Heilige Boontjes and Changemakers (batch 1 fits).

### 3. LRK childcare
- Download (CC0, refreshed Monday and Friday): https://www.landelijkregisterkinderopvang.nl/opendata/export_opendata_lrk.csv
  (11.9 MB; the "including history" file is export_opendata_lrk_2.csv). Dataset page:
  https://data.overheid.nl/dataset/gegevens-kinderopvanglocaties-lrk
- Columns I saw (semicolon separated): lrk_id, type_oko (KDV, BSO, PSZ, VGO), actuele_naam_oko, aantal_kindplaatsen,
  status, opvanglocatie_adres/postcode/woonplaats, naam_houder, kvk_nummer_houder, rechtsvorm_houder, houder_*,
  contact_persoon, contact_telefoon, contact_emailadres, contact_website, verantwoordelijke_gemeente.
- Filter I ran for the counts: type KDV/BSO/PSZ, group by houder KvK number, legal form Stichting, Vereniging or Coöperatie,
  location municipality from `verantwoordelijke_gemeente`. Size band: summed places 60-700 (my rough proxy for 15-100
  staff; calibrate on the first batch).
- Counts: 2,977 holders nationally; 377 nonprofit holders (345 with a website). Delft 11 and Rotterdam 20 nonprofit holders.
  The business-form holders (BV, eenmanszaak) are far more numerous (about 2,300) and are not our segment; the offer is for nonprofits and social enterprises.
- Cautions: (a) some holders are huge (Humankind about 21,000 places, Kibeo 11,000): the places column cuts them; (b) websites
  are free text with typos ("ww.kinderspeelzaal.nl", ".ml"); validate before use; (c) the register's email column must not be used as
  the contact address, because the kit's rule is an address printed on the organisation's own page; use the register only for the
  domain; (d) the host's robots.txt is `Disallow: /`, but the file is the official open-data download linked from data.overheid.nl,
  so fetch it once, cache it, and do not crawl the site. Flag this to Manuel anyway.
- Overlap: Dutch childcare foundations often hold ANBI status, so expect 30-50% duplicates with the ANBI rows; the kit's
  domain de-duplication handles it.
- New script would be `tools/sources/lrk.py` (about 80 lines, same pattern as `anbi.py`).

### 4. ANBI (already built)
- `python tools/sources/anbi.py --region` adds Rijnmond and Haaglanden (2,095 non-cultural rows, 549 cultural).
- Needed code change, small: drop rows with the cultural flag (`ingangsDatumCultuur` present, `eindDatumCultuur` absent) by
  default; batch 1 had six cultural venues and all six were rejected for "no visible workflow".
- Add a keyword priority on name for care, youth, welzijn, buurt, werk, wonen, schuld, ouderen, vluchteling, kinderopvang,
  jeugd, gezin. The three nonprofit fits (Maaszicht, Opwijs, Kinderparadijs) are all of this kind.
- Beyond the region: Amsterdam 3,055 rows, Utrecht 976, Leiden 354, Haarlem 343, Zoetermeer 158, Gouda 165, Dordrecht 189
  (counts include cultural flag rows, before duplicate removal).

### 5. Subsidy registers as enrichment
- Utrecht (CC0, monthly): https://data.overheid.nl/dataset/utrecht-subsidieregister-utrecht, file
  https://open.utrecht.nl/sites/default/files/open-data/subsidieregister-april-2026.xlsx. Columns: Datum Verlening, Aanvrager,
  Subsidiedoelstelling, Regelingnaam, Verleend bedrag, Aanvraagnummer, Boekjaar. The 2023, 2024 and 2025 files are linked on the
  dataset page. There is also a separate "Subsidieregister sociale basis" dataset. Verified by download: 970 grant rows, 286 applicants in the 2026 file.
- Den Haag (CC0 listing): https://data.overheid.nl/dataset/subidieregister-den-haag, which points to
  https://subsidieregister.denhaag.nl/ and an Opendatasoft file link. Re-check what the app returns before building.
  denhaag.nl returned 403 to my fetch.
- Vlaardingen (CC0): https://data.overheid.nl/dataset/subsidieregister-2026, csv.
- Method: copy `rotterdam_subsidies.py`: normalise names, match to ANBI and Social Enterprise NL rows in the same city, write
  the amount into `size_hint`. It adds no new organisations. It also hands the researcher the funding fact it lacked in batch 1.
- Other municipalities mostly publish PDF registers on their own site (Rijswijk and Amstelveen found); Delft and Leiden
  publish none I could find, and the Zuid-Holland province has no subsidy register dataset on data.overheid.nl.

## Segments outside the current three that fit the offer better

Evidence is from the 28 batch-1 cards (`tenants/180dc-delft-rotterdam/cards/`). What predicted a fit: an intake, enrolment,
order, sign-up or placement flow shown on the site (referral at Maaszicht, enrolment at Opwijs and Kinderparadijs, volunteer
sign-up at OASE, order handling at Lunch Bunch and Heilige Boontjes, sign-up flows at TeachBuddy and Socialdebt). What predicted a reject: cultural venues (6 of 6 rejected), tiny volunteer-run
organisations (Wijkbus Alexander), fund managers and investors (Impact First), consumer products with a social label (Plasklas,
Upstream Trophies), and housing corporations (0 of 3, "no named person").

| Segment | Why | Where to find them |
|---|---|---|
| Childcare, BSO and peuterspeelzaal foundations | enrolment, waiting list, fee letters, ouderportaal: Opwijs and Kinderparadijs fit on exactly that | LRK (row 3) |
| Youth care, welzijn, buurtwerk, mantelzorg | referral intake and case admin: Maaszicht fit | ANBI keyword priority, Sociaal Werk Nederland (ask), DigiMV (check) |
| Work-integration social enterprises (catering, logistics, recruitment, repair) | order and placement flows, own revenue; the 67% segment | Social Enterprise NL, Rotterdam SR list, Impactkaart |
| Volunteer-matching and programme foundations | OASE fit: sign-up form plus named funders | ANBI keywords; NLvoorelkaar would be ideal but is unclear on terms |
| SMEs in the 180DC network | I found no evidence for or against: nothing in the repo or cards. Likely the warmest source (alumni, past clients) but past clients cannot be named in emails (CLAUDE.md), and the offer is built for funded organisations. | ask Manuel for the branch's contact list |

Drop or deprioritise: cultural ANBIs, school boards (DUO lists them but I found no website or staff field, and the kit already
filters schools), energy cooperatives (volunteer-run), housing corporations beyond the few small Aedes members (Hef Wonen,
MaasWonen, Vidomes were suggested in the handoff; none is checked), national giants.

## Estimate: fits from the adopt-now sources

"Fits" = organisations the researcher would call FIT under the batch-1 rule, estimated from tiny samples; ranges are wide.
Net of duplicates between sources, minus rows already researched.

| Source | Rows usable | Fit rate used | Fits (range) |
|---|---|---|---|
| Social Enterprise NL, remaining | about 450 | 50% (45-67%) | 225 (200-300) |
| Rotterdam SR list and Impactkaart, net of SE NL overlap | about 60-100 | 50% | 30-50 |
| LRK nonprofits, Delft to Randstad, size-filtered, net of ANBI overlap | about 50-70 | 40% | 20-30 (NL-wide: another 40-60) |
| ANBI Rijnmond and Haaglanden, non-cultural, keyword-prioritised first 500 | 500 of 2,095 | 30% | 150 (100-200) |
| ANBI Delft/Rotterdam non-cultural not yet researched | about 960 | 25% | up to 240, but researching all is not needed |
| Subsidy enrichment | adds none | lifts ANBI rate | +10 points on matched rows |
| **Adopt-now total** | | | **about 700-900 fits available, of which the first 300 need about 650-750 organisations researched** |

Reading: 300 fits are reachable without Maps or job boards. The order that spends the fewest tokens is Social Enterprise NL,
then the Rotterdam SR list, then LRK, then ANBI by keyword. The constraint is research tokens (about 17k per organisation measured, 5k target in the tooling review), not leads.
At 5k tokens per organisation, 700 researched organisations is about 3.5M tokens.

## Decisions for Manuel (terms or sign-up)

1. Google Maps scraper or Places API: terms restrict scraping and storing; not needed to reach 300 fits. I recommend no.
2. JobSpy on LinkedIn and Indeed: LinkedIn forbids automated means (verified); do not run silently. A cleaner hiring signal is the
   "werken bij" page of an organisation we already research; no scraper needed.
3. Email Voor Goed Agency (impactkaart@voorgoedagency.nl) for the Impactkaart list and consent to use Goed Inkopen 010.
4. Email Sociaal Werk Nederland for a member list (not published as far as I found), and data@cbf.nl (unchanged from the handoff).
5. LRK robots.txt `Disallow: /` on the host of a CC0 download: OK to fetch the one file?
6. Register, sign-up or pay: TenderNed API login, Adzuna keys, KvK paid API: none recommended now.
