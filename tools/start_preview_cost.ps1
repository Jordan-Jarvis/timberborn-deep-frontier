param(
  [Parameter(Mandatory=$true)][string]$Label,
  # Quiet world: a new Iron Teeth game (settlement "Memory Test") on a map with open flat ground.
  [string]$NewGame = 'user:Deep Frontier - Plains',
  # Busy world instead: load this save copy (it must lie in ExperimentalSaves\Memory Test). The
  # colony runs at speed 1 during the probe (MemoryLoadProbe), so construction, tree cutting
  # and navmesh changes go on while previews are measured.
  [string]$Save,
  [double]$CeilingGB = 13,
  # Measure every Deep Frontier building, not only the heavy ones and the vanilla references.
  [switch]$All
)
# Native placement-preview cost probe (Scripts/PreviewCostAcceptance.cs), unattended: the
# main-menu loader starts the game (-deepFrontierLoadAcceptance with -deepFrontierNewGame or
# -deepFrontierLoadSave, MemoryLoadProbe.cs/IndustrialAcceptanceLoader.cs); the probe drives
# PreviewPlacer.ShowPreviews still and moving, with the preview caches off (native) and on,
# and logs '[DeepFrontier PreviewCost]' lines. Nothing is placed. The memory sampler closes
# the game above -CeilingGB; the watcher closes it when the probe finishes.
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'A game process is already running; finish the current session before launching the preview cost probe.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$log = Join-Path $root "outputs/preview-cost-$Label.log"
$csv = Join-Path $root "outputs/preview-cost-$Label-memory.csv"
$world = @('-deepFrontierLoadAcceptance')
if ($Save) {
  $testDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ExperimentalSaves\Memory Test'
  $Save = [IO.Path]::GetFullPath($Save)
  if ((Split-Path -Parent $Save) -ne $testDir) { throw "Only copies in $testDir are loaded: $Save" }
  if (-not (Test-Path -LiteralPath $Save -PathType Leaf)) { throw "No save at $Save" }
  $world += @('-deepFrontierLoadSave',('"' + $Save + '"'))
} else {
  $world += @('-deepFrontierNewGame',('"' + $NewGame + '"'))
}
if ($All) { $world += '-deepFrontierPreviewCostAll' }
$sampler = Start-Process -FilePath 'powershell' -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + (Join-Path $PSScriptRoot 'sample_timberborn_memory.ps1') + '"'),
  '-Out',('"' + $csv + '"'),'-CeilingGB',$CeilingGB,'-Minutes','40')
Write-Output "Sampler pid $($sampler.Id) -> $csv (ceiling $CeilingGB GB)"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments (@(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080') + $world +
  @('-deepFrontierPreviewCost','-logFile',('"'+$log+'"')))
Write-Output "Requested preview cost probe ($(if ($Save) { "save $Save" } else { "new game on $NewGame" })). Log: $log"
& (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier PreviewCost\] ALL MEASURED' -TimeoutMinutes 35
$code = $LASTEXITCODE
if (-not $sampler.HasExited) { Stop-Process -Id $sampler.Id }
Get-Content -LiteralPath $csv | Select-Object -Last 3
exit $code
