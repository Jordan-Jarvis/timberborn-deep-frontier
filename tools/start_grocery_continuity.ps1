param([Parameter(Mandatory=$true)][int]$Build)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not (Test-Path -LiteralPath (Join-Path $root 'outputs/grocery-reload-expectations.json'))) { throw 'Capture the successful native grocery save expectations first.' }
$log = Join-Path $root "outputs\grocery-reload$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance','-deepFrontierGroceryReload','-logFile',('"'+$log+'"')
)
Write-Output "Requested the marked grocery continuation. Log: $log"
