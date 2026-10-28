param(
  [Parameter(Mandatory=$true)][int]$Build,
  [ValidateSet('main','preparing','flight','refurbishing')][string]$Checkpoint='main',
  # Opt-in: launches the final mission and completes the native wonder, which also
  # records a first-time map completion in the player's profile outside the save.
  [switch]$Ending,
  # Wait for the harness outcome, then close the game (tools/watch_acceptance_log.ps1).
  [switch]$Watch
)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$saves = 'C:\Users\Jordan\Documents\Timberborn\ExperimentalSaves\Industrial Acceptance'
if ($Checkpoint -eq 'main') {
  # The rocket sequence runs on the verified late-game layout save.
  $check = Get-Content -LiteralPath (Join-Path $root 'outputs\lategame-save-checkpoint.json') -Raw | ConvertFrom-Json
  if ((Get-FileHash -LiteralPath (Join-Path $saves 'Lategame acceptance - main.timber') -Algorithm SHA256).Hash -ine $check.SourceSha256) {
    throw 'Lategame acceptance - main differs from the captured late-game layout save.'
  }
  $flag = '-deepFrontierLategameRocket'
} else {
  $check = Get-Content -LiteralPath (Join-Path $root 'outputs\lategame-rocket-checkpoints.json') -Raw | ConvertFrom-Json
  if ((Get-FileHash -LiteralPath (Join-Path $saves "Lategame rocket - $Checkpoint.timber") -Algorithm SHA256).Hash -ine $check.$Checkpoint) {
    throw "Lategame rocket - $Checkpoint differs from the captured rocket checkpoint."
  }
  $flag = '-deepFrontierLategameRocket' + $Checkpoint.Substring(0,1).ToUpper() + $Checkpoint.Substring(1)
}
if ($Ending -and $Checkpoint -ne 'main') { throw '-Ending applies only to the main rocket sequence.' }
$extra = if ($Ending) { @('-deepFrontierRocketEnding') } else { @() }
$log = Join-Path $root "outputs\lategame-rocket-$Checkpoint$Build.log"
$arguments = @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance',$flag
) + $extra + @('-logFile',('"'+$log+'"'))
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments $arguments
Write-Output "Requested marked rocket $Checkpoint run$(if ($Ending) {' with the opt-in story ending'}). Log: $log"
if ($Watch) { & (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier Rocket\] COMPLETE '; exit $LASTEXITCODE }
