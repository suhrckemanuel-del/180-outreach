We are building client outreach for 180DC Delft & Rotterdam. This session does two things: phase 0 of
the tooling plan (four small safeguards before the first send), then the rest of batch 1 up to
`needs_approval`. Nothing is sent in this session.

Read first: `CLAUDE.md`, `docs/handoff-2026-11-21.md`, `docs/tooling-review-2026-11-23.md` (phase 0,
items 1-5), `docs/REPO-MAP.md`, `docs/runbook.md` steps 6-7. Run `python tools/selftest.py` once
(it should say 55 passed) and `python tools/send.py approvals` (it should say 0 waiting).

## Part 1: phase 0 (code, each change with a self-test check)

1. **Unsubscribe header.** `gmail_draft.py draft` adds
   `List-Unsubscribe: <mailto:{sender address}?subject=unsubscribe>` to every first email, follow-up
   and chain email. `gmail_draft.py sync` classifies a reply whose subject or body is just
   "unsubscribe" as an opt-out (same path as "no"). Add self-test checks for both.
2. **Lawful basis on every contact.** `pipeline.py add-contact` takes `--basis`, defaulting to
   "legitimate interest: address published by the organisation at {source}; offer relevant to its
   work". Store it next to the address in `private/contacts.private.yaml`. `send.py` holds a touch
   whose contact has no basis. Write `docs/lawful-basis.md`, one page for the 180DC legal team:
   why legitimate interest, what we collect, where it came from, the opt-out, how long we keep it,
   and that a named person's address is personal data while info@ mostly is not. No legal claims
   beyond that; the legal team owns the conclusion. Add self-test checks.
3. **MX check.** `add-contact` refuses an address whose domain has no mail server. Use dnspython
   (add it to `requirements.txt`). If DNS cannot be reached, refuse with a clear message rather than
   accept. Add a self-test check with the lookup stubbed.
4. **Approval page.** `send.py approvals --html` writes `tenants/<t>/state/approvals.html` (gitignored):
   for each touch waiting for approval, the clean email text, organisation, tier, arm, the card's
   facts with their source links, and the touch id to approve. Escape all text. Approving stays the
   `send.py approve` command, which only Manuel runs.

Run the self-test after each change; it must end with 0 failed. Do not change sending limits, the
ramp, the footer wording or the ledger.

## Part 2: finish batch 1 (the 11 fits)

The fits, with cards in `tenants/180dc-delft-rotterdam/cards/`: maaszicht, stichtingopwijs,
kinderparadijs (nonprofit); oaserotterdam, equalrecruitment, cupxchange, lunchbunch, teachbuddy,
socialdebt, changemakers, heiligeboontjes (social enterprise). All tier 2, all Rotterdam, all English.

For each fit, from its card only:
1. `python tools/registry.py check <domain>` again (it may have changed since 21 Nov).
2. `pipeline.py add-org` (tier 2, `--card cards/<id>.md`).
3. `pipeline.py add-contact` with an address **printed on their own site**, and the page it was
   printed on as `--source`. Use a personal address only if it is printed beside that person's name;
   otherwise use the info@-type inbox and put the director's name in the subject, per `tenant.yaml`.
   One contact per organisation for now.
4. `pipeline.py add-touch --kind first --workflows "<workflow 1>" "<workflow 2>"`, two workflows
   in their words, taken from the card. The output names the arm, template and draft file.
5. Write the draft from that template: one verified fact with `[src:URL]`, the sector workflow
   worded as a guess, sentences about us only from `ledger.yaml` entries with `usable: true`
   (`[claim:ID]`), no client names, no Dutch. 125 words at most.
6. `python tools/lint_email.py tenants/180dc-delft-rotterdam/drafts/<touch>.txt --lang en` until no ERROR.

Then **one** `checker` agent call for all drafts (draft files, cards, `ledger.yaml`). Fix or drop every
FAIL and say which. Then for each draft that passed: `python tools/gmail_draft.py draft --touch <id>`
(this is the first live use of the new inbox: if the login fails, stop and tell me, don't work
around it), then `python tools/send.py ready --touch <id>`. Every one should end `needs_approval`.
Finally `python tools/send.py approvals --html`.

Mark anything you drop in `targets.yaml` with `python tools/sources/mark.py <domain> --status rejected --why "..."`.

## Never in this session

`send.py approve`, `send.py run`, any Gmail send, editing `pipeline.yaml` by hand, guessing an address,
Google Maps or job-board scraping, Apify, or any decision from the "Decisions for Manuel" list in
`docs/tooling-review-2026-11-23.md`. Don't commit or push; ask me first.

## End with a short report

- Phase 0: what changed per item, the self-test count before and after.
- Batch 1: per organisation, the contact used (inbox or named, and the page), arm, checker result,
  final status; anything dropped and why.
- The list from `python tools/send.py approvals` and the path of `approvals.html`.
- Roughly how many tokens the drafting and checker calls took (subagent totals).
- Any decision you need from me.
