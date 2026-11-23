# Runbook

All paths below are relative to the repo root; tenant files are under `tenants/<tenant>/`
(today `tenants/180dc-delft-rotterdam/`, called `T/` here).

## The daily run

Started by `tools/daily_run.ps1` on weekdays at 07:00 after the Gmail preflight passed. One fresh
Sonnet session does steps 1-8; then the script runs `tools/send.py run` (no model) through the send
window and mails the report.

1. **Status.** `python tools/send.py status`. If `T/state/STOP` exists, do only steps 2, 3 and 8, and
   put the STOP reason first in the report.
2. **Sync.** `python tools/gmail_draft.py sync --days 14 --apply`. It records human replies (the
   organisation stops), opt-outs (suppressed, registry updated), bounces (address suppressed) and
   auto-replies (noted only).
3. **Replies.** For each human reply: `python tools/gmail_draft.py read --thread <id>`, then draft an
   answer into `T/drafts/reply-<org-id>.txt` that offers the booking link or answers the question
   asked. Never send it. It goes first in the report, with the thread id.
4. **What is due.** `python tools/outreach_due.py`. Work in this order: FOLLOW-UP, CHAIN, then NEW
   FIRST EMAILS up to the number it prints. STALE items: redo once or drop.
5. **Follow-ups** (no model): `python tools/followups.py prepare`. It writes the question from the two
   workflows stored on each first email, lints it, drafts it in the same thread and queues it. Only the
   ones it lists under WRITE BY HAND need a session: write those from `templates/follow.<lang>.md`
   (`pipeline.py add-touch --kind follow_up`), then step 7.
6. **New organisations.** Take the next `status: new` candidates from `T/targets.yaml` (about 1.3 per
   email needed, since some get rejected).
   - `python tools/registry.py check <domain>` for each; drop blocked ones (mark rejected, why: registry).
   - One `researcher` agent call per 5 organisations. Save each card to `T/cards/<org-id>.md`.
     REJECT -> targets.yaml status rejected with the reason.
   - FIT: `pipeline.py add-org` (tier from the card), `add-contact` for the person to write to
     (address and the page it was printed on), `add-touch --kind first --workflows "<workflow 1>" "<workflow 2>"`
     with the two workflows the email will name, in their words (the follow-up reuses them). The output
     names the arm, language, template and the draft file to write.
   - Write the draft from the template and the card. Tier 1: both ideas from the card. Tier 2: one
     verified fact, the sector's typical workflow worded as a guess.
7. **Check and queue**, per batch of drafts:
   - `python tools/lint_email.py T/drafts/<touch>.txt [--followup] --lang <lang>` until it prints no ERROR.
   - One `checker` agent call for the batch (draft files, cards, `T/ledger.yaml`). Fix or drop every FAIL.
   - `python tools/gmail_draft.py draft --touch <id>` then `python tools/send.py ready --touch <id>`.
     `ready` may answer `needs_approval` (tier 1, or the first 30 first emails): that is expected.
8. **Report** to `T/state/daily-report.md`, in this order: replies that need Manuel (org, thread, the
   draft answer's file); approvals waiting (`python tools/send.py approvals` output); what was
   prepared today (ready / needs_approval counts by arm and tier); held and why; anything broken.
   Append one line to `T/state/log.md`. Commit the tenant's tracked files (never private, drafts, state).

## Manuel, each morning (10 minutes)

- Read the report in the 180DC inbox.
- Answer the human replies yourself, using the drafted answers if they help.
- `python tools/send.py approvals`, read the listed `.clean.txt` files, then
  `python tools/send.py approve --touch <id> <id> ...` before 08:30 so they go out today.
- Record outcomes: `python tools/pipeline.py set --org X --outcome call|proposal|signed|no`.
  This also marks the organisation in the shared registry so nobody else in the branch writes to it.

## Sunday review (20 minutes)

1. `python tools/stats.py`: sent, replies, positives, opt-outs and bounces by arm and by tier.
2. Read five random tier-2 emails from the week's sent folder. One bad one = tighten the template.
3. Check the pace against the goal: about 1,000 emails by 22 December, 2-3 signed by mid-January.

## Stop rules

- `send.py run` pauses itself (writes `T/state/STOP`) when bounces pass 3% of the last 100 sends or
  3 in one day. Find the cause (bad source, a typo pattern) before deleting STOP.
- One angry reply or a spam complaint: create `T/state/STOP` by hand and look at the template.
- Fewer than 2 human replies from the first 100 tier-2 emails: change the template before sending more.
- Arms: no conclusion before about 30 first emails per arm; read it as a direction only.
