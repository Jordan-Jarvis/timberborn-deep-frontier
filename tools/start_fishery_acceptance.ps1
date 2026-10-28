param([ValidateSet('run','reload','continuity','bootstrap','hatchery')][string]$Mode = 'run', [Parameter(Mandatory=$true)][int]$Build)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit before the fresh test starts.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$modeFlag = switch ($Mode) {
  'run' { '-deepFrontierFisheryAcceptance' }
  'reload' { '-deepFrontierFisheryReload' }
  'continuity' { '-deepFrontierAquacultureContinuity' }
  'bootstrap' { '-deepFrontierAquacultureBootstrap' }
  'hatchery' { '-deepFrontierHatcheryAcceptance' }
}
$log = Join-Path $root "outputs\fishery-$Mode$Build.log"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierArtReview','-deepFrontierLoadAcceptance',$modeFlag,'-logFile',('"'+$log+'"')
)
Write-Output "Requested the marked fishery $Mode fixture. Log: $log"
