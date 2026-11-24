# 05. Capacity, funnel, testing and tailoring at scale

Written 2026-11-24. Model only: no limit, ramp or tenant file was changed. Every number is marked
**[fact]** (read from the repo or a cited page), **[calc]** (arithmetic or simulation from stated
inputs) or **[assumption]** (a guess, to be replaced by measurement). The small scripts behind the
tables were run in a scratch folder, not in the repo.

## 0. Headline

- The current ramp allows **850 emails** from a 25 Nov first send to 22 Dec **[calc]**: 444 first emails to new organisations, 290 follow-ups, 116 chain emails to a second person. That is not the "about 1,000" in `limits.yaml`; that figure assumed a Monday 23 Nov start (980 **[calc]**).
- On the base funnel assumptions that is **about 0.8 signed projects, with a ~19% chance of 2 or more**. Two projects needs roughly 3x the volume or a better reply-to-signed rate. The spread between pessimistic and optimistic is 50x, because call-to-signed has no benchmark at all.
- Week 1 is bottlenecked by **leads, not sending**: 100 first emails are needed in the first five sending days and the repo holds 11 fit organisations.
- The A/B test cannot answer 2% vs 4% at this volume (power ~23%). It can only catch a gap like 4% vs 12%.

## 1. Capacity

### 1.1 How the ramp really counts **[fact, `tools/send.py` `daily_cap`]**

Weeks are blocks of 7 calendar days from the first real send (`(today - first).days // 7`). The cap applies on weekdays and counts every email (first, follow-up, chain). The last value (65) holds. An unused day is not carried over. `last_send_date: 2026-12-22` is the only thing that stops January sending; the ramp would continue at 65 (the code does not re-ramp after a gap).

Send window 08:30-16:30 with 3-8 minute random gaps = 480 min / 5.5 min mean = **about 87 emails a day maximum per inbox [calc]**, so 65 fits.

### 1.2 Totals by option

Simulation rules **[assumption]**: a follow-up (day 7) for 93% of organisations (the rest replied, opted out or bounced); a chain email to a second person (4 days after the follow-up) for half of those (a second published person exists at half the organisations); priority follow-up, then chain, then new first emails (the order `outreach_due.py` uses). Expected values, not random draws. The second inbox starts Mon 30 Nov and the third Mon 7 Dec, each on its own 20/35/50/65 ramp from its own first send. The January wave is 5-16 Jan (10 weekdays), all inboxes at 65.

