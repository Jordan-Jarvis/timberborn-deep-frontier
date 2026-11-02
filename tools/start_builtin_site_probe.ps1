param(
  [Parameter(Mandatory=$true)][string]$Label,
  # Map of the Iron Teeth new game: builtin:<name> or user:<name> (settlement "Memory Test"; the run makes
  # autosaves there).
  [Parameter(Mandatory=$true)][string]$NewGame,
  # "Template@x,y,z,Orientation,place|fill;..." (src/DeepFrontier/Scripts/MapSetup/BuiltinSiteProbe.cs);
  # "none" for screenshots only.
  [string]$Checks = 'none',
  # "label@x,y,z;..." extra camera targets.
  [string]$Shots = '',
  [int]$TimeoutMinutes = 20
)
# New game (on a built-in map with the Deep Frontier map setup), then native preview checks of chosen sites
# and screenshots (outputs/site-probe/<Label>/). The log keeps the map setup's "placed" lines and the text
# of every startup dialog the acceptance loader dismissed. Never loads a user save.
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'A game process is already running.' }
if ($Label -match '[\\/:*?"<>|\s]') { throw "Label must be a plain file-name part: $Label" }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$log = Join-Path $root "outputs/site-probe-$Label.log"
$arguments = @('-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierLoadAcceptance','-deepFrontierNewGame',('"' + $NewGame + '"'),
  '-deepFrontierSiteProbe',('"' + $Checks + '"'),'-deepFrontierSiteProbeLabel',$Label)
if ($Shots) { $arguments += @('-deepFrontierSiteProbeShots',('"' + $Shots + '"')) }
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments ($arguments + @('-logFile',('"' + $log + '"')))
Write-Output "Requested the site probe on $NewGame. Log: $log"
& (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier SiteProbe\] COMPLETE' -TimeoutMinutes $TimeoutMinutes
$code = $LASTEXITCODE
Get-Content -LiteralPath $log | Where-Object { $_ -match '^\[DeepFrontier (MapSetup|SiteProbe)\]|Dismissed startup panel' } | ForEach-Object { $_.Substring(0, [Math]::Min(400, $_.Length)) }
exit $code
