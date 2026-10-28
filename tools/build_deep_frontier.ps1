$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$project = Join-Path $root 'vendor\timberborn-modding'
$unity = 'C:\Program Files\Unity\Hub\Editor\6000.5.11f1\Editor\Unity.exe'
$log = Join-Path $root 'outputs\unity_official_build.log'

if (Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object ExecutablePath -eq $unity) {
  throw 'Close the authoring project in Unity before running the batch build.'
}
if (-not (Test-Path -LiteralPath $unity -PathType Leaf)) {
  throw "The required Unity editor is missing: $unity"
}
& (Join-Path $PSScriptRoot 'stage_deep_frontier.ps1')
$process = Start-Process -FilePath $unity -WindowStyle Hidden -PassThru -ArgumentList @(
  '-batchmode', '-nographics', '-quit',
  '-disable-assembly-updater', 'TimberUi.dll', '0Harmony.dll', 'ModdableRecipes.dll', 'ConveyorBelt.dll', 'ConveyorBelt.Algorithm.dll', 'ModdableTimberborn.dll', 'ModSettings.Core.dll', 'ModSettings.Common.dll', 'TimberPipes.dll', 'PowerLines.dll', 'ModdableWeathers.dll', 'SluiceIsBack.dll',
  '-projectPath', ('"' + $project + '"'),
  '-executeMethod', 'Timberborn.ModdingTools.ModBuilding.DeepFrontierBatchBuild.Build',
  '-logFile', ('"' + $log + '"')
)
# Wait for the editor's result. Its shared Roslyn compiler can remain alive
# after a failed compile; waiting for the entire process tree never completes.
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw "Official Mod Builder failed ($($process.ExitCode)). See $log" }
Write-Output "Official Mod Builder finished. Log: $log"
