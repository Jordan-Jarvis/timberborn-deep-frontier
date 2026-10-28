# Watches a marked acceptance run started by tools/launch_timberborn.ps1 (which removes a
# previous log of the same name before launching) until it finishes,
# then closes the game (window close, as the user would) and exits 0 only on the harness's
# completion line. Outcomes, checked every 5 s:
#   crash    Timberborn's "First uncaught exception" handler (the "Uh oh... a bug" screen)
#   failed   a "[DeepFrontier <harness>] FAILED"/"INCOMPLETE" line
#   done     the -Done regex (each launcher passes its harness's saved/complete line)
#   stuck    no "Modded:" line 180 s after the log started (the Mods screen or Steam blocked)
#   exited   the game process ended first
#   timeout  -TimeoutMinutes elapsed
# Startup panels dismissed by the mod (AcceptanceStartupPanels.cs, needs a build that
# contains it) and panels left for the harness are listed from the log.
param(
  [Parameter(Mandatory=$true)][string]$Log,
  [Parameter(Mandatory=$true)][string]$Done,
  [int]$TimeoutMinutes = 120,
  # Leave the game running after a 'done' outcome (for manual inspection).
  [switch]$KeepOpen
)
$ErrorActionPreference = 'Stop'
$start = Get-Date
$fresh = $false
$freshSince = $null

function Read-Log {
  $stream = [System.IO.File]::Open($Log, 'Open', 'Read', 'ReadWrite')
  try { (New-Object System.IO.StreamReader($stream)).ReadToEnd() } finally { $stream.Dispose() }
}
function Get-Game { Get-Process -Name Timberborn -ErrorAction SilentlyContinue | Select-Object -First 1 }

$outcome = $null; $detail = ''; $text = ''
while (-not $outcome) {
  Start-Sleep -Seconds 5
  $game = Get-Game
  if (Test-Path -LiteralPath $Log) {
    if (-not $fresh) { $fresh = $true; $freshSince = Get-Date }
    if ($fresh) { $text = Read-Log }
  }
  if ($fresh) {
    $lines = $text -split "`r?`n"
    $crash = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like 'First uncaught exception*') { $crash = $i; break } }
    if ($crash -ge 0) {
      $outcome = 'crash'
      $detail = ($lines[($crash+1)..([Math]::Min($crash+3, $lines.Count-1))] | Where-Object { $_.Trim() } | Select-Object -First 1)
      break
    }
    $failed = $lines | Where-Object { $_ -match '^\[DeepFrontier [^\]]+\] (FAILED|INCOMPLETE)' } | Select-Object -First 1
    if ($failed) { $outcome = 'failed'; $detail = $failed; break }
    $complete = $lines | Where-Object { $_ -match $Done } | Select-Object -First 1
    if ($complete) { $outcome = 'done'; $detail = $complete; break }
    if (-not ($lines | Where-Object { $_ -like 'Modded:*' }) -and ((Get-Date) - $freshSince).TotalSeconds -gt 180) {
      $outcome = 'stuck'; $detail = 'No mods were loaded 180 s after the log started: the Mods screen or a Steam prompt is blocking.'; break
    }
  } elseif (((Get-Date) - $start).TotalSeconds -gt 180) {
    $outcome = 'stuck'; $detail = "No fresh log at $Log 180 s after the watch started."; break
  }
  if (-not $game) { $outcome = 'exited'; $detail = 'The Timberborn process ended before the harness finished.'; break }
  if (((Get-Date) - $start).TotalMinutes -gt $TimeoutMinutes) { $outcome = 'timeout'; $detail = "No outcome after $TimeoutMinutes minutes."; break }
}

foreach ($line in ($text -split "`r?`n" | Where-Object { $_ -like '`[DeepFrontier Acceptance`]*panel*' })) {
  Write-Output "panel: $line"
}
Write-Output "outcome: $outcome"
Write-Output "detail: $detail"

$game = Get-Game
if ($game -and -not ($outcome -eq 'done' -and $KeepOpen)) {
  if ($outcome -eq 'done') { Start-Sleep -Seconds 10 }
  [void]$game.CloseMainWindow()
  # A window close waits for a blocking scene load to finish.
  if (-not $game.WaitForExit(300000)) { throw "Timberborn (pid $($game.Id)) did not close within 5 minutes; close it manually." }
  Write-Output 'Closed Timberborn.'
}
exit ([int]($outcome -ne 'done'))
