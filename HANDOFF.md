# Handoff: the 180DC Delft & Rotterdam outreach kit

Written 24 November 2026 for the outside auditor (GPT-Astra) and for Manuel. Sections 1–5 and 7 are
meant to be readable in ten minutes without touching code. Section 3 is the design rationale, section
4 the commands, section 6 the open decisions.

## 1. What this is, in five lines

1. It is a cold-outreach kit that finds Dutch nonprofits and social enterprises, decides from their
   own website whether an automation project could fit, and writes a short, sourced email.
2. A person approves the first emails; a plain script sends them, with a daily ramp and a bounce pause.
3. It runs on public registers and the organisation's own pages. It never buys a list, never scrapes a
   closed platform, and never guesses an email address.
4. The goal is two or three paid student-consulting projects for 180DC Delft & Rotterdam by
   mid-January 2027, from about 1,000 emails by 22 December.
5. The kit is deliberately token-cheap: every rule and every gate is code. No script calls a model.

## 2. Repo map

### Top level

| Path | What it is | Why it exists |
|---|---|---|
| `README.md` | Short overview and the shape of a sending day | First file a new reader opens |
| `CLAUDE.md` | The rules every Claude session must follow here | Keeps sessions from sending, guessing or over-spending |
| `HANDOFF.md` | This file | Audit trail for the outside reviewer |
| `requirements.txt` | PyYAML, Google client libraries, pypdf | Pinned, standard dependencies only |
| `data/` | `data/cache/` for fetched pages from `firm_contacts.py` | Avoids refetching the same page |
| `docs/` | Plan, runbook, decisions, legal notes, explainer | Where the thinking lives |
| `out/` | Generated files: the report, the log, the shortlist | Never committed; safe to delete and regenerate |
| `tenants/` | One folder per sending organisation | Everything tenant-specific lives here |
| `tools/` | All scripts | The engine |

### `tenants/180dc-delft-rotterdam/`

| Path | What it is |
|---|---|
| `tenant.yaml` | Sender identity, offer, target profile, A/B arms, approval rules |
| `limits.yaml` | Daily ramp 20/35/50/65, send window, gaps, follow-up timing, bounce pause |
| `ledger.yaml` | The only claims an email may make about the sender, each with an ID |
| `pipeline.yaml` | Organisations, contacts (no addresses), touches and outcomes |
| `targets.yaml` | ~1,800 candidate organisations from the public registers |
| `templates/` | Email skeletons per arm and language |
| `cards/` | 28 research cards, one per researched organisation |
| `state/` | Send log, enrich records, calls, approvals page, local registry; never committed |
| `drafts/` | Written email bodies and reply drafts; never committed |
| `private/` | Contacts, suppression list, Google credentials; never committed, never read by a session |

### Every tool

| Tool | What it does | Why it exists |
|---|---|---|
| `tools/tenant.py` | Resolves every path and loads YAML | One place for paths, so no script hard-codes the tenant |
| `tools/selftest.py` | Offline test of every sending rule against a throwaway tenant | Proves the rules still hold before any commit |
| `tools/enrich.py` | Fetches a site politely, extracts facts, scores it, writes a digest; `batch` ranks the next candidates | The zero-token gate between 1,800 candidates and research |
| `tools/report.py` | Builds `out/report.html`, one self-contained page | The status page for the team and the board |
| `tools/pipeline.py` | Adds organisations, contacts and touches; assigns arms; records outcomes | Stops hand-edited YAML and arm-picking |
| `tools/lint_email.py` | Checks one email against the writing rules | Mechanical check before a human read |
| `tools/gmail_draft.py` | Gmail drafts, thread reading, reply sync, report mail | The only script that touches the mailbox contents |
| `tools/send.py` | The only script that sends; ramp, gaps, caps, bounce pause, approvals page | Sending is irreversible, so it is isolated |
| `tools/followups.py` | Writes the one follow-up per first email, seven days later | Follow-ups should never depend on memory |
| `tools/outreach_due.py` | Prints today's work in order: replies, approvals, follow-ups, new emails | The daily starting point, read-only |
| `tools/stats.py` | Numbers by arm and tier | Sunday review, read-only |
| `tools/calls.py` | Plans and logs Manuel's calls; prints the number and opener | Calls are not emails and must not pollute the pipeline |
| `tools/registry.py` | Shared contact registry, local or monday.com | Two branch members must not write to one organisation |
| `tools/writer_lock.py` | One writer at a time for `pipeline.yaml` | A daily run and a session must not interleave writes |
| `tools/google_auth.py` | One-time OAuth for the sending inbox | Login lives per tenant, not per repo |
| `tools/firm_contacts.py` | Prints the addresses and team digest a firm publishes | For the high-value track, never guesses an address |
| `tools/verdict_harness.py` | Compares a cheap model's verdicts with the 28-card answer key | Tests a model outside the repo, with no key committed |
| `tools/daily_run.ps1` | Windows scheduled task: preflight, prepare, send, report | The unattended day |
| `tools/sources/_common.py` | Shared fetch, de-duplicate and append helpers | One implementation for every register |
| `tools/sources/anbi.py` | ANBI charity register into `targets.yaml` | The largest free source of Dutch nonprofits |
| `tools/sources/social_enterprise_nl.py` | Social Enterprise NL member list | The social-enterprise segment |
| `tools/sources/aedes.py` | Aedes housing members, Rotterdam region | The housing segment, kept separate on purpose |
| `tools/sources/rotterdam_subsidies.py` | Marks subsidised candidates, adds no rows | Funding signal without a new source |
| `tools/sources/mark.py` | Sets candidate status; prints the next picks | Keeps the batch rule in one command |

