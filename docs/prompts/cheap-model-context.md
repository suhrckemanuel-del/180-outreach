# Context for the cheap-model worker (DeepSeek or similar)

Repo: https://github.com/suhrckemanuel-del/180-outreach (private; work from a local clone)

## Who and why
We run client outreach for 180 Degrees Consulting Delft & Rotterdam (student consultancy). Goal: 2-3 signed
AI-automation projects with nonprofits and social enterprises by mid-January. Sender: Manuel, who leads AI.
Cold emails go to organisations, with a free 30-minute call as the only ask. A strong model (Claude)
orchestrates; you do high-volume, low-judgement work and hand back JSON that code checks.

## Read first (in this order, then stop reading)
1. `CLAUDE.md` (the rules)  2. `docs/scoping-2026-11-24/03-enrichment.md` sections 5-7
3. `tenants/180dc-delft-rotterdam/ledger.yaml` (the only claims allowed about the sender)
4. `tenants/180dc-delft-rotterdam/cards/maaszicht.md` and `.../teachbuddy.md` (what a good card looks like)

## Your jobs (each has a fixed input and a fixed JSON output)
A. **Verdict.** Input: one digest from `tenants/<t>/state/enrich/<domain>.digest.md`.
   Output: `{"domain","verdict":"fit|reject","tier":1|2|3,"reason":"<=25 words","evidence_url":"<a URL that appears in the digest>"}`.
   Fit = a repetitive, visible workflow (intake, orders, reports, sign-ups), a real organisation (not a
   consumer product), 8-150 staff, reachable by a printed address on its own domain.
B. **Two ideas.** Same input. Output: `{"workflow":"<their words>","idea1":"<one line>","idea2":"<one line>","source_url":"<from the digest>"}`.
   Name the workflow the way their page does. Word anything not read on the page as a guess ("if done by hand now").
C. **Slot fill.** Input: the template `first-A.en.md` or `first-B.en.md` plus job B's output. Output: the finished
   email text with `[src:URL]` after every fact about them and `[claim:ID]` after every sentence about us.
   Then run `python tools/lint_email.py <file>`; if it fails, fix and rerun once, then report.
D. **List cleanup.** Normalise names and cities in a candidate CSV; flag cultural and housing organisations by name.

Return only the JSON or file named above. No commentary.

## Never (a failure here is worse than doing nothing)
- Write, guess or build an email address. Addresses come only from `tools/enrich.py` output.
- Send, approve, or touch `send.py`, Gmail, `pipeline.yaml`, `targets.yaml`, `private/`, `state/` (read digests only).
- Claim anything about the sender that is not in `ledger.yaml` with `usable: true`.
- Name a client. Use numbers about time saved. Use "AI-powered", "revolutionise", "unlock", "streamline".
- Invent a fact about an organisation. If the digest does not say it, it is a guess, worded as one.
- Contact LinkedIn or Google Maps. Push to git.

## Privacy
Digests may contain names and addresses of real staff. Do not copy them into any output except
inside the email draft for that organisation. Do not send them to any service other than the one
running you.

## Done means
Every output validates against its JSON shape, every URL appears in the input, and `python tools/selftest.py`
still ends with `0 failed`. Test yourself on the 28 batch-1 cards first: the 11 FIT and 17 REJECT verdicts in
`tenants/180dc-delft-rotterdam/cards/*.md` are the answer key. Report your match rate before doing new work.
