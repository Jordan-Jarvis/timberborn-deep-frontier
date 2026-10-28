param([Parameter(Mandatory=$true)][int]$Build,[switch]$Watch)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$log = Join-Path $root "outputs\hospital-run$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance','-deepFrontierHospitalAcceptance','-logFile',('"'+$log+'"')
)
Write-Output "Requested the marked hospital fixture. Log: $log"
if ($Watch) { & (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier Hospital\] ALL CARE, STAFF, POWER, CAPACITY AND ACCESS CHECKS PASSED AND SAVED$'; exit $LASTEXITCODE }
