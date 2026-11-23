# Setup, once per tenant (about 45 minutes)

Until steps 1-4 are done, `send.py` holds everything ("BLOCKS SENDING" in `send.py status`).
Drafting and research work without them.

## 0. Python packages

```
pip install -r requirements.txt
```

## 1. The sending inbox

The new 180dc.org inbox. Then in `tenants/180dc-delft-rotterdam/tenant.yaml` set `sender.address`
(and `sender.name` if someone other than Manuel signs).

Before the first send, check in that inbox's Gmail settings that the display name is a person's
name, and that the signature is empty (the kit adds its own footer).

## 2. Gmail API login, without the 7-day expiry

Signed in as the new inbox:

1. https://console.cloud.google.com, create a project (for example "180dc-outreach"). If 180dc.org
   does not let members create projects, ask the person who ran the earlier script, or the domain admin.
2. APIs & Services -> Library -> enable **Gmail API**.
3. OAuth consent screen -> User type **Internal**. Internal apps on a Workspace domain do not expire
   after 7 days, which is what broke the job kit. (If Internal is greyed out, the domain admin must
   allow it; External + Testing works but dies every 7 days.)
4. Credentials -> Create credentials -> OAuth client ID -> **Desktop app** -> download the JSON to
   `tenants/180dc-delft-rotterdam/private/gmail_credentials.json`.
5. `python tools/gmail_draft.py auth`. The browser opens once: **choose the 180DC account** in the
   account picker, not a personal Gmail. Your Claude account can be on any email; this login is the kit's own.
6. `python tools/gmail_draft.py auth-status --check` must print `inbox: <the 180DC address> (matches tenant.yaml)`.
   If it says `WRONG_ACCOUNT`, repeat step 5 and pick the other account. Drafting and sending refuse
   to run until the two match.

## 3. Booking link

Google Calendar of the inbox -> Create -> Appointment schedule, 30 minutes, the hours you can take
calls, buffer 15 minutes. Copy the public link into `booking_link` in tenant.yaml.

## 4. Shared registry on monday.com

1. In the branch workspace create a board **Outreach registry** with columns:
   Domain (Text), Owner (Text), Status (Text), Last contact (Date), Blocked until (Date).
   Tell the branch: before anyone writes to an organisation, they add a row (domain, their name,
   status, today, today + 90 days).
2. Token: monday avatar -> Developers -> My access tokens -> copy. Save it as
   `tenants/180dc-delft-rotterdam/private/monday_token.txt` (gitignored), or set `MONDAY_API_TOKEN`.
3. Put the board id (from the board URL) into `registry.monday.board_id`, then run
   `python tools/registry.py test-monday`. It prints every column's id; copy them into
   `registry.monday.columns`.
4. Set `registry.backend: monday`. From now on an unreachable monday holds all sending (fail closed).
5. Try it: `python tools/registry.py check example.org` should print `free: example.org`.

The monday code has not run against a real board yet. Step 3 is the first test; send Claude the output
if anything fails.

## 5. Ledger and templates

- Read `tenants/180dc-delft-rotterdam/ledger.yaml`. Confirm TR-EVIDENCE's wording, and set
  `BR-PAST-WORK` to `usable: true` only when the branch confirms it.
- Have the legal team read the footer in tenant.yaml (identity, address source, opt-out).

## 6. The scheduled run

```
schtasks /Create /TN "OutreachClientRun-180dc" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:00 ^
  /TR "powershell -ExecutionPolicy Bypass -File C:\Users\User\Desktop\180dc-outreach\tools\daily_run.ps1"
```

Then in Task Scheduler -> the task -> Conditions: tick **Wake the computer to run this task**. The
send loop runs until 16:30, so the PC must stay on and awake during the day (power plan: never sleep
on mains). If that is not realistic, the cloud plan in the job kit's `docs/cloud-runtime.md` applies.

First week: run `powershell -ExecutionPolicy Bypass -File tools\daily_run.ps1 -NoSend` by hand once
and read the report before the task sends anything.

## 7. Target list

`tenants/180dc-delft-rotterdam/targets.yaml` needs candidates (name, website, city, country, segment,
source). This is open item 1 in `docs/build-spec.md`.