## 3. The pipeline, step by step

| Step | Design choice | Alternative we rejected |
|---|---|---|
| 1. Registers → candidate list | Free public registers, de-duplicated on the website domain | Buying a contact list, or scraping Google Maps; both are expensive or against terms |
| 2. Enrich gate | Twelve code signals, threshold 3, about 16 requests per site, cached 7 days | Asking a model about every candidate: roughly 17k tokens each, and most are obvious misses |
| 3. Research card | One card per organisation, every fact with its URL, verdict with reasons | Re-researching for each email; the card would drift |
| 4. Email from a template | Two alternating arms, fixed shape, one ask and one link | Letting the model design each email; results stop being comparable and the rules leak |
| 5. Lint and checker | Mechanical rules, then a second reader | Trusting one model to police itself |
| 6. Gmail draft | Footer, opt-out and unsubscribe header added by code | Pasting text into Gmail by hand; footers drift and tracking breaks |
| 7. Manuel approves | First 30 first emails and all tier-1 emails wait for an explicit command | Auto-sending everything; one bad batch burns the domain |
| 8. Send with a ramp | Separate script, working hours, random gaps, 20→65 a day, bounce pause at 3% | Sending from the drafting session; a model must not be able to send |
| 9. Follow-ups, replies, calls | One follow-up in-thread; replies classified and drafted for a human; call planner prints number and opener | A model reading the inbox and answering; wrong answers to real organisations are worse than slow ones |
| 10. Reporting | `stats.py` for the week, `report.py` for the whole status, one approvals page | A spreadsheet nobody updates |

## 4. How to run each part

All commands run from the repo root with `python` (3.10 or newer; this machine has 3.14).
"Cost" says what the command can do to the outside world.

### Safe, read-only or local-only

| Command | What it does | Cost |
|---|---|---|
| `python tools/selftest.py` | Runs every rule against a temporary tenant | None; offline, Gmail stubbed. **Run before every commit.** |
| `python tools/report.py` | Writes `out/report.html` | Writes one local file only |
| `python tools/stats.py` | Sends, replies, positives by arm and tier | Reads only |
| `python tools/outreach_due.py` | Today's work in priority order | Reads only |
| `python tools/send.py status` | What is ready, held or waiting | Reads only |
| `python tools/send.py check --touch ID` | Every reason a specific touch would be held | Reads only, changes nothing |
| `python tools/pipeline.py show --org ID` | One organisation and its touches | Reads only |
| `python tools/calls.py list` / `due` | Planned calls, with number and opener | Reads only |
| `python tools/registry.py check DOMAIN` | Whether anyone already contacted that domain | Reads only |
| `python tools/enrich.py score DOMAIN` | Scores a saved facts record | Reads only (no fetch) |
| `python tools/enrich.py calibrate --cached` | Re-scores the 28 cards from saved facts | Reads only |
| `python tools/verdict_harness.py --model FILE --limit 5` | Tests a model file you supply | Spends whatever that model costs, if it is paid; the repo itself calls nothing |

