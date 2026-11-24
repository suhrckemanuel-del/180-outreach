We are building client outreach for 180DC Delft & Rotterdam. This session builds the cheap research
front end: a code-only enrichment step and a score gate, so that a model only reads a short digest of the
organisations worth reading. No API key: everything runs in Claude Code. Nothing is sent.

Read first: `CLAUDE.md`, `docs/decisions-2026-11-25.md` (blank answer = skip that part),
`docs/scoping-2026-11-24/00-plan.md` (items A1, A2, A4), `docs/scoping-2026-11-24/03-enrichment.md`
sections 5-7, `docs/scoping-2026-11-24/02-tools.md` stage 2, and `tools/firm_contacts.py`. For the port,
read `C:\Users\User\Desktop\BDR-pipeline\app\services\email_finder.py` and its test. Run
`python tools/selftest.py` once (it should say 75 passed).

## What to build

1. **`tools/enrich.py <domain> [--json]`** (0 model tokens, plain HTTP, cached in `state/sources/` like
   `firm_contacts.py`). Per organisation:
   - GET `/`, `robots.txt` (obey it) and `sitemap.xml`.
   - Pick up to 8 pages by URL words: contact, over-ons/about, team/bestuur/organisatie,
     vacatures/werken-bij, anbi/jaarverslag, partners/financiering/fondsen, plus 1-2 workflow pages
     (aanmelden, inschrijven, intake, verwijzen, vrijwilliger, bestellen, offerte).
   - Turn each page into text with trafilatura (add it to `requirements.txt`).
   - Extract, each value with its page URL:
     - every on-domain email (decode `[at]`/`(at)`), and the name printed in the same block, if any
     - forms and their field labels
     - named funders, and staff hints (FTE, medewerkers, vrijwilligers)
     - vacancy titles, flagging admin/office/planning/data/AI/automation/digitalisering roles
     - words that signal pain: werkdruk, administratieve last, wachtlijst, handmatig, Excel, digitalisering, AI
     - the language
   - Output a **facts record** (YAML) and a **digest**: at most ~600 words, 5 fact lines plus the 3 best
     passages, every line with its URL.
   - Pages that come back empty because they need JavaScript are marked `js_needed`. No browser in this
     session.
2. **Score gate, `tools/enrich.py score`:** integer points from the facts record, using the 12 signals in
   `03-enrichment.md` section 6, with a gate (skip) for: no on-domain address, site down, registry-blocked,
   suppressed. If D1 is yes, cultural names score -3 and housing associations -2.
   - **Calibrate on the 28 batch-1 organisations.** The verdicts are in `tenants/180dc-delft-rotterdam/cards/`.
     All 11 fits must clear the threshold. Report how many of the 17 rejects it would have skipped.
     Change weights only to meet that, and write the final weights and the result into a comment block at
     the top of the score code.
3. **Address checks, ported from BDR-pipeline's `email_finder.py`:** role-address detection and the MX
   logic. **Drop its pattern guessing entirely.** `pipeline.py add-contact` already does MX; reuse
   `pipeline.mx_problem`, don't duplicate it. Add: prefer a printed functional address that matches the
   workflow (aanmelden@, administratie@) over info@, as a suggestion in the facts record.
4. **`tools/enrich.py batch --pick N [--segment ...]`:** runs enrich + score over the next `status: new`
   rows of `targets.yaml` (by `mark.py`'s rule) and prints a ranked table. It writes the facts and digests
   to `state/enrich/` and changes nothing in `targets.yaml` or `pipeline.yaml`.

## How to work (multi-agent, token-lean)

You write the code yourself. **Use a workflow** only for verification, at most 4 agents, Haiku unless a
step needs judgement:
- **Fetch-check agents (Haiku, 2):** each takes 14 of the 28 batch-1 domains. Run `enrich.py <domain>`
  and compare the facts record with the card: are the card's workflow page, funder and email in the
  facts? Return one line per domain: found / missed + what.
- **Adversarial reviewer (Sonnet, 1):** reads `enrich.py` and the diff. Hunts for: any path that could
  build or guess an address, robots.txt ignored, a fact without a URL, unbounded crawling, a cache that
  never expires. Returns findings only.

Fix what they find, then add self-test checks (stubbed HTTP, no network): extraction from a fixture page,
`[at]` decoding, off-domain addresses skipped, score of a fixture, gate on no address, no guessing path.
`python tools/selftest.py` must end with 0 failed.

Then a live dry run: `python tools/enrich.py batch --pick 30 --segment social_enterprise` and report the
ranked table, the share of `js_needed` pages and the time taken.

## Never in this session

`send.py approve` or `send.py run`, any Gmail send, guessing or building an address, LinkedIn or Google
Maps, an API key, editing `pipeline.yaml` or `targets.yaml` by hand, any decision left blank in the
decisions file. Commit only if D17 is yes (never `private/`, `drafts/`, `state/`, `data/`); never push.

## End with a short report

What was built (files), the self-test count before and after, the calibration result (11/11 fits kept,
N/17 rejects skipped, threshold), the dry run's table and `js_needed` share, what the verification agents
found and what you fixed, subagent tokens, and anything you need from me.
