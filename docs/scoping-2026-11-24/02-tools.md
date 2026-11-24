# Tools scoping, 2026-11-24: every suggested tool checked, alternatives, recommended stack

Scope: the 15 repos in `docs/tooling-review-2026-11-23.md`, alternatives per stage, and the tools already
connected in Manuel's Claude setup. Stars, licence and last push were read with `gh api` on 2026-11-24.
READMEs were read for the repos where a verdict depends on them. Nothing was installed, run or paid for.
"Unverified" marks things I could not confirm from a primary page today.

## Bottom line first

1. **Leads are not the bottleneck; qualification cost is.** `targets.yaml` holds 1,796 candidates and the
   plan needs ~770 researched to get ~300 fits. More sources (Maps, job boards) add terms-of-service risk
   and little the registers do not already give. The money and tokens go into researching organisations
   that turn out to be REJECT (61% in batch 1).
2. **The biggest token lever is not a library, it is moving bulk research off Claude Code onto the API.**
   Prices (from the claude-api reference, cached 2026-11-03; re-check before committing): Claude Haiku 5.5
   is $0.10 per million input tokens and $0.50 per million output (prompts up to 100K), Message Batches are
   50% cheaper. 770 organisations at today's 17k tokens is ~13M input tokens: **about $1.30 plus ~$0.20 of
   output, before the batch discount.** At 5k tokens it is under $1. The campaign's whole research bill is
   therefore a few dollars, versus 13M tokens of Manuel's subscription. This is decision 6 in the tooling
   review, and it deserves to move from "later" to "decide this week". Caveat: the API route has no
   WebFetch, so it needs the local page digest (item 2 of the stack) to feed it.
3. **A cheap funnel in front of the model**: rules from register data, then a page digest, then a local
   embedding score, then the LLM only on the top slice. Each stage costs zero or near-zero tokens.
4. **Everything that brings in third-party contact data (Vibe Prospecting, Apollo, Clay, Lusha, ZoomInfo,
   Firecrawl people/company enrich) breaks CLAUDE.md rule 3 and the legitimate-interest text in
   `docs/lawful-basis.md`**, which both say addresses come only from the organisation's own pages. Use at
   most firmographics (size band, funding events), never addresses.
5. **The Telecommunicatiewet art. 11.7 question is still open in `docs/lawful-basis.md` (open point 3) and it
   gates everything.** A quick search today did not give me the current wording for e-mail to legal persons
   (the 2008 amendment extended the opt-in rule to them; the 2021 telemarketing change is about phone). I
   could not confirm either way. I am not a lawyer; the legal team's answer should come before send volume
   is raised. It matters more than any tool below.

---

## Stage 0: what exists (for context)

`firm_contacts.py` fetches with urllib, caches HTML 7 days in `data/cache/<host>/`, respects robots.txt,
follows team/contact/Impressum/careers links, extracts emails and a people digest by regex. The researcher
(Haiku, in Claude Code) then runs that, adds up to two WebFetch calls, and writes a ~150-word card. Where
the 17k tokens go is not measured per step; my reading is that most of it is the digest JSON plus two
WebFetch page bodies plus the agent's own overhead (system prompt, tool schemas, 3-6 turns). Measure this
once on batch 2 before optimising (log `usage` per step).

---

## Stage 1: lead sources

