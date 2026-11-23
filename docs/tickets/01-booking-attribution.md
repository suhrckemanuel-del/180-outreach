# 01 Know which email a booking came from

**Problem.** A prospect books through the shared link. The kit knows who it emailed with which arm and
tier, but nothing connects the booking to that email, so the Sunday review counts replies, not calls,
and the A/B test measures the wrong thing.

**Options.**
- (a) Booking form asks "Organisation name" (required). A script matches it to the pipeline by name
  or domain and sets `outcome: call`. Cheap, works with one link.
- (b) Two identical appointment schedules, one link per arm. Exact attribution, but two schedules to
  keep in sync.
- (c) Read the booking confirmation emails in the 180DC inbox (`gmail_draft.py sync` already reads
  the inbox) and parse the organisation and email from them.

**Suggested.** (a) now, set up with the booking page. Then (c): extend `sync` to spot Google Calendar
booking confirmations, match the booker's email domain to the pipeline, and set `outcome: call`
plus the registry status `call_booked` automatically.

**Done when.** `stats.py` shows calls per arm and tier without Manuel typing them in.
