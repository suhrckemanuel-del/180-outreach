# enrich.py: site facts and the score gate

One organisation's own website in, a facts record and a ~600-word digest out, plus a score that decides
whether the organisation is worth a model's time. Zero LLM tokens, standard library plus `PyYAML` and
`trafilatura`.

## What it does

`python tools/enrich.py <domain>` reads:

- `robots.txt` (an unreachable robots.txt means nothing is fetched; a disallowed page is never requested),
- the homepage, `sitemap.xml` (one level of a sitemap index, at most two extra files),
- up to 8 more pages chosen by words in the URL or the anchor text: contact, about/over-ons, team/bestuur,
  vacatures, ANBI/jaarverslag, partners/fondsen, and aanmelden/intake/inschrijv/offerte.

Two of those 8 slots are reserved before the rest are chosen: the best partners/fondsen page and the best
team/contact page. Without that, a site with many matching pages pushed out the funders list and the team
addresses.

From each page it extracts, and keeps with the URL it came from: printed on-domain addresses (mailto or
text, `[at]` decoded, never guessed), the name printed beside an address, forms with their field labels,
named funders and subsidy phrases, staff counts, vacancies, pain words, workflow words in the navigation,
portal/login words and ticket words.

Writes `tenants/<t>/state/enrich/<domain>.facts.yaml` and `<domain>.digest.md`. `state/` is gitignored and
the tool never touches `targets.yaml` or `pipeline.yaml`.

Request budget: 16 per organisation (robots, sitemaps, homepage, pages), one request at a time, 0.4 s apart,
pages cached for 7 days in `state/sources/enrich/`. A failed fetch is not cached.

## How to run

```
python tools/enrich.py voorbeeld.nl            # facts + digest, printed
python tools/enrich.py voorbeeld.nl --json     # the facts record as JSON
python tools/enrich.py score voorbeeld.nl      # score from the saved record
python tools/enrich.py calibrate --cached       # score the batch-1 cards, report recall on the fits
python tools/enrich.py batch --pick 25          # enrich + score the next 25 'new' rows
```

The self-test covers the tool offline: `python tools/selftest.py`.

## How the score is calibrated

Twelve signals from `docs/scoping-2026-11-24/03-enrichment.md` §6, with the weights in `W` and
`THRESHOLD = 3` in `tools/enrich.py`:

| Signal | Points |
|---|---|
| segment is `social_enterprise` | +3 |
| a workflow form (3+ fields beyond name/email/message) or aanmelden/inschrijven/intake in the nav | +3 |
| portal / login / dashboard | +2 |
| a named funder, or a Rotterdam subsidy of 50k-1M in `size_hint` | +2 |
| an admin/data/AI vacancy on the organisation's own site | +2 |
| a person's name beside a printed address | +1 |
| social/care/youth/education words | +1 |
| staff about 8-100 (only from about/team pages) | +1 |
| staff above ~150 | -3 |
| a newsletter form or a ticket shop and nothing else | -2 |
| cultural name (only when D1 is yes) | -3 |
| housing association (only when D1 is yes) | -2 |

Before scoring, `gate()` skips: site down, no on-domain address, blocked by the registry, suppressed
domain or address, no mail server. A skip never reaches the model whatever the points.

Measured on the 28 batch-1 cards (`calibrate`, threshold 3): 11/11 fits clear it; 7/17 rejects would be
skipped (9/17 with D1). Two code choices were needed, not weight changes: a plain contact form is not a
workflow form, and an address printed on a sister TLD of the same name counts as on-domain. The rejects
that still pass have a form or a funder but no workflow a person would call repetitive, so the model
verdict stays the judge; the gate only removes the clear misses. Re-fit the weights with logistic
regression after ~100 model verdicts (doc §6).

## Known limits

- **Staff counts** are kept only from pages about the organisation itself (about / team / over-ons /
  wie-zijn-wij / organisatie). A "500 medewerkers" line on a partners or klanten page is the partner's
  size, so it is ignored. A figure in an image, a PDF or a JavaScript-rendered block is missed.
- **Addresses** must be printed on the organisation's own domain (or the same name on another TLD). There
  is no guessing and no third-party lookup, by design.
- **JavaScript sites**: when a page's extracted text is tiny but the HTML is large, the URL is listed under
  `js_needed` in the facts record. The digest then carries little for that page and the score may be low.
- **Page selection** is a heuristic, not a crawl: sitemap plus homepage links, at most 8 pages, two of them
  reserved as above. A page linked only from a subpage is not found.
- **No PDFs** (annual reports, jaarrekeningen) are read, and no phone numbers are extracted; `calls.py`
  looks for a printed number in the dossier instead.
- **Digest** is capped near 600 words, so a very long page can be truncated: the three best passages are
  chosen by workflow, pain and funder words.
- `calibrate --cached` needs saved facts; without it the tool re-fetches (respecting robots and the cache).
