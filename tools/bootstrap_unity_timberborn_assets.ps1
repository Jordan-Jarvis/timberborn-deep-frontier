$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\vendor\timberborn-modding')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$gameRoot = (Get-DevEnvironment 'gameRoot').gameRoot
$managedSource = Join-Path $gameRoot 'Timberborn_Data\Managed'
$streamingSource = Join-Path $gameRoot 'Timberborn_Data\StreamingAssets\Modding'
$dllDestination = Join-Path $projectRoot 'Assets\Plugins\Timberborn'
$importedDestination = Join-Path $projectRoot 'Assets\Tools\ImportedAssets'
$resourcesDestination = Join-Path $importedDestination 'Editor\Resources'

if (-not (Get-ChildItem -Path $managedSource -Filter 'Timberborn.*.dll' -ErrorAction SilentlyContinue | Select-Object -First 1)) {
  throw "Timberborn managed assemblies were not found at $managedSource"
}

Remove-Item -LiteralPath $dllDestination -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $importedDestination -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $dllDestination, $resourcesDestination | Out-Null

# Match the official Timberborn importer. Unity already supplies its own
# engine/System assemblies; copying those game copies into Assets/Plugins
# creates duplicate extension methods under newer Unity editor builds.
Remove-Item -Path (Join-Path $dllDestination '*') -Force -ErrorAction SilentlyContinue
$excludedPrefixes = @('Mono.', 'mscorlib.', 'netstandard', 'System.', 'Unity.', 'UnityEngine.')
$alwaysImported = @(
  'System.Collections.Immutable.dll',
  'System.Runtime.CompilerServices.Unsafe.dll',
  'System.Threading.Tasks.Extensions.dll',
  'System.Diagnostics.EventLog.dll',
  'System.Text.Encodings.Web.dll',
  'System.Text.Json.dll'
)
Get-ChildItem -Path $managedSource -Filter '*.dll' | Where-Object {
  $dll = $_
  $alwaysImported -contains $dll.Name -or
    -not ($excludedPrefixes | Where-Object {
      $prefix = $_
      $dll.Name.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
    })
} | Copy-Item -Destination $dllDestination -Force

function Expand-ModdingZip([string]$name, [string]$destination, [string]$extension = '') {
  $zip = Join-Path $streamingSource "$name.zip"
  if (-not (Test-Path $zip)) { throw "Missing Timberborn modding archive: $zip" }
  New-Item -ItemType Directory -Force -Path $destination | Out-Null
  Expand-Archive -LiteralPath $zip -DestinationPath $destination -Force
  if ($extension -ne '') {
    Get-ChildItem -Path $destination -File -Recurse | ForEach-Object {
      if (-not $_.Name.EndsWith($extension)) {
        Rename-Item -LiteralPath $_.FullName -NewName ($_.Name + $extension)
      }
    }
  }
}

Expand-ModdingZip 'Shaders' (Join-Path $resourcesDestination 'Shaders')
Expand-ModdingZip 'Blueprints' $resourcesDestination
Expand-ModdingZip 'Localizations' (Join-Path $resourcesDestination 'Localizations')
Expand-ModdingZip 'UI' (Join-Path $resourcesDestination 'UI') '.txt'
Expand-ModdingZip 'EditorDll' (Join-Path $resourcesDestination 'EditorDll')
Expand-ModdingZip 'EditorUI' (Join-Path $resourcesDestination 'UI')
Copy-Item -LiteralPath (Join-Path $streamingSource 'TimberbornExampleModels.blend') -Destination $importedDestination -Force

# The official importer publicizes Timberborn.* assemblies for mod authoring.
# Keep this as a separate, auditable step while making the bootstrap one-shot.
& (Join-Path $PSScriptRoot 'publicize_timberborn_dlls.ps1')

Write-Output "Bootstrapped Timberborn assemblies and modding assets into $projectRoot"
