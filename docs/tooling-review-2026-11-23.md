# Tooling review and plan, 2026-11-23

Every repo and post suggested in the 2026-11-23 research chat, checked against this kit and against
the goal, with a verdict and an order of work. Repos were checked with `gh api` on 2026-11-23 (stars,
last push, licence); the two small "closest match" repos were read to confirm the features we borrow.

## The goal, as it stands now

- Manuel is joining the 180DC Delft & Rotterdam board. The branch needs clients; Manuel wants **two AI
  projects** for himself from this kit.
- A project runs **February to end of May 2027**, with **4-5 consultants at about 6 hours a week each**:
  roughly 400-500 team hours over ~17 weeks. Scope stays concise: one workflow, built and handed over.
- So the sales cycle is: first emails now, calls in December, nonprofits closed ~23 Dec to early
  January, scoping and signing in January, kickoff in February.
- The branch's other teams send generic mass email, about 200 a day, for normal consulting projects,
  from the same 180dc.org domain we send from.
- Constraint from Manuel: automate it, but without spending many tokens.

**Volume.** Two projects need roughly 300 good leads and 500-700 touches with follow-ups. Batch 1 fit
rate was 11 of 28 (39%), so 300 fits means ~770 organisations researched.

**What research costs today (measured).** Batch 1 used 474k subagent tokens for 28 organisations
(six Haiku calls, 74k-83k each): **about 17k tokens per organisation.** 770 organisations at that rate
is ~13M tokens. The two levers are fewer pages per organisation (phase 1, items 6-7) and fewer
organisations researched per fit (item 8). Target: ~5k tokens per organisation and a fit rate above
55%, which is ~550 organisations and under 3M tokens. The target is a guess until batch 2 measures it.

## What the kit already has (no change needed)