### Network fetches, no email

| Command | What it does | Cost |
|---|---|---|
| `python tools/enrich.py DOMAIN` | Facts record and digest for one site | ~16 polite requests, obeys robots.txt, cached 7 days |
| `python tools/enrich.py batch --pick 50 --csv` | Enriches and scores the next 50 candidates, writes `out/shortlist.csv` | ~800 requests in total, 4 workers, cached; no personal data in the CSV |
| `python tools/firm_contacts.py DOMAIN --people` | Published addresses and a team digest | A handful of requests, cached in `data/cache/` |
| `python tools/sources/anbi.py` (and the other three source scripts) | Refreshes `targets.yaml` from a register | One download per source; changes `targets.yaml` |

### Writes state or Gmail, does not send

| Command | What it does | Cost |
|---|---|---|
| `python tools/send.py ready --touch ID` | Drafted → ready, waiting or held | Changes `pipeline.yaml` |
| `python tools/send.py approvals --html` | Writes the approvals page | Writes `state/approvals.html` |
| `python tools/gmail_draft.py draft --touch ID` | Creates or replaces the Gmail draft | **Writes to the Gmail account** |
| `python tools/gmail_draft.py sync` | Classifies replies and bounces | Reads Gmail; `--apply` writes the pipeline and suppression list |
| `python tools/followups.py prepare` | Queues due follow-ups | Writes new touches; `--dry-run` only lists them |
| `python tools/pipeline.py add-org` / `add-contact` / `add-touch` / `set` | Maintains the pipeline | Writes `pipeline.yaml` |
| `python tools/calls.py add` / `log` | Plans and records a call | Writes `state/calls.yaml`; `log` can set a pipeline outcome |
| `python tools/gmail_draft.py auth` | One-time browser login | Writes the private token |
| `powershell -ExecutionPolicy Bypass -File tools\daily_run.ps1 -NoSend` | Preflight and prepare only | Runs a session; still no send |

### Sends email, or is Manuel's alone

| Command | What it does | Cost |
|---|---|---|
| `python tools/send.py run` | The send loop | **Sends email.** Scheduler or Manuel only. |
| `python tools/send.py run --dry-run` | Shows what would go, sends nothing | None |
| `python tools/send.py approve --touch ID` | Manuel's approval | Changes the pipeline; Manuel only |
| `powershell -ExecutionPolicy Bypass -File tools\daily_run.ps1` | Full unattended day, including send | **Sends email** |
| `python tools/gmail_draft.py mail-self` | Mails the report to the sending inbox | Sends a mail to yourself |

Not run in this session, and why: `send.py run` and `daily_run.ps1` send email; `send.py approve` is
Manuel's; `gmail_draft.py draft`, `sync`, `auth` and `mail-self` write to or read the Gmail account;
`followups.py prepare` writes touches; the source scripts and `firm_contacts.py` fetch the open
internet, which this session only did through `enrich.py` when building. Everything else in the
tables was run while writing this file.

## 5. Current numbers

Taken from `out/report.html`, generated 24 November 2026:

| | |
|---|---|
| Emails sent | 10 |
| Replies | 0 |
| Calls or better | 0 |
| Signed | 0 |
| Candidates in `targets.yaml` | 1,796 (1,768 new, 17 rejected, 11 researched) |
| Research cards | 28 |
| Cards that are a fit | 11 |
| Drafted / approved / sent touches | 10 / 10 / 10 |
| Days left to 22 December | 28 |
| Selftest | **142 passed, 0 failed** |
| Report size | about 16 KB, one file, no external request |

The funnel's largest measured drop is 28 researched → 11 fit. The gate stage is not measured yet
because `out/shortlist.csv` has not been produced; the report says so instead of guessing.

## 6. Open decisions

`docs/decisions-2026-11-25.md` holds D0–D17. **D0 is answered** (no API key; everything runs from the
Claude subscription). **D1–D17 are blank.** A blank answer means the session skips that work.

