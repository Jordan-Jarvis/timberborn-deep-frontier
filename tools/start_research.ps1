param([Parameter(Mandatory=$true)][int]$Build,[switch]$Reload)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$kind = if ($Reload) { 'reload' } else { 'run' }
$flag = if ($Reload) { '-deepFrontierResearchReload' } else { '-deepFrontierResearch' }
$log = Join-Path $root "outputs\research-$kind$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance',$flag,'-logFile',('"'+$log+'"')
)
Write-Output "Requested marked research $kind. Log: $log"
