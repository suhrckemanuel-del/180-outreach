We are building client outreach for 180DC Delft & Rotterdam. This session builds the **high-value track**.
It finds organisations that show a pain we can solve: hiring for AI, automation, data or admin work;
writing publicly about AI, digitalisation, admin burden or waiting lists; or picked by Manuel. For the top
ones it builds a tailored package: a dossier, a one-page sketch of the workflow we would automate, a
tier-1 email, a call script for Manuel, and an optional LinkedIn note he sends by hand. No API key:
everything runs in Claude Code. Nothing is sent, and Manuel makes every call himself.

Read first: `CLAUDE.md`, `docs/decisions-2026-11-25.md` (D3, D13-D16; blank answer = skip that part),
`docs/lawful-basis.md`, `tools/enrich.py` (the facts record: vacancies, pain words, phone), the 11 batch-1
cards, `templates/first-B.en.md` and `ledger.yaml`. Run `python tools/selftest.py` once.

## Part 1: find them (code first, then cheap agents)

1. **Pool.**
   - `state/enrich/tier1-candidates.yaml` (from S3)
   - every scored organisation in `state/enrich/` above S1's threshold
   - `state/enrich/manuel-picks.txt` (one organisation or domain per line; create it empty if missing,
     and say in the report that Manuel can add names he has seen post about AI)
2. **Signal score in code (`tools/signals.py`, 0 tokens)**, from the facts record:
   - an AI, automation, data or digitalisering vacancy on their own site: +5
   - an admin, office, planning or coordinator vacancy: +3
   - pain words on their own pages: +2 each, max +4
   - a named funder that funds digitalisation: +2
   - a printed phone number: +1
   - a named person beside an address: +1

   Keep the top 40. Self-test checks with a fixture facts record.
3. **Public signals (use a workflow; scouts are Haiku, 8 organisations per agent, up to 5 in parallel).**
   - Per organisation, at most 2 WebSearch calls (3 results each), e.g. `"<org name>" digitalisering`,
     `"<org name>" AI OR automatisering`, `"<org name>" vacature`.
   - Read a result page only if it is on the organisation's own site, a news site, or a job board that
     D3 allows.
   - Never fetch linkedin.com or indeed.com. If D3 includes (c), return the LinkedIn and Indeed search
     URLs for Manuel to open by hand instead.
   - Return per organisation: each signal as `quote | url | date`, or `none`.
4. Rank by signal score plus public signals. Take the **top 10** (fewer if the signals are weak; a weak
   lead goes to tier 2, not here).

## Part 2: the tailored package (per lead)

**Use a workflow:** dossier writers (Sonnet, 2 leads per agent, up to 5 in parallel), then one verifier
(Haiku) that re-opens every URL and fails any fact its page does not say. Each lead gets
`tenants/180dc-delft-rotterdam/dossiers/<org-id>.md` (add `tenants/*/dossiers/` to `.gitignore`; dossiers
hold names and phone numbers):

1. **Pain, in their words:** every signal with its quote and URL. Separate what we saw from what we guess.
2. **Workflow map:** their steps as their pages show them. Mark which step is manual today, and say
   whether that is seen or guessed.
3. **One-page sketch:** the one automation we would build. Inputs (their form fields, their documents),
   steps, output, what a person still approves, what they would have after a February-May project. No
   time-saving numbers. This is for the call and for the reply after "tell me more", not an attachment.
4. **Tier-1 email** (`drafts/<touch>.txt`, `first-B` shape): the signal as the fact, two ideas from the
   sketch, claims only from `ledger.yaml` (BR-PROJECT-SHAPE if D13 added it), 125 words at most, one
   question, one link. Written to the person beside the printed address, or to the inbox with their name
   in the subject.
5. **Call script (if D15 is answered):**
   - the printed number and its page
   - who to ask for
   - a 2-sentence opener that names the signal
   - 3 questions about their workflow
   - the ask: a 30-minute call with the booking link read out
   - what to say to "send me an email"
   - language: English, German for DE/AT/CH; no Dutch script
6. **LinkedIn note (if D16 is yes):** up to 300 characters, for Manuel to send by hand.

Then for each lead:
- `pipeline.py add-org --tier 1`, then `add-contact` and `add-touch --kind first --workflows`
- `lint_email.py` until no ERROR
- one checker pass for all 10 drafts
- `gmail_draft.py draft`, then `send.py ready` (tier 1 always gives `needs_approval`)
- `send.py approvals --html`

## Part 3: `tools/calls.py`, the call track (code, with self-test checks)

- `calls.py add --org ID --due YYYY-MM-DD --script dossiers/<org>.md`
- `calls.py due` lists today's calls with number, name and the dossier's opener.
- `calls.py log --org ID --outcome no_answer|callback|call_booked|not_interested|wrong_person [--note]`
- `call_booked` runs `pipeline.py set --outcome call`.
- `not_interested` suppresses the domain the same way an email opt-out does.
- Calls never live in `pipeline.yaml`'s send path. `send.py` must ignore them; add a self-test check
  for that.

Sequence per lead:
- day 0: the email, once approved and sent
- day 1: the LinkedIn note by hand (D16)
- day 2-3: the call, if there is no reply (D15 hours)
- day 7: the automatic follow-up

`outreach_due.py` prints `CALLS` from `calls.py due`. Add a line to the "Calls" open point in
`docs/lawful-basis.md`, and leave the answer to the legal team (D14).

## Never in this session

`send.py approve` or `send.py run`, any Gmail send, any call (Manuel calls), fetching LinkedIn or Indeed,
Google Maps, a guessed address or phone number, an API key, a fact without its URL, editing
`pipeline.yaml` by hand, any decision left blank. Commit only if D17 is yes (never `private/`, `drafts/`,
`state/`, `data/`, `dossiers/`); never push.

## End with a short report

- The top 10: org, the strongest signal with its URL, the contact, call yes/no, checker result, status.
- Who was dropped and why.
- The LinkedIn and Indeed links for Manuel (if D3 c).
- The `calls.py due` list for the next 5 days.
- The approvals page path.
- Self-test before and after, subagent tokens, anything you need from me.
