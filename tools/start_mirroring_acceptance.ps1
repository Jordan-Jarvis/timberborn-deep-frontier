param([Parameter(Mandatory=$true)][int]$Build)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'A game process is already running; finish the current session before launching the explicit mirroring fixture.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$log = Join-Path $root "outputs/mirroring$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierLoadAcceptance','-deepFrontierMirrorAcceptance','-logFile',('"'+$log+'"')
)
Write-Output "Requested exact native mirroring fixture. Log: $log"
