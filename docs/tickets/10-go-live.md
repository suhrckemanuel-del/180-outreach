# 10 Go live: first supervised run, then the schedule

**Before the first real send.**
- [ ] Manuel confirms the TR-EVIDENCE wording in `ledger.yaml`.
- [ ] The legal team has read the footer in `tenant.yaml` (identity, where the address came from, opt-out).
- [ ] The consent screen is **Internal** (otherwise the Gmail login dies on about 28 Nov).
- [ ] The 180DC inbox has Manuel's name as display name and an empty signature.
- [ ] Booking page checked from a phone (ticket 02).
- [ ] The repo is committed.

**First run, together.** `powershell -ExecutionPolicy Bypass -File tools\daily_run.ps1 -NoSend`, read the
report and the drafts, approve, then `python tools/send.py run --max 5` by hand and look at the five
sent emails in the 180DC Sent folder.

**Then the schedule.** Register the task (docs/setup.md step 6), weekdays 07:00, wake the PC, power
plan never sleeps on mains.

**Done when.** The task has run unattended for three weekdays and the reports arrived in the inbox.
