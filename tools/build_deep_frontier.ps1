$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$project = Join-Path $root 'vendor\timberborn-modding'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$unity = (Get-DevEnvironment 'unity').unity
$log = Join-Path $root 'outputs\unity_official_build.log'

if (Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object ExecutablePath -eq $unity) {
  throw 'Close the authoring project in Unity before running the batch build.'
}
if (-not (Test-Path -LiteralPath $unity -PathType Leaf)) {
  throw "The required Unity editor is missing: $unity"
}
& (Join-Path $PSScriptRoot 'stage_deep_frontier.ps1')
# The official Mod Builder adds and overwrites installed files but never removes one, so a
# blueprint, recipe or sprite deleted from src stayed installed (and uploaded) from older
# builds. Start from an empty version folder; workshop_data.json and the thumbnail sit one
# level up and stay. A running game holding the DLL makes this fail before Unity starts.
$installed = Join-Path (Get-DevEnvironment 'timberbornDocuments').timberbornDocuments 'Mods\DeepFrontier\version-1.1'
if (Test-Path -LiteralPath $installed) { Remove-Item -LiteralPath $installed -Recurse -Force }
$process = Start-Process -FilePath $unity -WindowStyle Hidden -PassThru -ArgumentList @(
  '-batchmode', '-nographics', '-quit',
  # No names: Unity skips its API updater for every assembly. The game's and the mods' DLLs are built for this editor,
  # and on a new project the single-threaded updater otherwise spends over 30 minutes on the 518 game assemblies.
  '-disable-assembly-updater',
  '-projectPath', ('"' + $project + '"'),
  '-executeMethod', 'Timberborn.ModdingTools.ModBuilding.DeepFrontierBatchBuild.Build',
  '-logFile', ('"' + $log + '"')
)
# Wait for the editor's result. Its shared Roslyn compiler can remain alive
# after a failed compile; waiting for the entire process tree never completes.
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw "Official Mod Builder failed ($($process.ExitCode)). See $log" }
Write-Output "Official Mod Builder finished. Log: $log"
