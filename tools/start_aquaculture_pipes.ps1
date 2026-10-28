param([Parameter(Mandatory=$true)][int]$Build)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$log = Join-Path $root "outputs\aquaculture-pipes$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance','-deepFrontierAquaculturePipes','-logFile',('"'+$log+'"')
)
Write-Output "Requested marked aquaculture pipe acceptance. Log: $log"
