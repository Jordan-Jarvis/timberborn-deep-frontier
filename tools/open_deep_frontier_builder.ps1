$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\vendor\timberborn-modding')).Path
$unity = 'C:\Program Files\Unity\Hub\Editor\6000.5.11f1\Editor\Unity.exe'

if (-not (Test-Path -LiteralPath $unity -PathType Leaf)) {
  throw "The project's Unity editor was not found at $unity."
}
if (Get-Process -Name Unity -ErrorAction SilentlyContinue) {
  throw 'Unity is already running. Stage changes, then open Timberborn > Show Mod Builder in the existing editor.'
}

& (Join-Path $PSScriptRoot 'stage_deep_frontier.ps1')
# This opens the official builder; it does not copy runtime files or build a package.
Start-Process -FilePath $unity -ArgumentList @(
  '-projectPath', ('"' + $projectRoot + '"'),
  '-executeMethod', 'Timberborn.ModdingTools.ModBuilding.ModBuilderWindow.ShowWindow'
) | Out-Null
Write-Output 'Opened the official Mod Builder. Select DeepFrontier, compatibility 1.1, Code and Windows AssetBundle, then Build.'
