# Loads one save unattended under the memory sampler and runs it for 180 s of game time
# (src/DeepFrontier/Scripts/MemoryLoadProbe.cs). The save must be a copy in the test
# settlement "Memory Test"; the user's own saves are never loaded by this script.
#
#   powershell -File tools/start_memory_load.ps1 -Build 128 -Label 128 -Trace
#   powershell -File tools/start_memory_load.ps1 -Build 131 -Label new66 -NewGame "user:Deep Frontier - Plains (Hard, Radioactive Spring)" -SaveAs "new66"
#   powershell -File tools/start_memory_load.ps1 -Build 177 -Label leg-inspect -Save "<Memory Test>\leg Day 20-4 copy.timber" -SaveInspect
#
# -NewGame starts an Iron Teeth new game on a map (user:<name> or builtin:<name>) instead of
# loading -Save; -SaveAs saves the game into "Memory Test" after the run.
#
# -Trace adds -deepFrontierMemoryTrace (MemoryTrace.cs): per-singleton Load/PostLoad and
# first-tick memory lines and a 200 ms private-bytes watchdog naming the running method.
param(
  [Parameter(Mandatory=$true)][int]$Build,
  [Parameter(Mandatory=$true)][string]$Label,
  [string]$Save = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ExperimentalSaves\Memory Test\asdf copy.timber'),
  [double]$CeilingGB = 8,
  [string]$NewGame,
  [string]$SaveAs,
  # Test switch: run without Scripts/PrefabMeshRelease.cs (before/after comparisons).
  [switch]$KeepPrefabMeshes,
  [switch]$Trace,
  # Also run Scripts/PileVisualizationProbe.cs (DeepOre/DeepAlloy pile visuals; needs -NewGame).
  [switch]$PileProbe,
  # Also run Scripts/SaveInspectionProbe.cs: a read-only report on the loaded copy's FishHatchery,
  # FisheryWorks and Greenhouse (outputs/save-inspect-<save>.json). Not with -NewGame or -SaveAs.
  [switch]$SaveInspect,
  # Also run Scripts/ShowcaseCapture.cs: UI hidden, Workshop screenshots of Deep Frontier buildings (outputs/showcase).
  [switch]$Showcase,
  # Game seconds to run instead of 180 (SaveInspect runs at speed 3, so wall time is a third).
  [double]$RunSeconds = 0
)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$testDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ExperimentalSaves\Memory Test'
$Save = [IO.Path]::GetFullPath($Save)
if ((Split-Path -Parent $Save) -ne $testDir) { throw "Only copies in $testDir are loaded: $Save" }
if (-not (Test-Path -LiteralPath $Save -PathType Leaf)) { throw "No save at $Save" }
$log = Join-Path $root "outputs\memory-load-$Label.log"
$csv = Join-Path $root "outputs\memory-load-$Label.csv"
$sampler = Start-Process -FilePath 'powershell' -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + (Join-Path $PSScriptRoot 'sample_timberborn_memory.ps1') + '"'),
  '-Out',('"' + $csv + '"'),'-CeilingGB',$CeilingGB,'-Minutes','20')
Write-Output "Sampler pid $($sampler.Id) -> $csv (ceiling $CeilingGB GB)"
$arguments = @('-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080','-deepFrontierLoadAcceptance')
if ($NewGame) { $arguments += @('-deepFrontierNewGame',('"' + $NewGame + '"')) } else { $arguments += @('-deepFrontierLoadSave',('"' + $Save + '"')) }
if ($SaveAs) { $arguments += @('-deepFrontierSaveAs',('"' + $SaveAs + '"')) }
if ($Trace) { $arguments += '-deepFrontierMemoryTrace' }
if ($PileProbe) { $arguments += '-deepFrontierPileProbe' }
if ($SaveInspect) {
  if ($NewGame -or $SaveAs) { throw '-SaveInspect is read-only: it loads -Save and never takes -NewGame or -SaveAs' }
  $arguments += '-deepFrontierSaveInspect'
}
if ($Showcase) {
  if ($NewGame -or $SaveAs) { throw '-Showcase is read-only: it loads -Save and never takes -NewGame or -SaveAs' }
  $arguments += '-deepFrontierShowcase'
}
if ($RunSeconds -gt 0) { $arguments += @('-deepFrontierRunSeconds',$RunSeconds.ToString([Globalization.CultureInfo]::InvariantCulture)) }
if ($KeepPrefabMeshes) { $arguments += '-deepFrontierKeepPrefabMeshes' }
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments ($arguments + @('-logFile',('"' + $log + '"')))
Write-Output "Build ${Build}: $(if ($NewGame) { "new game on $NewGame" } else { "loading $Save" }). Log: $log"
& (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier MemoryLoad\] COMPLETE' -TimeoutMinutes 25
$code = $LASTEXITCODE
if (-not $sampler.HasExited) { Stop-Process -Id $sampler.Id }
Get-Content -LiteralPath $csv | Select-Object -Last 3
exit $code
