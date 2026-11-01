# Radiation shader variants against the native water and terrain shaders, in game
# (src/DeepFrontier/Scripts/Radiation/WaterShadingProbe.cs): loads a copy of a save in "Memory Test",
# captures clean water and badwater with the variants, with the native shaders and with the
# radiation keywords forced on, then radioactive water and irradiated soil added beside the clean
# water. Screenshots: outputs/water-shading/<Label>/. Log: outputs/water-shading-<Label>.log.
#
#   pwsh tools/start_water_shading.ps1 -Label before
#   pwsh tools/start_water_shading.ps1 -Label after -Save "<Memory Test>\some save.timber"
#
# -Save defaults to the newest autosave in Memory Test. The copy ("water shading copy.timber") is
# removed afterwards. Every file in Memory Test is recorded first; a file the run removed (autosave
# rotation) is restored with its original time, and a file the run added is backdated to before
# every user save so Continue keeps opening the user's own save.
param(
  [Parameter(Mandatory=$true)][string]$Label,
  [string]$Save,
  [int]$TimeoutMinutes = 20
)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
if ($Label -match '[\\/:*?"<>|\s]') { throw "Label must be a plain file-name part: $Label" }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$testDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ExperimentalSaves\Memory Test'
if (-not $Save) {
  $newest = Get-ChildItem -LiteralPath $testDir -Filter '*.autosave.timber' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $newest) { throw "No autosave in $testDir to copy" }
  $Save = $newest.FullName
}
$Save = [IO.Path]::GetFullPath($Save)
if ((Split-Path -Parent $Save) -ne $testDir) { throw "Only saves in $testDir are copied: $Save" }
if (-not (Test-Path -LiteralPath $Save -PathType Leaf)) { throw "No save at $Save" }
$backup = Join-Path ([IO.Path]::GetTempPath()) "df-water-shading-$Label"
if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Recurse -Force }
New-Item -ItemType Directory -Path $backup | Out-Null
$before = @{}
foreach ($file in Get-ChildItem -LiteralPath $testDir -File) {
  Copy-Item -LiteralPath $file.FullName -Destination $backup
  $before[$file.Name] = $file.LastWriteTimeUtc
}
Write-Output "Backed up $($before.Count) files of Memory Test to $backup"
$copy = Join-Path $testDir 'water shading copy.timber'
if (Test-Path -LiteralPath $copy) { throw "$copy already exists" }
Copy-Item -LiteralPath $Save -Destination $copy
# Older than every user save, so Continue never opens it.
$old = [datetime]'2026-10-01 12:00:00'
(Get-Item -LiteralPath $copy).LastWriteTime = $old
$log = Join-Path $root "outputs\water-shading-$Label.log"
try {
  & (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
    '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
    '-deepFrontierLoadAcceptance','-deepFrontierLoadSave',('"' + $copy + '"'),'-deepFrontierRunSeconds','900',
    '-deepFrontierWaterShading',$Label,'-logFile',('"' + $log + '"'))
  Write-Output "Water shading probe on a copy of $(Split-Path -Leaf $Save). Log: $log"
  & (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier WaterShading\] COMPLETE' -TimeoutMinutes $TimeoutMinutes
  $code = $LASTEXITCODE
} finally {
  $game = Get-Process -Name Timberborn -ErrorAction SilentlyContinue
  if ($game) { $game.CloseMainWindow() | Out-Null; if (-not $game.WaitForExit(30000)) { Stop-Process -Id $game.Id -Force } }
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
    $file.LastWriteTime = $old
    Write-Output "Added by the run, backdated to $old`: $($file.Name)"
  }
}
Get-Content -LiteralPath $log | Where-Object { $_ -like '`[DeepFrontier WaterShading`]*' }
exit $code
