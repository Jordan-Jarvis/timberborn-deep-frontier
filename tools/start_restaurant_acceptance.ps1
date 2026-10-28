param([ValidateSet('run','reload')][string]$Mode = 'run', [Parameter(Mandatory=$true)][int]$Build)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'Wait for the previous Timberborn process to exit before starting a fresh test.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$modeFlag = if ($Mode -eq 'reload') { '-deepFrontierRestaurantReload' } else { '-deepFrontierRestaurantAcceptance' }
$log = Join-Path $root "outputs\restaurant-$Mode$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance',$modeFlag,'-logFile',('"'+$log+'"')
)
Write-Output "Requested the exact $Mode fixture through Steam. Log: $log"