| Tool | Stars / licence / last push | How it plugs in | Effort | Cost | Gain | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| gosom/google-maps-scraper | 8.4k / MIT / 2026-11-22 | New `tools/sources/gmaps.py` calling its Docker image (`-email` is a visit to the business website, not Google). README: default mode opens listings; "fast mode" over HTTP needs `-geo`. Output name, category, address, phone, website. | 3-4 h | 0 (proxies optional) | Local small orgs with no register entry (buurthuis, welzijn). Overlap with ANBI/SE-NL is probably high. | Google ToS forbids automated scraping; Google may block the PC's IP; phone numbers and personal-looking names in output are extra personal data. A README sponsor list shows paid add-ons, ignore. | **Decision for Manuel; my lean: skip.** Try the OSM route first. |
| OpenStreetMap Overpass API (alternative, no repo to adopt; plain `urllib` call) | Overpass is open infrastructure; data ODbL | `tools/sources/osm.py`: query tags like `office=ngo`, `social_facility=*`, `amenity=community_centre` inside Delft/Rotterdam/region boxes; keep rows with a `website` tag. | 2-3 h | 0 | A legal Maps substitute; small yield, honest provenance | ODbL needs attribution only if we publish the data; Overpass has fair-use limits (one polite query per area). Coverage of `website` tags is patchy (unverified for NL nonprofits). | **Adopt later**, after batch 2, only if registers run dry |
| speedyapply/JobSpy | 4.8k / MIT / 2026-11-20 | `tools/sources/jobs.py`; README lists LinkedIn, Indeed, ZipRecruiter, Glassdoor, SEEK, Naukri, HelloWork, Bayt, BDJobs and a Google Jobs term; proxy support to "bypass blocking" | 3 h | 0, proxies if blocked | A hiring signal ("office coordinator", "vrijwilligerscoördinator") | LinkedIn/Indeed/Glassdoor ToS forbid scraping; the README's own proxy option is a sign of blocking; the ai-cold-outreach repo you borrowed from says "never scrape". | **Skip.** Use the free own-site signal below instead. |
| Own careers pages as the hiring signal (code only, extend `firm_contacts.py`) | n/a | `firm_contacts.py` already fetches `werken-bij`, `vacatures`, `careers` and has an INTERN regex. Add a second regex for admin/office/coordinator/volunteer-manager roles and write `hiring_admin: true` into the digest. | 1-2 h | 0 | Same signal as JobSpy at zero ToS risk and zero extra fetches; also feeds the pre-filter (stage 4) | Only sees what the org posts itself, fine | **Adopt now** (cheap, in-rule) |
| apify/apify-mcp-server | 17.6k / MIT / 2026-11-24 | Would run Apify Actors (Maps, job boards, contact finders) from a session. The MCP is connected here but its tools failed to load. | 1 h to debug | Pay per Actor run, token cost for every tool call result | Nothing the free sources cannot do | Same ToS issue as Maps/JobSpy, plus paid, plus returns large payloads into the model context | **Skip** |
| More Dutch registers (not tools, sources) | n/a | Candidates to check, each needs a ToS/robots check: CBF Erkend Goede Doelen list, Goede Doelen Nederland, Vereniging Kleine Kernen-style local networks, NLvoorElkaar / vrijwilligerswerk platforms (volunteer-intake pain), municipal "welzijnsinstellingen" lists. KvK Handelsregister API is paid per lookup (unverified price). | 2 h each | 0 mostly | Volunteer-heavy orgs are the best fit for the offer | Each page's terms must be read | **Later**, only if the funnel needs more than 1,796 |

Note on volume: 1,796 candidates at a 39% fit rate gives ~700 fits. Nobody needs 3x more raw leads. Better to improve the fit rate (stage 4).

---

## Stage 2: website to short text (the token lever)

Goal: ~2k tokens (about 7-8k characters of Dutch/English text) of clean, relevant text per organisation,
built by code, so the model never fetches.

