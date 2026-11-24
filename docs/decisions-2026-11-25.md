# Decisions for Manuel, 25 Nov 2026

Write your answer after each `Answer:`. Every session prompt in `docs/prompts/2026-11-25-*` reads this file
first. **A blank answer means "not decided": the session skips that part and says so.** It never decides
for you. Recommendations come from `docs/scoping-2026-11-24/00-plan.md`.

## Already decided

- **D0. API key: no.** Everything runs from Claude Code on the subscription, as token-efficiently as possible
  (Manuel, 2026-11-24). No script calls the Anthropic API.

## Leads

**D1. Segments.** Drop cultural ANBIs (0 of 6 fit) and housing associations (0 of 3). Add childcare, youth
care, welzijn and work-integration social enterprises.
Recommendation: yes.
Answer:

**D2. LRK childcare register.** The official open-data csv sits on a host whose robots.txt says
`Disallow: /`. Is one cached download of the open-data file OK?
Recommendation: yes, one fetch, cached.
Answer:

**D3. Job boards for the "hiring for AI/admin" signal.** Code reads vacancies on the organisation's own
site. LinkedIn and Indeed forbid automated reading. Options: (a) own sites only; (b) plus nonprofit job
boards whose terms allow it (e.g. goededoelenvacatures.nl, checked first); (c) plus a list of LinkedIn and
Indeed searches the session writes for you to open by hand.
Recommendation: (b) + (c).
Answer:

**D4. Google Maps scraping (gosom, Places, Apify).**
Recommendation: no. OpenStreetMap Overpass is the fallback if the lists run short.
Answer:

**D5. Vibe Prospecting, company-level fields only (size, hiring), after a free coverage test. Never its
contact data.**
Recommendation: optional, low value.
Answer:

**D6. Ask for lists by email:** data@cbf.nl (API access), Voor Goed Agency (Impactkaart list), Sociaal Werk
Nederland (member list). The session drafts the three emails into `drafts/`; you send them.
Recommendation: yes.
Answer:

## Batch 1 leftovers

**D7. changemakers.** The only printed address is `enver@changemakers.nl`, under "Contact", no name beside
it. Write to it as their contact inbox and greet the team, or reject them?
Answer:

**D8. socialdebt.** The homepage names Jamal Oulel as founder (the card missed it). Put the name in the
subject?
Answer:

**D9. TR-EVIDENCE wording** in `ledger.yaml` (ticket 10 asks you to confirm it once): OK as written?
Answer:

## Volume

**D10. January wave, 5-16 Jan.** Pending follow-ups and first emails on 5-9 Jan only. It needs a
`limits.yaml` change.
Recommendation: yes. 850 → 1,435 emails, expected signed 0.8 → 1.3.
Answer:

**D11. A second inbox.** Who (another 180DC member who answers replies as themselves)? Start only after a
clean first week in Postmaster Tools.
Recommendation: yes. With D10: 2.45 expected signed, 70% chance of 2 or more.
Answer (name, address):

**D12. Who holds 180dc.org DNS** (for Postmaster Tools verification and a DMARC `rua=` report address)?
The session drafts the request; you send it.
Answer:

## Offer and law

**D13. New ledger claim `BR-PROJECT-SHAPE`:** "a student team working with you from February to May".
Recommendation: yes. It makes the ask a project, not a chat.
Answer (OK / your wording):

**D14. Legal team questions.** Send them `docs/lawful-basis.md` open points 1-3 plus one new one, cold
calls to an organisation's published phone number?
Recommendation: yes, before volume goes up.
Answer:

## The high-value track

**D15. Cold calls.** You make them yourself, to numbers printed on the organisation's own site, in English
(or German for DE/AT/CH). Which hours suit you, and how many a week?
Answer (hours, number per week):

**D16. LinkedIn by hand.** For top leads the session writes a short connection note you can send yourself.
The kit never automates LinkedIn. Want the notes?
Answer:

## Housekeeping

**D17. Commits.** May sessions commit tracked files (code, docs, cards, `pipeline.yaml`), never `private/`,
`drafts/`, `state/` or `data/`, and never push?
Recommendation: yes, commit at the end of each session; you push.
Answer:
