# Lawful basis for outreach email: a note for the 180DC legal team

This page says what the outreach kit does with contact data and why we think legitimate interest is
the basis. It describes our reasoning; it is not a legal opinion. The conclusion, and any change to
how we work, is yours.

## What we do

180 Degrees Consulting Delft & Rotterdam emails nonprofits, social enterprises and housing
associations in the Netherlands to offer a free 30-minute call about a student project (one workflow
automated with them). About 1,000 first emails until 22 December 2026, at most two people per
organisation, and one follow-up per address after 7 days. A person reads and approves the first 30
emails before they go out.

## Why legitimate interest

- **Purpose.** We offer organisations a project relevant to their work, and the branch needs clients.
  Every email is about the recipient's own work, taken from their own website.
- **Necessity.** We write only to addresses the organisation published itself, to contact the public
  (info@, or a named person's address printed beside that person's name). We don't buy lists, guess
  addresses or build them from a name.
- **Balance.** A published work address, one short email about the organisation's work, one follow-up,
  an opt-out honoured on the first reply. We think the recipient can reasonably expect this. We don't
  profile anyone, and we don't collect anything beyond what is listed below.

Each contact is stored with the basis we rely on for it. The default reads: "legitimate interest:
address published by the organisation at <page>; offer relevant to its work". The kit won't send to a
contact that has no basis recorded.

## What we collect, and where it comes from

| Data | Where it comes from | Where it is kept |
|---|---|---|
| Organisation name, website, city, sector | public registers: Belastingdienst ANBI open data, Social Enterprise NL member list, Aedes member map, Rotterdam subsidy register | `targets.yaml`, `pipeline.yaml` (in the repo) |
| Research card: public facts about the organisation's work and funding, names and job titles of its leaders | the organisation's own website, each fact with its page | `cards/` (in the repo) |
| Email address, the page it was printed on, the basis | the organisation's own website only | `private/contacts.private.yaml` (local, never in git) |
| Contact name and job title | the same page | `pipeline.yaml` |
| Emails sent and replies | our Gmail inbox | Gmail |
| Opt-outs and bounces: address or domain, reason, date | replies | `private/suppression.private.yaml` (local) |

**A named person's address is personal data** (for example `j.devries@organisation.nl`), and so are
that person's name and job title on a card. **An info@-type address mostly isn't**, though a
role inbox that one identifiable person reads may be. Where no personal address is printed beside a
name, we write to the general inbox and put the director's name in the subject line.

## Opting out

- Every first email ends with who we are, the page where we found the address, and: *Not relevant?
  Reply "no" and we will not contact <organisation> again.* Follow-ups carry a shorter version.
- Every email also has a `List-Unsubscribe` header, so mail clients can show an unsubscribe link.
  It sends an "unsubscribe" email to our inbox.
- The daily sync reads replies. "no", "unsubscribe", "not interested" and similar put the
  organisation's whole domain on the suppression list, so nobody there is written to again. It also
  marks the organisation as opted out in the kit's register of contacted organisations. That register
  is local for now; once it moves to a board the branch shares, other 180DC senders will see it too.
  A bounced address is suppressed too.

## How long we keep it

No retention period is set yet, and nothing is deleted automatically. Open points for you:

1. How long to keep the address, name and card of an organisation that never replied (for example,
   until the end of the campaign plus a fixed period).
2. The suppression list has to outlive the rest, or an opted-out organisation could be written to
   again. Keeping only the domain, the reason and the date seems the minimum.
3. Whether the Dutch rules on unsolicited electronic messages (Telecommunicatiewet art. 11.7) apply
   to email sent to an organisation's published address, and whether our footer and opt-out meet them.

Questions about the kit: Manuel Suhrcke, Head of AI. The code is in this repo; `tools/pipeline.py`
(`add-contact`) and `tools/send.py` enforce the rules above.