| Tool | Stars / licence / last push | How it plugs in | Effort | Cost | Gain | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| **trafilatura** | 7.2k / Apache-2.0 / 2026-11-23 | Add `extract_text(html)` to `firm_contacts.py`, run on the HTML it already caches (no extra fetches). Per page: `trafilatura.extract(html, include_links=False, favor_precision=True, output_format="txt")`; fall back to its own jusText/readability fallbacks (built in). Then build the digest: pick pages by the existing LINK_WORDS (about, over-ons, aanmelden, intake, projecten, financiering, jaarverslag), rank paragraphs by keyword hits (formulier, aanmelden, intake, vrijwilliger, subsidie, fonds, jaarverslag, rapportage), drop duplicates, hard-cap at 8,000 characters. Writes `data/digest/<domain>.txt`. | 3-4 h incl. tests | 0 | Replaces the two WebFetch calls and most of the digest JSON; estimated 17k to ~4-6k tokens per org (estimate, measure on batch 2) | Pure-HTML only: JS-rendered sites return near-empty text. Detect by output < 300 chars and send to the fallback below. | **Adopt now. Preferred over crawl4ai as the default.** |
| unclecode/crawl4ai | 87.7k / Apache-2.0 / 2026-11-23 | Fallback only, for JS-rendered sites flagged by the trafilatura empty-output check. `pip install crawl4ai; crawl4ai-setup` pulls a Chromium via Playwright (hundreds of MB; works on Windows). Mode: `AsyncWebCrawler` + `CrawlerRunConfig` with a `PruningContentFilterLXML` (README example uses threshold 0.48, fixed) or `BM25ContentFilter(user_query="aanmelden intake subsidie financiering vrijwilliger")`, read `result.markdown.fit_markdown`; own `CacheMode.BYPASS` since we cache ourselves; do NOT use its LLM extraction strategy (that spends tokens). Use `arun_many` for batches. Cap to ~2k tokens by truncating `fit_markdown` at ~8k chars. Check that its robots.txt option is enabled (I did not verify the exact flag name; the kit's rule is to respect robots). | 4-6 h incl. Windows browser setup | 0 | Covers the 10-25% of sites that are JS-only (my guess; count in batch 2) | The README now leads with a paid cloud API ("Crawl4AI Cloud"); the local library stays Apache-2.0 but is large and fast-moving; stealth mode is in it and must stay off (would breach "own pages, politely") | **Adopt later, as the JS fallback only.** The review's "adopt (item 6)" is right on goal, wrong on default. |
| Playwright for Python | 15.1k / Apache-2.0 / 2026-11-23 | What crawl4ai wraps. If only ~10% of sites need a browser, 30 lines of Playwright + trafilatura on the rendered HTML is lighter than crawl4ai. | 2-3 h | 0 | Same as above, fewer dependencies | You maintain it | **Alternative to crawl4ai fallback**; pick one |
| Jina Reader (r.jina.ai) | 12.3k / Apache-2.0 / last push 2026-05-22 (stale repo) | Prepend `https://r.jina.ai/` to a URL, get markdown. Page fetched says 20 requests/min without a key, higher with a free key (the page contradicts itself: 100 or 500/min, so measure); tokens billed on output; "does not bypass anti-bot". | 1 h | Free tier, then paid per token | Handles JS pages with zero local setup | Every URL is sent to a third party (public org pages, no personal data, but it breaks "all processing local"); output has no filtering to 2k tokens; repo not updated for six months | **Skip** (trafilatura + fallback is local and free) |
| Mozilla Readability | 11.6k / Apache-2.0 / 2026-08-04 | JS library (Node). trafilatura already embeds readability-lxml as a fallback. | n/a | 0 | none beyond trafilatura | Node dependency | **Skip** |
| microsoft/markitdown | 198k per API (surprisingly high, treat the number with care) / MIT / 2026-11-07 | HTML/PDF/DOCX to markdown. Useful for PDFs (annual reports: jaarverslag, which are the funding evidence). | 1-2 h | 0 | PDF annual reports into text for the funding fact, instead of the model reading PDFs | PDFs can be huge; cap pages | **Later**, with a 5-page cap, for the funding fact |
| Firecrawl MCP (connected) | firecrawl-mcp-server 7.9k / MIT; the hosted service is the credit-metered part | `firecrawl_scrape` with a `query` format returns a short answer, `firecrawl_map` lists a site's URLs. Per the setup note, 0 credits until 14 Dec, and the campaign's last send is 22 Dec. | 0 | Credits | A tidy way to read JS sites from a session | Credits unavailable now; sends each page URL to Firecrawl; same-site reading complies with the rule if only own pages are scraped | **Skip for this campaign window.** Revisit after 14 Dec only for the JS fallback. |

---

## Stage 3: structured research output (card fields)

| Tool | Stars / licence / last push | How it plugs in | Effort | Cost | Gain | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| 567-labs/instructor | 14.1k / MIT / 2026-11-19 | Would wrap API calls in a Pydantic schema with retries. | 2 h | 0 | Reliable JSON card | Unneeded: the Anthropic SDK has structured outputs built in (`output_config.format` with `client.messages.parse()` per the claude-api reference), so a second layer adds a dependency. | **Skip** (use the SDK) |
| Anthropic SDK structured outputs + Message Batches | official | New `tools/research_api.py`: for each org, input = digest (stage 2) + the researcher rules as system prompt; output = card fields as JSON; submit 25-770 orgs as one batch (50% off, results within hours, keyed by `custom_id`). Haiku 5.5 for fit/reject; Sonnet 5.5 ($2/$10) only for tier-1 idea sentences, if wanted. Prompt caching is irrelevant at these prices and the system prompt is below the minimum cacheable length (512-4096 tokens depending on model). | 6-8 h incl. tests | ~$1-3 for the whole campaign | Moves bulk research off the subscription entirely; fits the "automate without spending many tokens" rule literally | Needs an API key and a spend limit set in the Console; org text goes to the API under commercial terms (public page text only, no emails stored in prompts if emails are filtered in code); rules in `researcher.md` must be ported; quality of Haiku 5.5 on Dutch pages is unmeasured: run 28 batch-1 orgs and compare verdicts to the existing cards first | **Adopt now (decision for Manuel: API key + budget)** |
| anthropics/claude-cookbooks | 55k / MIT / 2026-11-20 | Reference for batches and caching only. | 0 | 0 | Reading time saved | none | **Reference only** (the claude-api skill is enough) |
| Ollama + small local model | ollama 188k / MIT / 2026-11-24; llama.cpp 136k / MIT | `tools/prefilter_llm.py` asking a local 4B-8B model "does this page show a repetitive admin workflow? yes/no". | 3-4 h | 0 | Free tokens | CPU-only speed is poor (a few tokens/s; I do not know this PC's GPU); weak on Dutch nonprofit nuance; a worse prefilter than embeddings for the same effort | **Skip** unless embeddings fail |

---

## Stage 4: cheap pre-filter (fewer organisations researched per fit)

Current evidence: 28 verdicts (11 FIT, 17 REJECT). Review said that is too few for SetFit; I disagree on the
number but agree on the caution. SetFit's own README claims competitiveness with 8 labelled examples per
class; 11/17 is in that regime. The risk is not the count, it is that the verdict depends on facts (funding
shown, a reachable named person) that the page text only partly carries.

| Tool | Stars / licence / last push | How it plugs in | Effort | Cost | Gain | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| **Rule filter on register data** | n/a (code in `mark.py`/`_common.py`) | Drop before any page is fetched: cultural ANBIs, rows with no website, sports clubs, church bodies, national giants (rules already derived from the 17 REJECT reasons in batch 1). Add `reason` codes so each rejection is auditable. | 1-2 h | 0 | Possibly 20-30% fewer orgs fetched (guess) | Over-filtering; keep a log of drops and spot-check 20 | **Adopt now** |
| **Embeddings + logistic regression** (fastembed + scikit-learn) | fastembed 3.3k / Apache-2.0 / 2026-11-23 (ONNX, no PyTorch, lists multilingual-e5-small); scikit-learn 68k / BSD-3 | `tools/score.py`: embed each digest with `intfloat/multilingual-e5-small` via fastembed (CPU, ~100-200 MB model download from Hugging Face, one time), fit `LogisticRegression` on the labelled digests, write `fit_score` into targets. Use leave-one-out cross-validation on the 28 and only act on scores that beat a majority-class baseline. Prefix inputs with "query: " as the e5 model expects. | 3-4 h | 0 | If it works: research only the top 50-60% by score; cuts organisations researched by 40%+ (the target fit rate above 55% needs exactly this) | 28 labels give a wide error band; start by only dropping the bottom 30% of scores until batch 3 confirms; model page was rate-limited when the review checked it (download once, keep in `data/`) | **Adopt now** (the cheap version, ahead of SetFit) |
| huggingface/setfit | 2.9k / Apache-2.0 / 2026-11-17 | Replaces the logistic head with contrastive fine-tuning of the same e5 model. Needs `torch`, `datasets`, GPU-optional; training on CPU with ~30-100 examples is minutes. | 4-6 h | 0 | A few points of accuracy over plain LR, typically (unverified for this data) | Heavy dependencies on Windows; overfits on 28 rows | **Later**, at ~100 verdicts, only if LR plateaus |
| Bootstrapping labels cheaply | n/a | Label the first 150-200 digests with Haiku 5.5 in one batch (a one-line fit rubric: ~200 x 3k tokens = 0.6M tokens, about 6 cents), then Manuel or a teammate overrides disagreements on 30-40 of them. LLM labels are noisy; human spot-check the low-confidence ones. `cleanlab` (11.8k / Apache-2.0 / 2026-01) can flag likely label errors; optional. | 2 h | cents | Gets from 28 to 200 labels in a day | LLM labels teach the filter the LLM's biases; always validate against the 28 human-checked verdicts | **Adopt later**, after the score script exists |
| Label tooling (Argilla 5.2k, Label Studio 28.7k, doccano 10.8k) | Apache/MIT | UIs for labelling | n/a | n/a | n/a | Overkill: a CSV of domain, label | **Skip** |
| Keyword hit counts | n/a | The digest builder counts workflow words per language; a score under N drops the org. Free and transparent. | 1 h | 0 | Baseline to beat | none | **Adopt now**, as a column next to the embedding score |

---

## Stage 5: email address verification

The kit only uses addresses printed on the organisation's own site, so invalid mailboxes are rare; the
risk is bounces hurting a **shared** domain (180dc.org carries ~200 mass emails a day from other teams).

| Tool | Stars / licence / last push | How it plugs in | Effort | Cost | Gain | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| dnspython MX check (exists) | n/a | In `pipeline.py add-contact`, done. | done | 0 | Baseline | A/AAAA fallback for domains with no MX; check it is handled | **Keep** |
| JoshData/python-email-validator | 1.5k / Unlicense / 2026-11-20 | Syntax + IDN + MX in one call; replaces hand-rolled regex in `add-contact`. | 1 h | 0 | Catches `name@domain,nl`-style typos and obfuscated scraped forms ("(at)") | none | **Adopt now** (small) |
| reacherhq/check-if-email-exists | 10.5k / MIT (LICENSE.md read; the repo advertises a paid SaaS next to it) / 2026-11-20 | Docker backend, `POST /v0/check_email`. README says "outbound port 25 must be open" and recommends paid SOCKS proxies beyond tiny volumes. | 3-4 h | 0 self-hosted; paid proxies at scale | Detects dead mailboxes before sending | Home/university networks usually block port 25; large providers (Google Workspace, Microsoft 365) are poor targets for SMTP probing and may throttle or flag probing IPs (my general knowledge, not verified today); probing from the PC can itself hurt the PC's IP reputation | **Skip.** Bounce auto-pause at 3% (already in `send.py`) plus suppression covers it. Revisit only if bounces exceed ~3% in week 1. |
| AfterShip/email-verifier | 1.7k / MIT / 2026-11-23 | Go library, same SMTP probe. | 3 h | 0 | same | same port-25 problem | **Skip** |
| Catch-all detection | n/a | Needs SMTP probing; not worth it for printed addresses | n/a | n/a | n/a | n/a | **Skip** |

---

## Stage 6: deliverability

| Tool | Stars / licence / last push | How it plugs in | Effort | Cost | Gain | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| Google Postmaster Tools | service (free) | Verify `180dc.org` (DNS TXT). Shows domain reputation and spam rate for mail to Gmail users. Needs enough Gmail-bound volume to show data (unverified threshold, roughly hundreds a day), so the other teams' mass mail may supply it. | 0.5 h plus an IT admin for DNS | 0 | The one place a spam-rate rise shows up before replies dry up. Gmail's published bulk-sender line is a spam rate under 0.3% (from memory, verify). | Requires DNS access to the shared domain | **Adopt now** (ask whoever owns the DNS) |
| mail-tester.com | service (free tier, a few tests/day) | Send one finished first email to its address before launch; fix SPF/DKIM/headers/content flags. | 0.3 h | 0 | Catches header and content mistakes in the exact `gmail_draft.py` output including the List-Unsubscribe header | Score is a heuristic | **Adopt now**, once, and again after template changes |
| DMARC: move 180dc.org from p=none to p=quarantine | DNS change | Today `p=none` (monitor only). Add an `rua` reporting address and read reports for 2 weeks first. | 1 h plus IT | 0 | Protects the shared domain from spoofing; Google and Yahoo expect SPF, DKIM and DMARC for bulk senders | A mistake can block other teams' mail | **Decision for Manuel/board** (their domain, not ours) |
| DMARC report readers: domainaware/parsedmarc | 1.3k / Apache-2.0 / 2026-11-23; cry-inc/dmarc-report-viewer 377 / MIT / 2026-11-16 | Receive aggregate XML at a dedicated mailbox, parse into a view. parsedmarc wants Elasticsearch/Splunk; the Rust viewer is a single binary. Free hosted weekly digests exist too (unverified: Postmark's). | 2-3 h | 0 | Visibility on who sends as 180dc.org | Needs a mailbox and a host | **Later** (only if DMARC enforcement is accepted) |
| One-click unsubscribe (`List-Unsubscribe-Post`) | header | Already adding `List-Unsubscribe: <mailto:...>`. The one-click POST form needs an HTTPS endpoint. | 3 h | hosting | Required by Gmail/Yahoo only for senders above 5,000/day, so not for us | A web endpoint is more to run | **Skip** (mailto is enough at our volume) |
| Warm-up networks (Smartlead, Zapmail, Instantly) | paid | relance's README links affiliate versions | n/a | monthly fees | none that the ramp does not give | Fake-engagement warm-up violates mailbox-provider terms and the review already rejected it | **Skip** |

## Stage 7: sending and multiple inboxes

| Tool | Stars / licence / last push | How it plugs in | Effort | Cost | Gain | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| Gmail API sender (exists) | n/a | `send.py run`: ramp 20/35/50/65, 3-8 min gaps. The ramp totals ~850 sends to 22 Dec. | done | 0 | Enough capacity for the plan | Daily cap, not throughput, is the limit | **Keep** |
| Second sending inbox | n/a | Add `sender` per tenant (the tenant model already supports a copy) and split the cap. | 3-4 h | Workspace seat if not free | Spreads load; a failure mode isolator | On the same domain it shares domain reputation; only a separate subdomain/domain truly isolates, and a new domain starts cold. A new mailbox must be warmed, with five weeks left that is hard. | **Skip** for this window. **Decision for Manuel** whether to ask for a subdomain for the next intake. |
| MattiooFR/relance | 0 / AGPL-3.0 / 2026-10-01 | README read: plain text, per-mailbox caps, windows in contact timezone, one-click unsubscribe, 5% bounce pause; README sends you to paid Zapmail and Smartlead via affiliate links. | n/a | n/a | Ideas already taken (unsub header, pause) | AGPL: do not copy code; the kit's 3% pause is already stricter | **Reference only** |
| ParishSynthMind/ai-cold-outreach-instantly | 0 / MIT / 2026-11-17 | README read: human approval gate, `--accept-warnings`, suppression before push, `review.html`. Its own compliance section says "never scrape, never buy lists". Instantly Growth plan is $47/month per its README. | n/a | n/a | consent basis and approval HTML already implemented in the kit (REPO-MAP lists `--basis` and `approvals --html`) | A 0-star repo: do not adopt, nothing more to borrow | **Done. Reference only.** Paying for Instantly: skip. |
| listmonk (24k, AGPL-3.0), Mautic (11k, NOASSERTION), Mailtrain (5.7k, GPL-3.0), Postal (17k, MIT) | various | Newsletter/MTA tools | n/a | hosting | none | They are built for opted-in lists, not 1:1 cold outreach with approval; AGPL/GPL | **Skip** |

## Stage 8: reply classification and follow-up

`gmail_draft.py sync` already sorts replies into human, opt-out, bounce, auto-reply with rules. Expected replies
are on the order of 30-80 over the campaign (3-8% of ~1,000; a guess), so a classifier model is not warranted.
Sorting "interested / later / wrong person / referral" is a 3-line job per reply for Haiku 5.5 on the API
(under a cent per hundred replies) or by Manuel reading; draft replies still go to `drafts/reply-<org>.txt`
for Manuel (CLAUDE.md never rule). **Verdict: keep rules; optionally add an intent tag in `sync` via the API
script. Skip libraries.** `mailgun/talon` (1.4k, Apache-2.0) strips quoted text and signatures from replies; it
would help the intent tag; 1 h; **later**.

## Stage 9: registry / CRM

| Tool | Licence | How it plugs in | Verdict |
|---|---|---|---|
| monday.com (planned, ticket 11) | SaaS | The board is the shared registry keyed by domain. The monday MCP timed out connecting this session and needs a sign-in. | **Keep the plan**, only needed once a second sender exists |
| Twenty (61k, NOASSERTION), NocoDB (65.6k, NOASSERTION), Baserow (6.4k, NOASSERTION), EspoCRM (3.7k, AGPL-3.0), frappe/crm (4k, AGPL-3.0) | mixed | Self-hosted CRMs | **Skip**: hosting, accounts and licence reading for a 1,000-contact, single-team pipeline already in YAML |
| SQLite instead of YAML at scale | public domain | If `pipeline.yaml` grows past a few hundred orgs, tools reread the whole file | **Later**, only if a tool gets slow |

---

## Writing, offer and scoping tools

| Tool | Stars / licence / last push | How it plugs in | Effort | Cost | Gain | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| coreyhaines31/marketingskills | 62k / MIT / 2026-11-23 | README lists skills incl. cold-email, copywriting, prospecting, pricing, customer-research. Use for tickets 02-04 (booking page, offer page, reply kit) only. | 1-2 h per ticket | tokens only | Faster page copy | Its README carries a "Verified Partners" block of sponsored tool promotions: treat advice that names tools as ads. Its cold-email skill must not override CLAUDE.md writing rules (125 words, one question, no AI pitch). Read each skill before install. | **Adopt for tickets 02-04 only; never for the emails** |
| Jakeschincariol/founder-skill | 4.8k / MIT / 2026-10-07 | README: eleven skills, including a "consumer panel" of 100 simulated buyers. | 1 h | tokens | A critique of the offer | Simulated buyers are not evidence; the kit's own A/B arms (track record first vs two ideas first) are the real test | **Skip** (or one pass on offer wording if time allows) |
| rafiaauthoi/sow-generator | 1 / no licence / 2026-06-04 | n/a | n/a | n/a | n/a | No licence means no right to reuse | **Skip** |
| Aren-Garro/StatementOfWork | 0 / MIT / 2026-03-05 | n/a | n/a | n/a | n/a | Dormant, 0 stars | **Skip**; one-page own template (audit, one automation, handover, no maintenance) |
| vale-cli/vale | 6.4k / MIT / 2026-11-23 | Prose linting rules | 3 h | 0 | none: `lint_email.py` already enforces the rules; the kit writes English and German only and Vale's style packs are English-centric | extra binary | **Skip** |

---

## Already connected in Manuel's Claude setup

| Connected tool | What it would add | Conflicts with "only addresses printed on the organisation's own pages" (CLAUDE.md) | Conflicts with legitimate-interest text (`docs/lawful-basis.md`) | Verdict |
|---|---|---|---|---|
| Firecrawl MCP (scrape, map, crawl, search, agent, monitor) | Reading JS sites; `firecrawl_map` URL discovery; `query`-format scrape gives a short answer | No, if limited to scrape/map of the org's own domain. Yes for `people_company_enrich`, `people_company_search`, `firecrawl_agent`, `alexandria` providers: they return third-party contact data | Same split; the lawful-basis page promises "we don't buy lists, guess addresses" | 0 credits until 14 Dec, campaign ends 22 Dec. **Skip now; scrape/map only after 14 Dec as the JS fallback.** |
| Vibe Prospecting MCP (match-business, enrich-business, fetch-entities, fetch-businesses-events, enrich-prospects, estimate-cost, show-sample) | Firmographics (employee band, funding/hiring events), candidate lists | **Yes** for `enrich-prospects`/`match-prospects` (professional emails from a database). No for company-level fields | Pulling named people from a vendor database is personal data from a third party (GDPR Art. 14 notice duty; the footer's "where we found your address" would be a lie). Company-level data is fine | **Decision for Manuel.** Only company-level fields, after `estimate-cost` and `show-sample` on 10 Dutch nonprofits to see if coverage exists at all (I did not test; I expect thin coverage of stichtingen). |
| Apify MCP | Actors for Maps/jobs/contact finders | Contact-finder actors: yes | Same | Failed to load; **skip** |
| Playwright MCP, Chrome DevTools MCP | One-off look at a JS site from a session | No (own pages) | No | Fine for debugging; **not for batch** (page snapshots flood the context, which is exactly the token problem). Use Python Playwright inside a script instead. |
| Sales plugins: Apollo, Clay, Lusha, ZoomInfo, Crunchbase (need login) | Contact/firmographic databases and waterfall enrichment | **Yes** (emails not from the org's page) except Crunchbase for company facts | **Yes**: third-party sourced personal data, paid, and the lawful-basis page says it does not do this | **Skip.** Crunchbase has no nonprofit depth. Also the generic sales skills (`draft-outreach`, `lead-triage`, `account-research`) bypass the kit's ledger, lint and checker and burn tokens: do not use them for sending. |
| Gmail, Google Calendar, Drive, Linear, Composio MCPs | n/a for the pipeline | n/a | n/a | Not needed; the kit uses the Gmail API directly under its own caps, and an MCP send would bypass `send.py` |

---

## Recommended stack, in order (what to adopt, and why each moves leads or clients)

1. **Rule filter on register data plus the free hiring-signal regex** (stage 4 and stage 1; 2-3 h, zero
   cost). Why: removes known REJECT classes before any fetch, adds a fit signal for free. Moves **fit rate**.
2. **trafilatura inside `firm_contacts.py` to build a ~2k-token digest** (3-4 h, zero cost). Why: it is the
   precondition for every other token saving, works on the HTML already cached, no browser. Moves
   **tokens per org** from 17k to an estimated 4-6k.
3. **API research script with Message Batches and structured outputs on Haiku 5.5** (6-8 h, ~$1-3 for the
   campaign; needs Manuel's yes on an API key and a spend cap). Why: bulk research stops using the
   subscription at all, and a batch of 100 returns overnight. Moves **number of organisations researched**.
   Run the 28 batch-1 orgs first and compare to the existing cards.
4. **fastembed + multilingual-e5-small + logistic regression score** (3-4 h, zero cost), trained on the 28
   verdicts, then enlarged with cheap LLM labels. Why: research only the top slice; this is the "fit rate
   above 55%" lever. Moves **fit rate and leads per token**. SetFit only if this plateaus.
5. **Deliverability checks: mail-tester once, Google Postmaster Tools on 180dc.org, python-email-validator**
   (about 2 h total, zero cost). Why: a shared domain with ~200 mass emails a day is the single biggest risk
   to every email we send; these three show trouble early. Moves **inbox placement and replies**.
6. **crawl4ai or a thin Playwright script, JS fallback only** (4-6 h). Why: recovers the sites trafilatura
   cannot read, which would otherwise be dropped as "no visible workflow" and are exactly the tooling-poor
   organisations that benefit from automation. Moves **leads**, marginally.
7. **Own marketingskills pass for tickets 02-04** (booking page, offer page, reply kit; not the emails).
   Why: replies only become clients if the next step is clear. Moves **reply-to-call conversion**.
8. **OpenStreetMap Overpass source** (2-3 h), only if the funnel runs short of fits. Why: a lawful
   substitute for Google Maps. Moves **leads**.

Not recommended: Instantly or any paid sender, warm-up networks, Reacher, JobSpy, Apify, instructor, vale,
the self-hosted CRMs, sow-generator, StatementOfWork, any third-party contact database.

## Decisions for Manuel that this scoping adds or sharpens

1. **API key and a monthly cap** for item 3 (budget of roughly 5-10 dollars covers research, labelling and
   drafting for the whole campaign, by the prices above; confirm current prices before relying on it).
2. **Google Maps and job boards**: my lean is no for both; OSM and own-site signals replace them.
3. **Vibe Prospecting**: company-level only, after a free coverage test, never contact data.
4. **DNS on 180dc.org** (Postmaster verification, DMARC reporting address): who owns it, and will they
   cooperate before the first send?
5. **Telecommunicatiewet 11.7**: get the legal team's answer before volume is increased. It is open point 3
   on `docs/lawful-basis.md` and nothing in this file settles it.

## What I could not verify

- Whether Haiku 5.5 reads Dutch nonprofit pages as well as the batch-1 Haiku: test on batch-1 orgs.
- The share of target sites that need JS rendering: count empty trafilatura outputs on batch 2.
- Vibe Prospecting coverage of Dutch stichtingen; Jina's real free limits; the exact crawl4ai robots flag;
  Google Postmaster's minimum data threshold; this PC's GPU (matters only for local models).
- The current text of Telecommunicatiewet art. 11.7 for legal-person recipients.