Claude drafts, code checks, a second agent reads, a person approves, a plain script sends with caps,
a weekday window, random 3-8 minute gaps and a 20/35/50/65 ramp. Replies are sorted into human,
opt-out, bounce and auto-reply; a suppression list and a registry block repeat contact; sending pauses
itself above 3% bounces (stricter than relance's 5%). The footer names where the address was found and
gives a one-word opt-out. 180dc.org has SPF, Google DKIM and a DMARC record (`p=none`, monitor only),
checked by DNS on 2026-11-23.

## Every link, checked, with a verdict

### Closest existing builds (use as references, don't adopt)

| Link | Checked | What it is | Verdict |
|---|---|---|---|
| [ParishSynthMind/ai-cold-outreach-instantly](https://github.com/ParishSynthMind/ai-cold-outreach-instantly) | exists, 0 stars, MIT, pushed 2026-11-17; README read | Python: Claude drafts strict JSON, code checks, `review.html` approval queue, pushes to Instantly (paid) with caps, List-Unsubscribe, reply labels, suppression | **Borrow two ideas**: required `consent_basis` per lead (item 2) and an HTML approval page (item 4). Instantly is a paid sending platform; we keep Gmail. |
| [MattiooFR/relance](https://github.com/MattiooFR/relance) | exists, 0 stars, AGPL-3.0, pushed 2026-10-01; README read | Self-hosted TypeScript + Postgres cold email from Google Workspace: per-mailbox caps, sending in the contact's timezone, one-click unsubscribe, pause above 5% bounces | **Borrow one idea**: the unsubscribe header (item 1). Timezone sending only matters outside CET. Its warm-up advice is a paid Smartlead affiliate link: skip. AGPL, so don't copy code. |

### Lead sources (free, self-hosted)

| Link | Checked | What it is | Verdict |
|---|---|---|---|
| [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) | 8.4k stars, MIT, Go, active | Scrapes Google Maps: name, address, phone, website, category, rating | **Decision for Manuel**: Google's terms forbid scraping Maps, and ticket 07's rule was to stop and ask about such sources. If yes: categories like welzijn, stichting, sociaal ondernemen in Rotterdam, Delft and the region, as a new `tools/sources/` script. |
| [speedyapply/JobSpy](https://github.com/speedyapply/JobSpy) | 4.8k stars, MIT, Python, active | Scrapes job boards (LinkedIn, Indeed, Glassdoor...) | **Decision for Manuel**: same terms problem (LinkedIn and Indeed forbid scraping). The idea is good: an organisation hiring an office or admin person is a sign of the pain we fix (build-spec decision 14, "signals later"). |
| [apify/apify-mcp-server](https://github.com/apify/apify-mcp-server) | 17.6k stars, MIT, official | Lets the agent run Apify scrapers directly | **Not now.** Apify would mostly run the same Maps or job-board scrapers (same terms question) and costs money; its tools also failed to load in this session. Revisit only if a free source fails. |

### Address checks

| Link | Checked | What it is | Verdict |
|---|---|---|---|
| [reacherhq/check-if-email-exists](https://github.com/reacherhq/check-if-email-exists) | 10.5k stars, MIT, Rust + HTTP backend | Checks a mailbox exists over SMTP without sending | **Later.** We only use printed addresses, so bounce risk is low. Many home ISPs block port 25, so SMTP checks from this PC may fail. Start with an MX check (item 3); add Reacher in Docker only if bounces show up. |

### Cheaper research and drafting

| Link | Checked | What it is | Verdict |
|---|---|---|---|
| [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | 87.7k stars, Apache-2.0, Python, active | Turns web pages (also JavaScript sites) into clean, short markdown locally | **Adopt (item 6).** A local `site_digest.py` gives the researcher ~2k tokens of clean text instead of fetches. It also fixes `firm_contacts.py`'s weakness on JavaScript sites. |
| [567-labs/instructor](https://github.com/567-labs/instructor) | 14.1k stars, MIT | Makes a model return fixed fields | **Take the idea, not the library (item 7).** It needs direct API calls; inside Claude Code the researcher already returns a fixed card. Code then builds the email from the template. Use the library only if we move to the API (item 12). |
| [huggingface/setfit](https://github.com/huggingface/setfit) + [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) | setfit 2.9k stars, Apache-2.0; model page rate-limited (429) on check, well known | Few-shot text classifier on a small multilingual model, runs free on the PC | **Later (item 8).** 28 verdicts are too few to train on. Train it at ~100 verdicts (after batch 4) on site digest + verdict, then research only the top-scored. |
| [vale-cli/vale](https://github.com/vale-cli/vale) | 6.4k stars, MIT, Go | Prose linter with custom style rules | **Optional.** `lint_email.py` already bans the words that matter. Add vale only if the checker keeps failing drafts for tone. |
| [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) | 55k stars, MIT, official | Recipes, incl. prompt caching and batch requests | **Reference for item 12**, only if research and tier-2 drafting move from Claude Code to the API. |

### Selling, offer, scoping

| Link | Checked | What it is | Verdict |
|---|---|---|---|
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 62k stars, MIT, active | Claude Code skills for copywriting, landing pages, CRO | **Use for tickets 02-04** (booking page, offer page, reply kit). Read each skill before installing: third-party skills are instructions Claude will follow. |
| [Jakeschincariol/founder-skill](https://github.com/Jakeschincariol/founder-skill) | 4.8k stars, MIT | Skills that stress-test a business idea | **Run once** on the offer ("Feb-May student team, one workflow, priced by funding"). Read first, same reason. |
| [rafiaauthoi/sow-generator](https://github.com/rafiaauthoi/sow-generator) | 1 star, **no licence**, last push 2026-06 | React SOW drafter with a review gate | **Don't reuse**: no licence means no right to copy. |
| [Aren-Garro/StatementOfWork](https://github.com/Aren-Garro/StatementOfWork) | 0 stars, MIT, last push 2026-03 | Markdown-to-SOW generator | **Skip.** A scoping template of our own (build-spec decision 3: audit, one automation, further work, handover, no maintenance) is a one-page markdown file. |

### Posts on X (not opened: X blocks automated reading; treat as anecdotes)

| Link | Claimed content | Use |
|---|---|---|
| [MichLieben/status/2051286894206656782](https://x.com/MichLieben/status/2051286894206656782) | Hiring and funding signals as triggers | Supports the signals idea (JobSpy decision) |
| [Kenny_GTM/status/2087562259686211589](https://x.com/Kenny_GTM/status/2087562259686211589) | Niche sources beat big databases | Supports registers over bought lists (ticket 07) |
| [kyle_e_walker/status/2085036757410558202](https://x.com/kyle_e_walker/status/2085036757410558202) | Small nonprofits' spreadsheet workflows suit a first automation | Supports the offer |
| [nifinet/status/2110124161880465693](https://x.com/nifinet/status/2110124161880465693) | Haiku read 912 leads and checked the 21 best for ~5 cents | Supports a cheap pre-filter (item 8) |
| [misat0x/status/2118325264119693788](https://x.com/misat0x/status/2118325264119693788) | 240 businesses scanned overnight under a $15 cap, 25 sourced openers, nothing sent | Supports "research cheap, never auto-send" |

The research chat's cost estimate ($1-2 per 100 leads with these tools, $5-10 today) was not measured;
use the token numbers above instead.

## The plan, in order

### Phase 0: before the first send (this week, small code changes, each with a self-test check)

1. **Unsubscribe header.** `gmail_draft.py draft` adds `List-Unsubscribe: <mailto:SENDER?subject=unsubscribe>`;
   `sync` treats a reply with subject "unsubscribe" as an opt-out. Check on one real send that Gmail
   keeps the header. (~1 h)
2. **Lawful basis on every contact.** `pipeline.py add-contact --basis`, default "legitimate interest:
   address published by the organisation at <source>, offer relevant to its work"; `send.py` refuses a
   contact without one. One page `docs/lawful-basis.md` for the legal team (the legitimate-interest
   reasoning, opt-out, retention). A named person's address is personal data; an info@ address mostly is not. (~1-2 h)
3. **MX check** in `add-contact`: refuse an address whose domain has no mail server. (~30 min)
4. **Approval page.** `send.py approvals --html` writes `state/approvals.html`: per draft the clean
   text, the card's facts with their source links, tier and arm. Approval itself stays a command.
   (~1-2 h; makes approving the first 30 emails quick)
5. **Inbox warm-up without a service.** Use the new inbox normally for a few days and let the ramp's
   20 a day be the warm-up. No warm-up networks.

### Phase 1: batches 2-4, cut tokens per organisation

6. **`tools/site_digest.py <domain>`** with crawl4ai: home, about, and one workflow page, trimmed to
   ~2k tokens, cached in `state/`. The researcher reads the digest instead of fetching. Measure tokens
   per organisation on batch 2 against the 17k baseline.
7. **Fields, not emails.** The researcher returns the card fields only. `tools/render_draft.py` fills the
   tier-2 template from them with the `[src:]` and `[claim:]` tags; the model writes at most the one
   sentence in their words. Lint and checker unchanged.
8. **Pre-filter.** Now: the batch-1 rule changes (drop cultural ANBIs, give the researcher the Rotterdam
   subsidy as a funding fact). At ~100 verdicts: a setfit scorer on the site digest, research only the top.

### Phase 2: more leads and signals (after Manuel's decisions)

9. Google Maps source with gosom, if Manuel accepts the terms question.
10. Hiring signal with JobSpy, same question.
11. Apify only if a free source fails.
12. Optional: move research and tier-2 drafting to a script on the Claude API (batch requests, prompt
    caching), so the bulk work runs without Claude Code and off Manuel's subscription. Needs an API key
    and a budget. Load the `claude-api` skill before building it.

### Phase 3: turn replies into signed projects (tickets 02-04 and scoping)

13. Booking page, offer page and reply kit with marketingskills; the offer stress-tested once with
    founder-skill; our own one-page scoping template for after the call.

## Decisions for Manuel

1. **Google Maps scraping** (gosom or Apify): Google's terms forbid it. Yes, or stay with registers?
2. **Job-board signals** (JobSpy): LinkedIn and Indeed forbid scraping. Yes, no, or only boards that allow it?
3. **Apify**: suggested no spend for now.
4. **Offer wording**: say "a student team working with you from February to May" in the email? It needs a
   new ledger claim (`BR-PROJECT-SHAPE`), since emails may only claim what the ledger holds.
5. **January wave**: `limits.yaml` stops sending on 22 Dec. Add 5-16 January for a February start?
6. **API pipeline** (item 12): worth an API key and a budget once batch 2 measures the token savings?
7. **Board**: the branch's ~200 mass emails a day come from the same 180dc.org domain. Propose the
   shared registry (ticket 11, brought forward), published addresses only, the opt-out footer and a cap
   per inbox for every sender?
