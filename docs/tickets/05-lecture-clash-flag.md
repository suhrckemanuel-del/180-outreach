# 05 Lecture-clash flag for booked calls

**Problem.** The booking hours avoid only the Monday and Thursday 11:00 tutorials (Manuel's rule,
`tenant.yaml` call_availability). A call can land on a lecture, and Manuel wants to be told so he can
decide to skip it.

**Do.** Manuel shares the 180DC calendar with his personal account (see all event details). Then a
session with the Google Calendar connector can list the week's booked calls and the Erasmus timetable
(`3n9j3jhq6bl0a4tfe1vavns47verd5cq@import.calendar.google.com`) and report overlaps:
"Thu 13:00 call with Stichting X clashes with the Welfare State tutorial: skip it?"

Open: whether the unattended `claude -p` run can use the claude.ai calendar connector. If not, add
`calendar.readonly` to the kit's own Google login and read both calendars from a script.

**Done when.** A clash shows up in the daily report the morning after the booking.
