# Unattended daily run for one tenant. Register as a scheduled task (docs/setup.md), weekdays 07:00,
# so it never overlaps the job-search kit's 07:45 run.
#
#   1. Preflight: is the Gmail login alive? If not, alert and stop (no silent failure).
#   2. One fresh Claude session prepares the day: sync, follow-ups, new first emails, all marked
#      ready or needs_approval. It cannot send: send.py run and approve are denied to it.
#   3. tools/send.py run sends what is ready through the send window, with random gaps.
#   4. The report is mailed to the sending inbox. Any failure writes an alert file to the Desktop.
#
# Run by hand:      powershell -ExecutionPolicy Bypass -File tools\daily_run.ps1
# Prepare only:     powershell -ExecutionPolicy Bypass -File tools\daily_run.ps1 -NoSend

param([switch]$NoSend, [string]$Tenant = "180dc-delft-rotterdam")

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:OUTREACH_TENANT = $Tenant
$state = Join-Path $root "tenants\$Tenant\state"
$runs = Join-Path $state "runs"
New-Item -ItemType Directory -Force $runs | Out-Null
$log = Join-Path $runs ("{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))
$alertFile = Join-Path ([Environment]::GetFolderPath("Desktop")) "ALERT-outreach-$Tenant.txt"

function Write-Log($text) { "$(Get-Date -Format s) $text" | Out-File -FilePath $log -Append -Encoding utf8 }
function Send-Alert($text) {
  Write-Log "ALERT: $text"
  "$(Get-Date -Format s) $text" | Out-File -FilePath $alertFile -Append -Encoding utf8
  try { & msg $env:USERNAME /TIME:0 "Outreach kit ($Tenant): $text" 2>$null } catch {}
}

Write-Log "=== run started ==="

# 1. preflight
& python tools/gmail_draft.py auth-status --check 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
if ($LASTEXITCODE -ne 0) {
  Send-Alert "Gmail login is dead. Run: python tools/gmail_draft.py auth (in $root). Nothing was prepared or sent."
  exit 3
}

# 2. the session. The prompt must not contain double quotes: Windows PowerShell 5.1 does not escape
#    them when it passes an argument to a program, and the job kit's prompt was cut off that way.
$prompt = @'
You are the unattended daily run of the client outreach kit, tenant TENANT_NAME. Nobody is watching and nobody can answer questions. Read CLAUDE.md and docs/runbook.md, then do the section called The daily run, steps 1 to 8, for today. You never send: tools/send.py ready is the end of your work on an email. Never answer a human reply, never approve, never touch LinkedIn. If a step fails twice, write the failure into the daily report and go on to the next step. End by printing the report.
'@
$prompt = $prompt.Replace("TENANT_NAME", $Tenant)
if ($NoSend) { $prompt += " Today is a prepare-only run." }
if ($prompt.Contains('"')) { Send-Alert "run prompt contains a double quote; fix daily_run.ps1"; exit 1 }

$allowed = @(
  "Read", "Write", "Edit", "Glob", "Grep", "Agent", "WebFetch", "WebSearch",
  "Bash(python tools/*)", "Bash(git add:*)", "Bash(git commit:*)", "Bash(git status:*)", "Bash(git diff:*)"
)
$denied = @("Bash(python tools/send.py run:*)", "Bash(python tools/send.py approve:*)", "Bash(git push:*)")

& claude -p $prompt --model sonnet --allowedTools $allowed --disallowedTools $denied 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
if ($LASTEXITCODE -ne 0) { Send-Alert "the preparation session exited with code $LASTEXITCODE; see $log" }

# 3. sending, plain script, no model
if (-not $NoSend) {
  Write-Log "send loop started"
  & python tools/send.py run 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
  if ($LASTEXITCODE -ne 0) { Send-Alert "send.py run exited with code $LASTEXITCODE; see $log" }
  if (Test-Path (Join-Path $state "STOP")) {
    Send-Alert ("sending is paused: " + (Get-Content (Join-Path $state "STOP") -Raw))
  }
}

# 4. report
$report = Join-Path $state "daily-report.md"
if (Test-Path $report) {
  "`n## Send loop`n" | Out-File -FilePath $report -Append -Encoding utf8
  & python tools/send.py status | Out-File -FilePath $report -Append -Encoding utf8
  & python tools/gmail_draft.py mail-self --body $report 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
} else {
  Send-Alert "no daily report was written; see $log"
}
Write-Log "=== run ended ==="
