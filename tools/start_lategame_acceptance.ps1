param([Parameter(Mandatory=$true)][int]$Build,[switch]$Reload,[switch]$Watch)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($Reload) {
  $checkpoint = Get-Content -LiteralPath (Join-Path $root 'outputs\lategame-save-checkpoint.json') -Raw | ConvertFrom-Json
  $source = 'C:\Users\Jordan\Documents\Timberborn\ExperimentalSaves\Industrial Acceptance\Lategame acceptance - main.timber'
  if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ine $checkpoint.SourceSha256) {
    throw 'Late-game reload source differs from the captured native main save.'
  }
}
$kind = if ($Reload) { 'reload' } else { 'main' }
$flag = if ($Reload) { '-deepFrontierLategameReload' } else { '-deepFrontierLategame' }
$log = Join-Path $root "outputs\lategame-$kind$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance',$flag,'-logFile',('"'+$log+'"')
)
Write-Output "Requested marked late-game $kind. Log: $log"
if ($Watch) { & (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done "^\[DeepFrontier Lategame\] COMPLETE $($kind.ToUpper()) .* AND SAVED$"; exit $LASTEXITCODE }
