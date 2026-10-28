$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\vendor\timberborn-modding')).Path
$sourceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\src\DeepFrontier')).Path
$destinationRoot = Join-Path $projectRoot 'Assets\Mods\DeepFrontier'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$workshop = (Get-DevEnvironment 'workshopContent').workshopContent

New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null
# The game loads its own dependency mod. Import the exact installed assembly
# for the official builder's compiler/linker, outside this mod's package tree.
if (-not (Test-Path -LiteralPath (Join-Path $workshop '3430626620\version-1.1\TimberUi.dll') -PathType Leaf)) {
  throw 'The required TimberUi authoring reference is missing.'
}
$dependencies = Join-Path $projectRoot 'Assets\Plugins\ModDependencies'
New-Item -ItemType Directory -Force -Path $dependencies | Out-Null
Copy-Item -LiteralPath (Join-Path $workshop '3430626620\version-1.1\TimberUi.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\TimberUi.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $workshop '3284904751\0Harmony.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\0Harmony.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $workshop '3639961044\version-1.1\ModdableRecipes.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\ModdableRecipes.dll.meta') -Destination $dependencies -Force
foreach($name in @('ConveyorBelt.dll','ConveyorBelt.Algorithm.dll')) {
  Copy-Item -LiteralPath (Join-Path (Join-Path $workshop '3815376360\version-1.1') $name) -Destination $dependencies -Force
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot "unity\$name.meta") -Destination $dependencies -Force
}
Copy-Item -LiteralPath (Join-Path $workshop '3578009707\version-1.1\ModdableTimberborn.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\ModdableTimberborn.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $workshop '3283831040\version-1.1\Scripts\ModSettings.Core.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\ModSettings.Core.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $workshop '3283831040\version-1.1\Scripts\ModSettings.Common.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\ModSettings.Common.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $workshop '3801726769\version-1.1\TimberPipes.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\TimberPipes.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $workshop '3766893705\version-1.1\PowerLines.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\PowerLines.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $workshop '3630523180\version-1.1\ModdableWeathers.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\ModdableWeathers.dll.meta') -Destination $dependencies -Force
# Sluice is Back! 11.0.0: referenced only by the optional DeepFrontier.SluiceIsBack assembly (Scripts/SluiceIsBack).
Copy-Item -LiteralPath (Join-Path $workshop '3677643870\version-1.1\SluiceIsBack.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\SluiceIsBack.dll.meta') -Destination $dependencies -Force
foreach ($entry in @('manifest.json', 'Data', 'Scripts', 'Editor', 'AssetBundles')) {
  Copy-Item -LiteralPath (Join-Path $sourceRoot $entry) -Destination $destinationRoot -Recurse -Force
}
# Copying never removes files deleted from src, and the builder compiles and
# packages whatever is staged (a deleted RadiationInteractionTask.cs broke build
# 123's first attempt). Remove staged files with no source, keeping Unity's
# .meta files only for staged files and folders that still exist.
# Assets the build's "Deep Frontier/Create Materials" step authors inside the
# Unity project (src/DeepFrontier/Editor/DeepFrontierMaterials.cs) have no src
# file; they are kept while their input exists, so they are not rebuilt.
$reservoirMesh = 'Resources\Meshes\DeepFrontier\ReservoirRectangle.asset'
function Test-UnityAuthored([string]$entry, [string]$source, [string]$relative) {
  if ($entry -ne 'AssetBundles') { return $false }
  if ($relative -like '*.mat') { return Test-Path -LiteralPath (Join-Path $source ($relative.Substring(0, $relative.Length - 4) + '.BaseColor.png')) }
  return $relative -eq $reservoirMesh -or $reservoirMesh.StartsWith($relative + '\')
}
foreach ($entry in @('Data', 'Scripts', 'Editor', 'AssetBundles')) {
  $source = Join-Path $sourceRoot $entry
  $staged = Join-Path $destinationRoot $entry
  if (-not (Test-Path -LiteralPath $staged)) { continue }
  # Windows PowerShell 5.1 (the build runs there) has no Path.GetRelativePath.
  $stagedFull = (Resolve-Path -LiteralPath $staged).Path.TrimEnd('\')
  foreach ($file in Get-ChildItem -LiteralPath $staged -File -Recurse) {
    $relative = $file.FullName.Substring($stagedFull.Length + 1)
    $origin = if ($file.Extension -eq '.meta') { $relative.Substring(0, $relative.Length - 5) } else { $relative }
    if (-not (Test-Path -LiteralPath (Join-Path $source $origin)) -and -not (Test-UnityAuthored $entry $source $origin)) {
      Remove-Item -LiteralPath $file.FullName -Force
      Write-Output "Removed stale staged file: $entry\$relative"
    }
  }
  Get-ChildItem -LiteralPath $staged -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending |
    Where-Object { $folder = $_.FullName.Substring($stagedFull.Length + 1); -not (Test-Path -LiteralPath (Join-Path $source $folder)) -and -not (Test-UnityAuthored $entry $source $folder) } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force; Write-Output "Removed stale staged folder: $entry\$($_.FullName.Substring($stagedFull.Length + 1))" }
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity\DeepFrontierBatchBuild.cs') -Destination (Join-Path $projectRoot 'Assets\Tools\Editor\Scripts\ModBuilding\DeepFrontierBatchBuild.cs') -Force
Write-Output "Staged Deep Frontier authoring files at $destinationRoot"
