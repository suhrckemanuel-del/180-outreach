# Email skeletons

The drafting session fills the {slots} and keeps the shape. The footer (who we are, where the address
came from, the opt-out) is added by `tools/gmail_draft.py`. Never write it into the body.

Tags, stripped by `tools/lint_email.py --clean`:
- `[claim:ID]` after every sentence about us. IDs live in `../ledger.yaml`.
- `[src:URL]` after every fact about them. A first email without one fails the lint.

Rules for both arms:
- One question, and it is the call ask. A link only to the booking page.
- First email 125 words at most, follow-up 60, without the footer.
- No attachment, no usage numbers, no "AI-powered", "revolutionise", "unlock", "streamline".
- The two ideas name their workflow in their words ("the monthly report to your funders"), not ours.
- Tier 2: one verified fact and a workflow typical of their sector, worded as a guess
  ("organisations like yours often spend hours on ..."), never presented as something we saw.

| File | Use |
|---|---|
| `first-A.en.md`, `first-A.de.md` | Arm A: track record leads |
| `first-B.en.md`, `first-B.de.md` | Arm B: value-first leads |
| `follow.en.md`, `follow.de.md` | Day 7, same thread: the question |
| `chain.en.md` | Second person at the organisation, after the first person's follow-up |