| ID | Waiting on | Unlocks |
|---|---|---|
| D1 | Segment rule | Childcare, youth-care and welzijn leads; drops cultural and housing first picks |
| D2 | One cached LRK childcare download | Another official source |
| D3 | Job-board rule | The "hiring for admin/AI" signal |
| D4 | Maps scraping rule | A fallback if registers run short |
| D5 | Company-size data | Low-value enrichment |
| D6 | Three list-request emails | Member lists from funds and sector bodies |
| D7 | changemakers address | One batch-1 leftover |
| D8 | socialdebt subject line | One batch-1 leftover |
| D9 | Ledger wording | Closes a ticket |
| D10 | January wave | The 1,000-email goal and 1.3 expected signed |
| D11 | Second inbox | January volume, 2.45 expected signed with D10 |
| D12 | DNS holder | Postmaster Tools and DMARC reports |
| D13 | Project-shaped claim | Makes the ask a project, not a chat |
| D14 | Legal team questions | A legal answer before volume rises |
| D15 | Call hours and volume | Manuel's weekly call plan |
| D16 | LinkedIn notes | Hand-written notes for top leads |
| D17 | Commit rule | A commit at the end of each session |

## 7. Known gaps and risks

1. **Legal basis.** The Telecommunicatiewet 11.7 reading in `docs/lawful-basis.md` has not been
   confirmed by a lawyer. Volume should not rise before D14 is answered.
2. **Footer postal address.** The footer names the sender and the organisation, says where the address
   was found and offers an opt-out, but no postal address is configured in `tenant.yaml`.
3. **English templates to Dutch organisations.** A deliberate choice, because the team can check
   English. Dutch templates need a native reviewer.
4. **The Maaszicht case-file wording.** It is the one card that talks about client case files; the
   wording is still a review item, not a settled claim.
5. **The verdict harness has never seen a real model.** Its fixtures and the answer key work; no live
   model has been compared against them.
6. **GDPR transfer risk.** If a non-EU model is given digests, and a digest contains a person's name,
   that is a personal-data transfer. Today's code gate sends nothing anywhere; a model run needs a
   decision on this first.
7. **The Gmail OAuth app is in "Testing" mode.** The refresh token can expire after seven days. The
   daily run checks the login first and stops loudly; publishing the app removes the trap.
8. **Uncommitted code changes.** `tools/send.py`, `tools/gmail_draft.py`, `tools/pipeline.py`,
   `ledger.yaml`, `pipeline.yaml`, `templates/first-A.en.md`, `templates/first-B.en.md` and
   `requirements.txt` were already modified before this session and are Manuel's review items.
9. **The branch is unmerged and unpushed.** `deepseek/work-2026-11-25` sits six commits ahead of the
   base commit. Pushing and merging are Manuel's.
10. **No shared do-not-contact list** with Manuel's career outreach kit. An organisation that opted
    out there is not automatically blocked here.

## 8. What this session changed

The four answers at the top of the session prompt were blank, so:

- **W0 skipped.** No answer was written into `docs/decisions-2026-11-25.md`; the file is untouched.
- **W1 skipped.** `COMMIT_DOCS` was blank, so the planning docs were not committed.
- **D17 was blank, so no commits were made at all.** Every change is in the working tree, listed below.
- **W2, W3, W4, W5 and W6 done**, in the working tree.

Files created:

- `tools/report.py` — the status report generator.
- `docs/next-10-days.md` — the hand-edited plan the report prints.
- `docs/explainer/index.html` — the five-slide board explainer.
- `HANDOFF.md` — this file.

Files modified:

- `tools/enrich.py` — `batch --csv` and the shortlist writer (terminal table unchanged).
- `tools/selftest.py` — 13 new checks (129 → 142).
- `out/deepseek-log.md` — the session log entry (generated output, not committed).

## 9. Questions for the auditor

1. Does the score gate's calibration hold on the 28 cards, or does it only look good because those
   cards were written by the same process that chose the signals?
2. Is the D1 segment recommendation defensible, or does dropping cultural ANBIs and housing
   associations remove the easiest first projects?
3. Is the mail footer, without a postal address, enough for Dutch practice, or is it a blocker?
4. Is the "one follow-up, then stop" rule too conservative for a 1,000-email goal?
5. Does the report's funnel measure the right stages, or does it flatter the gate by counting cards
   rather than candidate outcomes?
6. Is the scrub in `report.py` sufficient to guarantee no personal data reaches a shared page?
7. What is the smallest change that would make the verdict harness usable with a real model without a
   GDPR transfer problem?
