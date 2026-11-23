# 08 Research, send and review in batches of 25

**Problem.** Sending 1,000 emails to one segment before knowing whether that segment answers wastes the
list and the shared domain's reputation. Manuel's doubt: nonprofits may not be the best segment.

**The batch.** 25 organisations from `targets.yaml`, picked by a rule, not by hand:
- **Batch 1 is mixed on purpose:** about 13 nonprofits and 12 social enterprises (plus 2-3 Rotterdam
  woningcorporaties if the list has them), Delft and Rotterdam only. This answers "which segment"
  in the first week instead of after 500 emails.
- Later batches follow what the review says.

**Per batch.**
1. `registry.py check` every domain; blocked ones are marked rejected.
2. Research: 5 `researcher` agent calls of 5 organisations. Cards to `cards/`. REJECTs marked with the reason.
3. Fits go into the pipeline (`pipeline.py add-org / add-contact / add-touch --workflows ...`).
4. Draft, lint, `checker` agent, Gmail draft, `send.py ready`. Batch 1 is all approved by Manuel.
5. `send.py run` sends it inside the daily cap. Follow-ups come 7 days later by themselves (ticket 09).

**Review after each batch (10 minutes, Manuel).** Write one line per batch in `docs/batches.md`:
- fit rate: fits / researched, by segment and by source (from ticket 07);
- the first week's replies and bookings, by segment and arm;
- one decision: same mix, shift the mix, or try a new segment or source.

The rule of thumb: a segment with a fit rate under 40% or no human reply after 25 sends gets no
more batches until the email or the filter changes.

**Done when.** Batch 1 is sent and reviewed, and `docs/batches.md` records the decision for batch 2.