| Option | Total emails | New organisations first-emailed | Follow-ups | Chain emails | Follow-ups still pending at the end |
|---|---|---|---|---|---|
| 1 inbox, 25 Nov-22 Dec (today's plan) | **850** | **444** | 290 | 116 | 122 (28% of those due) |
| 1 inbox if it had started Mon 23 Nov | 980 | 479 | 357 | 144 | 88 |
| 1 inbox + January wave | 1,435 | 715 | 513 | 206 | 152 |
| 2 inboxes | 1,505 | 828 | 481 | 196 | 289 |
| 3 inboxes | 1,880 | 1,033 | 605 | 243 | 356 |
| 2 inboxes + January wave | 2,675 | 1,346 | 944 | 385 | 309 |
| 3 inboxes + January wave | 3,635 | 1,855 | 1,299 | 480 | 426 |

Week by week for the current plan **[calc]**:

| Ramp week | Dates | Cap/day | Emails | New first emails | Follow-ups | Chain |
|---|---|---|---|---|---|---|
| 1 | 25 Nov-1 Dec | 20 | 100 | 100 | 0 | 0 |
| 2 | 2-8 Dec | 35 | 175 | 54 | 93 | 28 |
| 3 | 9-15 Dec | 50 | 250 | 158 | 50 | 41 |
| 4 | 16-22 Dec | 65 | 325 | 131 | 147 | 46 |

Follow-ups take about 48% of sends from week 2 on, so new-organisation volume dips in week 2 and the final week.

### 1.3 What the other options need (none is free)

- **January wave.** Needs only a `limits.yaml` change (tooling-review decision 5). Timing risk: a first email on 5 Jan gets its reply around 12-19 Jan and a call late January; signing before a February kickoff is tight. Best use: send the follow-ups still pending from 15-22 Dec (122) plus first emails only on 5-9 Jan. The 23 Dec-4 Jan stretch is quiet for nonprofits.
- **Second or third inbox from another 180DC member.** `tenant.yaml` has one `sender`, `send.py` one Gmail login, the daily sync one mailbox, and the footer and signature name Manuel. So this is a code change (a sender per touch, one OAuth login per inbox, per-inbox caps and ramp, reply routing) plus a person who answers replies as themselves. A new inbox starts at 20/day, as modelled, and adds volume under the same domain reputation (section 5).
- **Sending subdomain.** Adds no capacity; it only separates reputation, and only partly (section 5). Google counts subdomains toward the same primary domain for the 5,000-a-day bulk threshold.

### 1.4 What is the bottleneck? Numbers

| Constraint | Demand (current plan) | Supply | Binding? |
|---|---|---|---|
| **Fit leads, week 1** | 100 first emails in 5 days | **11** fit organisations (`researched` in `targets.yaml`); 10 in the pipeline waiting for approval | **Binding now.** Each unsent day is lost cap. |
| **Research tokens** | 1,044 organisations researched (444 fits at a 42.5% blended fit) x 17k = **17.7M tokens**; week 1 alone 235 x 17k = 4.0M | Unknown plan limit; batch 1 used 474k for 28 organisations | Likely binding in Claude Code today; relaxed by items 6-7 or the API (section 4). |
| **Sending cap** | 850 emails | 850 | Binding by design from week 3 on. |
| **Fit leads, whole plan** | 444 | ~611 estimated in the whole pool of 1,769 candidates (462 social enterprise x 67% = 310; 1,308 nonprofit x 23% = 301; 26 housing x 0%) **[calc]** | Fine for 1 inbox. **Binding once volume passes ~600 organisations** (2 inboxes, or 1 inbox + January). Fit rates come from 12 and 13 organisations; 95% intervals are 39-86% (social enterprise) and 8-50% (nonprofit) **[calc, Wilson]**. |
| **Approvals** | Tier 1 (~150 first emails) + the first 30 of any tier: at most ~180, about 9 a day over 20 days, at ~1 minute each [assumption] | Manuel, 10 minutes each morning before 08:30 | Not binding on average, but a daily deadline: a missed morning wastes that day's cap. Front-loading tier 1 means ~20 a day in week 1. |
| **Manuel's call time** | ~4 calls by 22 Dec (base) | Plenty | No. Calls are scarce, not time-consuming. |

Order of binding: leads (week 1), research tokens (weeks 1-3), sending cap (weeks 3-4), then, if volume is raised, the size of the fit pool.

## 2. Funnel

### 2.1 Benchmarks and their limits

| Metric | Figure | Source and caveat |
|---|---|---|
| Reply rate per email sent, strict | 0.45% over 7.5M emails (2025) | [Belkins](https://belkins.io/blog/cold-email-response-rates). Net-new contacts only; nonprofits not broken out. "Over 1,200 appointments" from 7.5M emails is roughly 0.016% of emails **[calc]**. |
| Reply rate, sending-platform data | 3.4% average, top quarter 5.5%, top tenth 10%+ | [Instantly 2026 report](https://instantly.ai/cold-email-benchmark-report-2026), via secondary summaries. Vendor data; replies counted over a whole sequence, 58% from the first email and 42% from follow-ups (unverified). |
| Sequence reply rate | 4.5% over 31M emails (2025) | [Hunter](https://hunter.io/the-state-of-cold-email), via search summary. |
| Reply rate per unique contact | 2.09% over 2M+ emails | [Sales.co](https://sales.co/research/cold-email-statistics), via search summary. |
| Nonprofit cold email | 2-3.5% reply, 1-2% positive, 0.6-1.5% meetings; "small nonprofits under $1M": 4.5-7.5% reply, 2-4% meetings | [RevenueFlow](https://www.revenueflow.com/blog/nonprofit-cold-email-benchmarks). **Weak:** it names no study or sample size, and the author sells cold email. A prior, not evidence. |
| Positive replies | 1-2% of sends (median), top quartile 4-6% | [Full-Send](https://full-send.io/resources/reply-rate-benchmarks.html), [LevelUp Leads](https://levelupleads.io/blog/cold-email-benchmarks-2025-key-stats-every-marketer-should-know/), via search summaries. |
| Reply to discovery call; show rate | 30-50% of replies; 75%+ show | [Cold Outreach Agency](https://coldoutreachagency.com/consulting-firm-cold-email-proposal-conversion-rate/): stated as targets, not measurements. |
| Meeting to signed paid project | **No benchmark found** for a student consultancy selling a project to a nonprofit | Pure assumption below. Replace it after the first 5 calls. |

The spread (0.45% to 4.5%) is mostly different denominators and vendors measuring their own users, not a real market split. Almost every figure is vendor data.

### 2.2 Scenarios, per organisation over the whole sequence **[assumption, built from the ranges above]**

| Step | Floor (all low) | Base | Optimistic |
|---|---|---|---|
| Any human reply (including "no thanks") | 2% | 4% | 7% |
| Of replies, positive (open to a call) | 20% | 35% | 50% |
| Positive reply to call held (booked and showed) | 50% | 65% | 80% |
| Call held to **paid project signed** | 10% | 20% | 35% |
| **Calls held per organisation** | 0.20% | **0.91%** | 2.8% |
| **Signed per organisation** | 0.02% | **0.18%** | 0.98% |
| **Organisations per signed project** | ~5,000 | **~550** | ~100 |

Base calls per organisation (0.91%) sits inside RevenueFlow's 0.6-1.5% meetings range. The floor stacks four low values: read it as a worst case, not a forecast.

### 2.3 What it takes to sign 2, 5 and 10 projects **[calc]**

One organisation costs 2.4 emails if the full sequence runs (1 + 0.93 follow-up + 0.5 x 0.93 chain). Leads to research use a 39% blended fit (batch 1) or 67% (social enterprise only).

| Signed | Scenario | Organisations to contact | Emails | Calls held | Leads to research at 39% fit | At 67% fit | Working days at 65 a day |
|---|---|---|---|---|---|---|---|
| 2 | Base | 1,100 | 2,630 | 10 | 2,820 | 1,640 | 40 |
| 2 | Optimistic | 205 | 490 | 6 | 520 | 305 | 8 |
| 2 | Floor | 10,000 | 23,950 | 20 | not feasible | | |
| 5 | Base | 2,750 | 6,580 | 25 | 7,040 | 4,100 | 101 |
| 5 | Optimistic | 510 | 1,220 | 14 | 1,310 | 760 | 19 |
| 10 | Base | 5,500 | 13,160 | 50 | 14,090 | 8,200 | 202 |
| 10 | Optimistic | 1,020 | 2,440 | 29 | 2,620 | 1,520 | 38 |

On the base case even 2 signed projects needs about 1,100 organisations, more than the whole estimated fit pool of ~611, so base reaches 2 only with more reach (EU lists, Maps, referrals) or a better rate.

### 2.4 What each option expects **[calc, Poisson]**

Expected signed = new organisations x signed per organisation.

| Option | Organisations | Floor: signed / P(2+) | Base: signed / calls / P(1+) / P(2+) / P(3+) | Optimistic: signed / P(2+) |
|---|---|---|---|---|
| 1 inbox (today) | 444 | 0.09 / 0% | **0.81** / 4 / 55% / **19%** / 5% | 4.4 / 93% |
| 1 inbox + January wave | 715 | 0.14 / 1% | 1.30 / 6.5 / 73% / 37% / 14% | 7.0 / 99% |
| 2 inboxes | 828 | 0.17 / 1% | 1.51 / 7.5 / 78% / 44% / 19% | 8.1 / 100% |
| 2 inboxes + January wave | 1,346 | 0.27 / 3% | 2.45 / 12 / 91% / 70% / 44% | 13 / 100% |
| 3 inboxes + January wave | 1,855 | 0.37 / 5% | 3.38 / 17 / 97% / 85% / 66% | 18 / 100% |

Caveats: from 828 organisations upward the estimated fit pool (~611) is exceeded, and replies to January sends arrive too late for some February starts.

Sensitivity of the base 0.81 (signed scales linearly with each step): reply rate 4% to 6% gives 1.2; call-to-signed 20% to 30% gives 1.2; a second inbox gives 1.5 (less than 2x because it ramps from cold and loses follow-up time); the January wave gives 1.3. Fit rate and lead mix change cost, not signed per organisation.

## 3. Testing

### 3.1 What the A/B setup can and cannot tell

Arms alternate by draft order, so each gets half of 444 = **222 organisations** by 22 Dec (1 inbox). Replies are rare: at 4%, about 18 in total, ~9 per arm.

| True reply rates (A vs B) | Samples needed per arm (80% power, 5% two-sided) **[calc]** | Power at 222 per arm | Power at 350 per arm (1 inbox + January) |
|---|---|---|---|
| 2% vs 4% | **1,141** | 23% | 34% |
| 4% vs 8% | 552 | 43% | 61% |
| 4% vs 12% | 179 | 88% | 98% |

At 222 per arm the smallest gap detectable with 80% power is about **4% vs 11%** (or 2% vs 8%). A 2% vs 4% difference would be missed three times in four, and a "winner" picked from a non-significant gap is usually noise. The branch's rule (about 30-50 per arm, direction only) is right; at 50 per arm power is 31% even for 4% vs 12%.

Further limits:
- **Confounds.** Alternating by draft order is fine, but if one arm gets more social enterprises or more tier 1 by chance, that outweighs any copy effect. Alternate **within** segment x tier x language, not globally.
- **Replies lag.** Count only emails sent at least 14 days ago (7-day follow-up plus reaction time). Arms in the last two weeks are unreadable before the holiday.
- **Metric.** Use "any human reply" (not auto-reply, not opt-out), not "positive" or "signed": positive is 1-2% of sends and will not move. Keep `stats.py`'s `replied` definition fixed.
- **Tier 1 vs tier 2 is not an A/B** (different organisations, different effort).

### 3.2 What to test, in the order it can be seen

1. **Arm A vs B (track-record lead vs value-first lead).** The only contrast big enough to show at this volume. Read it as a direction, plus the reply text (do B replies name an idea; do A replies ask who you are?).
2. **Segment (social enterprise vs nonprofit vs housing).** Not a copy test; a lead-allocation fact. Fit already differs 67% vs 23%, reply rate probably differs too. Report reply rate by segment beside the arm every Sunday and put more volume where fit and reply are both high.
3. **Tier-2 guess vs verified fact.** Only testable by sending two versions of the same sentence, 100 each, with no result expected before Christmas. Use the quality gates in section 4.3 and the Sunday read instead.
4. **Subject line and send day or time: do not test.** Belkins has Wednesday and Thursday at 0.48% against 0.45% overall and 8 AM-12 PM at 0.54% ([Belkins](https://belkins.io/blog/cold-email-response-rates)); effects of 0.03-0.09 points need hundreds of thousands of emails. Pick one sensible subject and keep the 08:30-16:30 weekday window.

### 3.3 A simple stopping rule that does not fool you

A naive rule ("stop when one arm leads by 5 replies") **falsely stops 83% of the time** even with equal arms, over 40 replies **[calc, simulation]**. Do not use it.

Use this instead (it counts replies, since the arms send equally; Haybittle-Peto style, stopping only on a very strong result):

| Total replies so far (look at) | Stop and drop the loser if the loser has this many or fewer |
|---|---|
| 10 | 0 (10 to 0) |
| 15 | 2 (13 to 2) |
| 20 | 3 (17 to 3) |
| 25 | 5 (20 to 5) |
| 30 | 7 (23 to 7) |
| 40 | 11 (29 to 11) |

Each row is a two-sided binomial p below 0.01. Simulated **[calc]**: with equal arms it stops falsely in about 1.7% of runs within 40 replies; with one arm truly 3x (6% vs 2%) it stops, correctly, in 75% of runs (average 29 replies); with 2x (4% vs 2%) it stops in only 32% of runs; it almost never picks the wrong arm.

Honest consequence: the whole plan produces about 18 replies by 22 Dec, so this rule can fire only for a very large gap (for example 10 to 0, 13 to 2), or after the January wave (~29 replies). That is the correct answer: most differences will not be decidable. The rule exists to kill a clear loser, not to find a winner.

The existing template alarm (fewer than 2 human replies from the first 100 tier-2 emails) is sensible: at a true 4% it fires 9% of the time and at a true 2% it fires 40% of the time **[calc]**. It is a template-health alarm, not a test. The runbook's stop on any angry reply or spam complaint stays.

## 4. Tailoring at scale for few tokens

### 4.1 Tokens per first email

All figures are per **first email actually sent**. Today's researcher cost is measured (17k tokens per researched organisation, `docs/tooling-review-2026-11-23.md`); the rest are estimates.

| Design | Research per organisation | Fit rate | Research per sent email | Draft, lint, queue, check per email | Total per sent email | For 444 first emails |
|---|---|---|---|---|---|---|
| **Today** (Claude Code, researcher fetches pages) | 17k [fact] | 39% | 43.6k | ~7.5k [assumption: session overhead of add-org, add-contact, add-touch, drafting, checker] | **~51k** | **~22.6M** |
| Items 6 + 7 in Claude Code (site digest; researcher returns fields; code renders; model writes one sentence), target 5k | 5k [target, a guess until batch 2] | 39% | 12.8k | ~1.1k [assumption] | **~13.9k** | ~6.2M |
| Same, with SE-first mix and pre-filter (item 8) | 5k | 55% | 9.1k | ~1.1k | **~10.2k** | ~4.5M |
| **Claude API, batch + caching** (item 12) | ~3.95k tokens (below) | 42.5% | 9.3k | 1.7k | ~11k API tokens | ~4.9M API tokens, **a few dollars**, none from the Claude Code plan |

API request shapes **[assumption]**: research call = 1,200 cached prefix (instructions, schema, two examples) + 2,300 fresh (the ~2k-token digest from crawl4ai plus organisation fields) + 450 output (the JSON card); sentence call per fit organisation = 1,000 cached (style rules, ledger wording, template) + 600 fresh + 100 output. The model writes nothing else: code renders the template, the `[src:]` and `[claim:]` tags, the footer and the lint.

### 4.2 API cost, from Anthropic's price list

[Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing), read 2026-11-24, per million tokens. The Batch API is a 50% discount on input and output; cache reads cost 0.1x base input (0.05x on Sonnet 5.5); batch and caching discounts stack. [Batch docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing): most batches finish within an hour and at most 24 hours, up to 100,000 requests per batch, and cache hits inside a batch are **best effort**, so use the 1-hour cache.

| Model | Input | Output | Cache read | Batch input | Batch output |
|---|---|---|---|---|---|
| Haiku 5.5 (prompts up to 100k) | $0.10 | $0.50 | $0.01 | $0.05 | $0.25 |
| Haiku 4.5 | $1 | $5 | $0.10 | $0.50 | $2.50 |
| Sonnet 5.5 | $2 | $10 | $0.10 | $1 | $5 |

Cost of the whole current plan (1,045 researched organisations + 444 sentence calls, the shapes above) **[calc]**:

| Model | Live, with caching | Batch, with caching | Per researched organisation (batch) |
|---|---|---|---|
| Haiku 5.5 | $0.54 | **$0.27** | $0.00023 |
| Sonnet 5.5 | $10.66 | **$5.33** | $0.0046 |
| Haiku 4.5 | $5.41 | not needed (use 5.5) | |

Without caching it is $0.35 (Haiku 5.5 batch) or $6.94 (Sonnet 5.5 batch). Model cost is not the constraint. The real costs of the API route are (a) writing and testing the script, an API key and a budget (tooling-review decision 6), (b) fetching, which has to be crawl4ai locally (item 6), and (c) losing the agent's habit of opening a second page when the digest is thin: expect a lower fit rate or a "needs a second look" bucket. Claude 4.7 and later tokenizers produce about 30% more tokens for the same text (same pricing page); counts above are before that.

Suggested split: Haiku 5.5 for digest-to-card extraction (fields only, each with a source URL that code checks), Sonnet 5.5 for the one sentence and for tier 1. Check first by running both on the 28 batch-1 organisations against the 11 fit and 17 reject verdicts already decided by hand.

### 4.3 Checks that keep tier-2 emails from reading generic

The first six are code and cost no tokens:

1. **Fact is in the fetched page.** The quoted fact string appears verbatim in the digest, not only a URL in `[src:]`.
2. **Specificity score.** The fact sentence must contain at least one term that is rare across this week's cards (TF-IDF) and occurs in the organisation's own digest. A sentence that could go to any other organisation in the batch fails.
3. **Duplicate check.** No two rendered emails in a batch share the fact sentence or the two workflows (shingle overlap above 60% fails). This also catches the model reusing a sentence.
4. **Their words.** The workflow named occurs on their page by string match; otherwise it comes from the sector list and must be hedged ("often", "typically").
5. **Guess marker.** Tier-2 guess sentences carry a hedge word; verified facts do not, so a guess is never presented as something we saw.
6. **Banned words and length** (existing `lint_email.py`).
7. **Sunday read.** Five random sent tier-2 emails (runbook), one question: "would a person there think this was written for them?". One fail tightens the template.
8. **Human gate** on all tier 1 and the first 30 first emails (existing).

## 5. Deliverability: more volume from 180dc.org next to the mass emails

### 5.1 What Google says **[fact]**

[Gmail email sender guidelines](https://support.google.com/mail/answer/81126) and the [sender guidelines FAQ](https://support.google.com/mail/answer/14229414):
- All senders: SPF or DKIM, TLS, valid DNS, and a Postmaster Tools spam rate **below 0.3%**; the guidance is to stay **below 0.10%** and never reach 0.30%.
- Bulk senders (close to 5,000 messages a day to personal Gmail accounts): SPF, DKIM and DMARC (policy may be `none`), domain alignment, and **one-click unsubscribe** for marketing and subscribed messages (`List-Unsubscribe-Post: List-Unsubscribe=One-Click` plus an HTTPS `List-Unsubscribe`).
- "Messages sent from the same primary domain count toward the 5,000 limit", including subdomains (the FAQ's example adds 2,500 from the domain and 2,500 from a subdomain). **Bulk sender status never expires** once assigned.
- The spam rate is user-reported and calculated daily; no minimum volume is stated. Unwanted or unsolicited mail is named as something to avoid.

### 5.2 Risks for this plan

| Risk | Why here | Numbers |
|---|---|---|
| **Shared reputation** | Every 180dc.org sender shares one domain reputation. The ~200 generic mass emails a day sit in the same Postmaster figure; our complaints hurt them and theirs hurt us. | If every message went to a personal Gmail account, one complaint in a ~265-message day (200 + 65) is 0.38%, above the 0.3% ceiling; 0.10% is about 1 complaint per 1,000. **[calc, worst case; many recipients use other providers.]** |
| **Unknown bulk status** | Nothing in the repo says whether 180dc.org worldwide already crosses 5,000 a day to Gmail. If it does, the status is permanent. | Then one-click applies. Plan item 1 adds a `mailto:` unsubscribe header only; Google's page specifies an HTTPS URL for one-click. |
| **Cold start** | A new inbox has no history. | The 20/35/50/65 ramp is the warm-up; keep it. |
| **No visibility** | The repo mentions no Postmaster Tools or DMARC reports; DMARC is `p=none`. | A reputation drop would be noticed only when replies stop. |
| **Unsolicited mail** | Cold mail is the category Google warns about. | The opt-out footer, "no" handling and the 3% bounce stop already help. |

### 5.3 Cheap fixes, in order

1. **Verify 180dc.org in [Google Postmaster Tools](https://postmaster.google.com/)** (a DNS TXT record; needs whoever holds 180DC's DNS, probably global IT). Watch spam rate and domain reputation daily for the first two weeks. It may show nothing at low volume (unverified).
2. **Add a DMARC reporting address (`rua=`)** to the existing `p=none` record to see who sends as 180dc.org. Do not tighten the policy while other teams send through other tools.
3. **Spam-rate stop rule in the kit:** pause on any complaint; pause the whole kit if Postmaster shows spam above 0.10% or reputation falling for two days. A manual check at first.
4. **Keep the volume ramp and weekday window.** Do not start a second inbox until the first week's Postmaster numbers are clean.
5. **One-click unsubscribe over HTTPS** if bulk status is true or likely (a tiny hosted endpoint), since `mailto:` alone is not one-click per Google.
6. **A sending subdomain** (for example `outreach.180dc.org`) separates reputation only partly: sources disagree on how much (vendor blogs, none from Google: [Suped](https://www.suped.com/knowledge/email-deliverability/sender-reputation/how-do-subdomain-spam-complaints-affect-root-domain-reputation-in-google-postmaster-tools), [ColdScore](https://coldscore.app/blog/subdomain-reputation-myth)), and Google adds it to the same primary-domain bulk total. A separate registered domain isolates fully but changes the brand and costs money. Neither is needed at 65 a day; consider the subdomain only if Postmaster shows the main domain slipping.
7. **Ask the branch to share the registry** (tooling-review decision 7) so mass senders and this kit never hit the same organisation.

## 6. The five actions that would raise signed projects the most

Ranked by expected effect, with the model's numbers.

1. **Build the lead stock before 25 Nov and cut the cost per lead.** Week 1 needs 100 first emails and there are 11 fit leads; unused sending days are lost, and 235 organisations must be researched for week 1 (4.0M tokens at 17k). Research social enterprises first (67% fit, 462 in the pool, about 310 fits), do items 6 and 7 so 5k tokens per organisation is real, and move bulk research to the API in batches if the token budget is the limit ($0.27 to $5 for the whole plan). Without this the cap goes unused and nothing below matters.
2. **Add the January wave, used for pending follow-ups plus first emails on 5-9 Jan.** No code change. It adds 585 emails (+69%), lifts the base expectation from 0.81 to 1.30 signed and P(2+) from 19% to 37%, and clears the 122 follow-ups left from the 15-22 Dec tail. Manuel's decision; replies after mid-January may miss a February start.
3. **A second inbox from another 180DC member, once Postmaster Tools is watching.** The largest volume lever: +655 emails, base 0.81 to 1.51 signed alone and 2.45 with the January wave (P(2+) 70%). It needs real code (sender per touch, an OAuth login per inbox, reply routing) and raises the shared-domain risk, so it follows action 5 and a clean first week. A third inbox adds less than it costs and runs into the ~611 fit-organisation pool.
4. **Raise the rate after the reply: call-to-signed and reply handling.** This step has no benchmark and the widest uncertainty; moving it from 20% to 30% is worth as much as 1.5x the volume. Concretely: booking page and reply kit (tickets 02-04), a one-page scoping template, a funding path ready to say on the call (the Rotterdam subsidy fact), the `BR-PROJECT-SHAPE` claim ("a student team working with you from February to May") so the ask is a project, not a chat, and same-day answers to replies. Add warm introductions (branch alumni, advisers, Rotterdam funders) for the top 30 tier-1 organisations; an introduction should beat any cold reply rate, but there is no figure for it here **[assumption]**.
5. **Protect the domain and measure honestly.** Verify 180dc.org in Postmaster Tools and add DMARC reporting before the first send, stop on any complaint, alternate A/B arms within segment x tier x language and judge them only by "any human reply" counted 14 days after sending. It costs little and removes the two silent failures: a deliverability drop nobody sees, and a copy "winner" that is noise.

What would change this ranking: if batch 2 shows reply rates near 7%, volume is already enough and call quality (action 4) matters most; if the first 100 tier-2 emails get fewer than 2 human replies, stop adding volume and fix the template (the existing rule).
