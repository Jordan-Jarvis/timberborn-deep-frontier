param([Parameter(Mandatory=$true)][int]$Build,[switch]$Reload,[switch]$PowerLines)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$kind = if ($Reload) { 'reload' } else { 'run' }
$flag = if ($PowerLines) {
  if ($Reload) { '-deepFrontierFactoryPowerLinesReload' } else { '-deepFrontierFactoryPowerLines' }
} else { if ($Reload) { '-deepFrontierFactoryTransportReload' } else { '-deepFrontierFactoryTransport' } }
$test = if ($PowerLines) { 'factory-power-lines' } else { 'factory-transport' }
$log = Join-Path $root "outputs\$test-$kind$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance',$flag,'-logFile',('"'+$log+'"')
)
Write-Output "Requested marked factory transport $kind. Log: $log"
