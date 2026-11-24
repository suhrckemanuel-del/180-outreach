We are building client outreach for 180DC Delft & Rotterdam. This session adds lead lists, so the
research step never runs dry. No API key: everything runs in Claude Code. Nothing is sent. Session S1 is
building `tools/enrich.py` in parallel. Don't touch `tools/enrich.py`, `tools/selftest.py` or
`tools/firm_contacts.py`.

Read first: `CLAUDE.md`, `docs/decisions-2026-11-25.md` (blank answer = skip that part),
`docs/scoping-2026-11-24/01-lead-sources.md` (notes per adopt-now source), `docs/sources.md`,
`tools/sources/_common.py`, `tools/sources/anbi.py` and `tools/sources/rotterdam_subsidies.py`. Don't read
`targets.yaml` whole; count with a short script.

## What to add (each a script in `tools/sources/`, plain HTTP, cached, de-duplicated by `_common.py`)

1. **Regional ANBI.** `anbi.py --region rijnmond haaglanden` (Rotterdam, Delft, Schiedam, Vlaardingen,
   Capelle, Barendrecht, Den Haag, Rijswijk, Zoetermeer, Leidschendam-Voorburg, Westland). If D1 is yes,
   only non-cultural rows. The scoping estimate is ~2,095 rows; report the real count.
2. **Rotterdam recognised social entrepreneurs** (`rotterdam_social.py`). The list has about 100 names and
   no websites. Match names to existing rows first. For the rest, find the website as described under
   "How to work". Record a website only if its own page names the organisation. Segment `social_enterprise`.
3. **LRK childcare** (`lrk.py`). Only if D2 is yes. One cached download of the official open-data csv. Keep
   nonprofit legal forms (stichting, vereniging) with a website. Put places per location into `size_hint`.
   Delft/Rotterdam first, then national. If D1 is yes, segment `childcare`; otherwise `nonprofit`.
4. **Subsidy facts** for Utrecht (CC0 xlsx) and Den Haag (API), like `rotterdam_subsidies.py`. They add no
   rows, only `size_hint` funding facts on matching rows.
5. If D1 is yes: add `childcare`, `youth_care`, `welzijn` to the segment choices in `pipeline.py add-org`
   and `tenant.yaml` `targets.segments`, and teach `mark.py --pick` a `--exclude` for cultural and housing
   rows. Self-test impact: tell S1's owner in your report. Don't edit `selftest.py` yourself; put your
   offline checks in `tools/sources/selftest_sources.py`.
6. If D6 is yes: draft three short English emails (CBF API access, Voor Goed Agency's Impactkaart list,
   Sociaal Werk Nederland's member list) into `tenants/180dc-delft-rotterdam/drafts/list-request-*.txt`.
   Who we are, what for, the opt-out promise. **Don't create Gmail drafts and don't send.**

Run order matters (the first source to claim a domain sets the segment): aedes, social_enterprise_nl,
rotterdam_social, lrk, anbi, then the subsidy scripts. Write that order into `docs/sources.md` and
`docs/REPO-MAP.md`.

## How to work (multi-agent, token-lean)

**Use a workflow**, at most 5 agents:
- **Builders (Sonnet, 1 per script, up to 3 in parallel):** each writes one script and its offline
  checks in `selftest_sources.py`, and returns the file paths and a row count from one live run.
- **Name-to-website matcher (Haiku, 1 call per 25 names):** for the Rotterdam names not matched in code.
  One WebSearch each, at most 3 results. Accept a site only if its own page names the organisation, and
  return `name | url | the page line that names it` or `name | none`.
- **Reviewer (Haiku, 1):** reads every new script. Checks that robots.txt and terms are respected, nothing
  is scraped in bulk beyond the official download or API, rows are de-duplicated against `targets.yaml`,
  pipeline and suppression, and each row keeps its source.

Then run each script for real and `python tools/sources/selftest_sources.py` (0 failed).

## Never in this session

`send.py approve` or `send.py run`, any Gmail draft or send, Google Maps, Apify, JobSpy, LinkedIn,
Indeed, an API key, editing `pipeline.yaml` by hand, any decision left blank. Commit only if D17 is yes;
never push.

## End with a short report

Rows added per source and segment, rows in Delft/Rotterdam vs region vs national, the new run order,
which decisions you skipped because they were blank, the draft emails' paths (if D6), subagent tokens,
and anything you need from me.
