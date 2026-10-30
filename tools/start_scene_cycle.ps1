# Several game scenes in one Timberborn process (src/DeepFrontier/Scripts/SceneCycleAcceptance.cs):
# load a save, return to the main menu, start a new game, and so on, as a player does. Every main
# menu requires the native water and terrain materials exactly as before the first game (the
# radiation renderer's shader swap restored), every game requires the radiation variants on them.
#
#   pwsh tools/start_scene_cycle.ps1 -Label 223
#
# The save steps load a copy of the newest autosave in "Memory Test" ("scene cycle copy.timber",
# made here and removed afterwards); the new games are Iron Teeth games in "Memory Test" that are
# never saved (the harness leaves each game with native OpenMainMenu, which skips the autosave).
# Every file in Memory Test is recorded first; afterwards a file the run removed is restored with
# its original time and a file it added is reported. Log: outputs/scene-cycle-<Label>.log.
param(
  [Parameter(Mandatory=$true)][string]$Label,
  [string]$NewGameMap = 'builtin:Canyon',
  [int]$Cycles = 2,
  [int]$TimeoutMinutes = 30
)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
if ($Label -match '[\\/:*?"<>|\s]') { throw "Label must be a plain file-name part: $Label" }
if ($Cycles -lt 1) { throw '-Cycles must be at least 1' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$testDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ExperimentalSaves\Memory Test'
$newest = Get-ChildItem -LiteralPath $testDir -Filter '*.autosave.timber' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $newest) { throw "No autosave in $testDir to copy" }
$backup = Join-Path ([IO.Path]::GetTempPath()) "df-scene-cycle-$Label"
if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Recurse -Force }
New-Item -ItemType Directory -Path $backup | Out-Null
$before = @{}
foreach ($file in Get-ChildItem -LiteralPath $testDir -File) {
  Copy-Item -LiteralPath $file.FullName -Destination $backup
  $before[$file.Name] = $file.LastWriteTimeUtc
}
Write-Output "Backed up $($before.Count) files of Memory Test to $backup"
$copy = Join-Path $testDir 'scene cycle copy.timber'
if (Test-Path -LiteralPath $copy) { throw "$copy already exists" }
Copy-Item -LiteralPath $newest.FullName -Destination $copy
# Older than every user save, so Continue never opens it.
(Get-Item -LiteralPath $copy).LastWriteTime = [datetime]'2026-10-01 12:00:00'
$steps = @()
for ($i = 0; $i -lt $Cycles; $i++) { $steps += "save:$copy"; $steps += $NewGameMap }
$log = Join-Path $root "outputs\scene-cycle-$Label.log"
try {
  & (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
    '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
    '-deepFrontierLoadAcceptance','-deepFrontierSceneCycle',('"' + ($steps -join ';') + '"'),'-logFile',('"' + $log + '"'))
  Write-Output "Scene cycle of $($steps.Count) games from $($newest.Name). Log: $log"
  & (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier SceneCycle\] COMPLETE' -TimeoutMinutes $TimeoutMinutes
  $code = $LASTEXITCODE
} finally {
  while (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 2 }
  Remove-Item -LiteralPath $copy
  foreach ($name in $before.Keys) {
    $path = Join-Path $testDir $name
    if (-not (Test-Path -LiteralPath $path)) {
      Copy-Item -LiteralPath (Join-Path $backup $name) -Destination $path
      (Get-Item -LiteralPath $path).LastWriteTimeUtc = $before[$name]
      Write-Output "Restored $name (the run removed it)"
    }
  }
  foreach ($file in Get-ChildItem -LiteralPath $testDir -File | Where-Object { -not $before.ContainsKey($_.Name) }) {
    Write-Output "Added by the run: $($file.Name) ($($file.LastWriteTime))"
  }
}
Get-Content -LiteralPath $log | Where-Object { $_ -like '`[DeepFrontier SceneCycle`]*' -or $_ -like '*DeepFrontier MapSetup*' }
exit $code
