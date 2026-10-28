param([Parameter(Mandatory=$true)][int]$Build,[switch]$Reload)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($Reload) {
  $checkpoint = Get-Content -LiteralPath (Join-Path $root 'outputs\hydro-save-checkpoint.json') -Raw | ConvertFrom-Json
  $source = 'C:\Users\Jordan\Documents\Timberborn\ExperimentalSaves\Industrial Acceptance\Hydro turbine - verified.timber'
  if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ine $checkpoint.SourceSha256) {
    throw 'Hydro reload source differs from the captured native checkpoint.'
  }
}
$kind = if ($Reload) { 'reload' } else { 'run' }
$flag = if ($Reload) { '-deepFrontierHydroReload' } else { '-deepFrontierHydro' }
$log = Join-Path $root "outputs\hydro-$kind$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance',$flag,'-logFile',('"'+$log+'"')
)
Write-Output "Requested disposable native turbine $kind. Log: $log"
