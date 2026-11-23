# Client outreach kit: rules for every session

Outreach that wins paid AI-automation projects for a tenant. Today the only tenant is 180DC Delft &
Rotterdam (`tenants/180dc-delft-rotterdam/`); the agreed plan is `docs/build-spec.md`, the daily
procedure `docs/runbook.md`. Tools pick the tenant from `OUTREACH_TENANT` (default 180dc-delft-rotterdam).

## Never
- Send. Only `tools/send.py run` sends, started by the scheduler or by Manuel. A session ends its work
  on an email with `python tools/send.py ready --touch ID`.
- Approve. `send.py approve` is Manuel's, said by him for those touch IDs in this session.
- Use an address that is not printed on the organisation's own pages. Never guess or build one.
- Claim anything about the sender that is not in the tenant `ledger.yaml` with `usable: true`
  (tag `[claim:ID]`), or anything about a recipient without its page (`[src:URL]`).
- Name a client (Oil Empire, one.immo, Aztec, Fleet, any past 180DC client) in an email.
- Write the footer, opt-out or "where we found your address" into a body. `gmail_draft.py` adds them.
- Contact an organisation that `registry.py check` blocks, or that is on the suppression list.
- Answer a human reply for Manuel. Draft it into `drafts/reply-<org>.txt` and put it in the report.
- Hand-edit `pipeline.yaml` while a tool could do it. Use `tools/pipeline.py`; if you must edit,
  take `python tools/writer_lock.py acquire --seat claude` first and release after.
- Commit anything in `tenants/*/private/`, `tenants/*/drafts/`, `tenants/*/state/` or `data/`.

## Token rules
- Research goes to the `researcher` agent (Haiku), several organisations per call. Never research in
  the main session. A card is written once to `tenants/<t>/cards/<org-id>.md` and never redone.
- The batch check goes to the `checker` agent (Haiku), once per batch of drafts.
- Don't read whole state files. Use `outreach_due.py`, `send.py status`, `stats.py`, `pipeline.py show`.
- Web search at most 3 results; prefer one narrow WebFetch.

## Writing
- Start from the template the `pipeline.py add-touch` output names, in the organisation's language
  (English, or German with Sie for DE/AT/CH; no Dutch).
- First line of a first email: `Subject: ...`. Follow-ups have no subject line.
- First email up to 125 words, follow-up up to 60, one question (the call ask), one link (booking).
- No usage numbers, no attachments, no AI-pitch words. Their workflow in their words.
- Tier 2 may guess a workflow typical of their sector, worded as a guess, never as something seen.
